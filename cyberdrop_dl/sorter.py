from __future__ import annotations

import asyncio
import dataclasses
import datetime
import errno
import hashlib
import logging
import shutil
import struct
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Self

import imagesize

from cyberdrop_dl import aio, archives, ffmpeg
from cyberdrop_dl.constants import FileExt, TempExt
from cyberdrop_dl.models.validators import strings
from cyberdrop_dl.progress.sorting import SortingUI, SortStats
from cyberdrop_dl.utils import cleanup

if TYPE_CHECKING:
    from cyberdrop_dl.config import Config
    from cyberdrop_dl.database import Database

_MAX_PASSWORD_CANDIDATES = 20


logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True, kw_only=True)
class Sorter:
    input_dir: Path
    output_dir: Path

    audio_format: str | None
    image_format: str | None
    video_format: str | None
    non_media_format: str | None
    unzip_archives: bool = False
    incrementer_format: str = "{i}"
    database: Database | None = None

    _tui: SortingUI = dataclasses.field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._tui = SortingUI(self.input_dir, self.output_dir)

    @property
    def stats(self) -> SortStats:
        return self._tui.stats

    @classmethod
    def from_config(cls, config: Config, database: Database | None = None) -> Self:
        settings = config.sort
        return cls(
            input_dir=settings.input_folder or config.download_folder,
            output_dir=settings.output_folder,
            unzip_archives=settings.unzip_archives,
            incrementer_format=settings.formats.incrementer,
            audio_format=settings.formats.audio,
            image_format=settings.formats.image,
            video_format=settings.formats.video,
            non_media_format=settings.formats.non_media,
            database=database,
        )

    async def run(self, *, disable_tui: bool = False) -> None:
        if not await aio.is_dir(self.input_dir):
            logger.error(f"Sort directory '{self.input_dir}' does not exist", extra={"color": "red"})
            return

        logger.info("Sorting downloads...", extra={"color": "cyan"})
        await aio.mkdir(self.output_dir, parents=True, exist_ok=True)

        self._tui.disabled = disable_tui
        with self._tui():
            await self._run()

    async def _run(self) -> None:
        if self.unzip_archives:
            await self._extract_archives()

        async with asyncio.TaskGroup() as tg:

            async def sort_subfolder(folder: Path) -> None:
                async for path in aio.rglob(folder, "*"):
                    if await aio.is_file(path):
                        _ = tg.create_task(self._sort_file(folder.name, path))

            async for path in aio.glob(self.input_dir, "*"):
                if await aio.is_file(path):
                    _ = tg.create_task(self._sort_file(self.input_dir.name, path))
                else:
                    _ = tg.create_task(sort_subfolder(path))

        logger.info("DONE!", extra={"color": "green"})
        cleanup.rm_empty_dirs(self.input_dir)

    async def _extract_archives(self) -> None:
        logger.info("Extracting archives...", extra={"color": "cyan"})
        async with asyncio.TaskGroup() as tg:
            async for path in aio.rglob(self.input_dir, "*"):
                if path.suffix.lower() in archives.SUPPORTED_SUFFIXES and await aio.is_file(path):
                    _ = tg.create_task(self._extract_archive(path))

    async def _extract_archive(self, archive: Path) -> None:
        try:
            await self._extract_w_passwords(archive)
        except archives.EncryptedArchiveError as e:
            logger.warning("%s; extract it manually", e, extra={"color": "yellow"})
            self._tui.stats.errors += 1
        except archives.CorruptedArchiveError as e:
            logger.error("%s; re-download or delete it", e, extra={"color": "red"})
            self._tui.stats.errors += 1
        except archives.UnsupportedArchiveError as e:
            logger.warning("Unable to extract '%s': %s", archive.name, e, extra={"color": "yellow"})
            self._tui.stats.errors += 1
        except OSError as e:
            logger.error("Unable to extract '%s': %s", archive.name, _os_error_hint(e), extra={"color": "red"})
            self._tui.stats.errors += 1
        except Exception:
            # task boundary: an uncaught exception would cancel every other extraction
            logger.exception("Unknown error while extracting '%s'", archive)
            self._tui.stats.errors += 1
        else:
            await aio.unlink(archive)

    async def _extract_w_passwords(self, archive: Path) -> None:
        try:
            return await asyncio.to_thread(archives.extract, archive)
        except archives.EncryptedArchiveError:
            pass

        candidates = await self._password_candidates(archive)
        if not candidates:
            raise archives.EncryptedArchiveError(f"'{archive.name}' is password protected and no passwords are known")

        for password in candidates:
            try:
                return await asyncio.to_thread(archives.extract, archive, password=password)
            except archives.WrongPasswordError:
                continue

        msg = f"'{archive.name}' is password protected; tried {len(candidates)} known password(s), none matched"
        raise archives.EncryptedArchiveError(msg)

    async def _password_candidates(self, archive: Path) -> list[str]:
        if self.database is None:
            return []
        candidates = await self.database.history.get_passwords_for_file(str(archive.parent), archive.name)
        for password in await self.database.history.get_all_passwords():
            if password not in candidates:
                candidates.append(password)
        return candidates[:_MAX_PASSWORD_CANDIDATES]

    async def _sort_file(self, folder_name: str, file: Path) -> None:
        ext = file.suffix.lower()
        if ext in TempExt:
            return None

        try:
            if ext in FileExt.AUDIO:
                return await self.sort_audio(file, folder_name)
            if ext in FileExt.IMAGE:
                return await self.sort_image(file, folder_name)
            if ext in FileExt.VIDEO:
                return await self.sort_video(file, folder_name)
            await self.sort_other(file, folder_name)

        except OSError as e:
            logger.error("Unable to sort '%s': %s", file, _os_error_hint(e), extra={"color": "red"})
            self._tui.stats.errors += 1
        except Exception:
            logger.exception("Unknown error while sorting '%s'", file)
            self._tui.stats.errors += 1

    async def sort_audio(self, file: Path, base_name: str) -> None:
        if not self.audio_format:
            return

        bitrate = duration = sample_rate = None
        probe_output = await _try_probe("audio", file)
        if probe_output and (audio := probe_output.audio):
            duration = audio.duration or probe_output.format.duration
            bitrate = audio.bitrate
            sample_rate = audio.sample_rate

        if await self._move_file(
            file,
            base_name,
            self.audio_format,
            bitrate=bitrate,
            duration=duration,
            length=duration,
            sample_rate=sample_rate,
        ):
            self._tui.stats.audios += 1

    async def sort_image(self, file: Path, base_name: str) -> None:
        if not self.image_format:
            return

        height = resolution = width = None
        try:
            info = await asyncio.to_thread(
                imagesize.get_info,
                file,
                size=True,
                dpi=False,
                colors=False,
                exif_rotation=True,
                channels=False,
            )
        except (OSError, ValueError, struct.error) as e:
            logger.warning("Unable to get some image properties of '%s': %s", file, e)
        else:
            width, height = info.width, info.height
            resolution = f"{width}x{height}"

        if await self._move_file(
            file,
            base_name,
            self.image_format,
            height=height,
            resolution=resolution,
            width=width,
        ):
            self._tui.stats.images += 1

    async def sort_video(self, file: Path, base_name: str) -> None:
        if not self.video_format:
            return

        codec = duration = framerate = height = resolution = width = None
        probe_output = await _try_probe("video", file)
        if probe_output and (video := probe_output.video):
            width = video.width
            height = video.height
            resolution = video.resolution
            codec = video.codec
            duration = video.duration or probe_output.format.duration
            framerate = video.fps

        if await self._move_file(
            file,
            base_name,
            self.video_format,
            codec=codec,
            duration=duration,
            length=duration,
            fps=framerate,
            height=height,
            resolution=resolution,
            width=width,
        ):
            self._tui.stats.videos += 1

    async def sort_other(self, file: Path, base_name: str) -> None:
        if not self.non_media_format:
            return

        if await self._move_file(file, base_name, self.non_media_format):
            self._tui.stats.others += 1

    async def _move_file(self, file: Path, base_name: str, format_str: str, /, **kwargs: object) -> bool:
        dest = _format_dest(
            file,
            base_name,
            format_str,
            mtime=(await aio.stat(file)).st_mtime,
            sort_dir=self.output_dir,
            **kwargs,
        )
        dest = await asyncio.to_thread(_move_file, file, dest, self.incrementer_format)
        if dest:
            logger.debug("Moved '%s' to '%s'", file, dest)
        else:
            self._tui.stats.errors += 1
        return bool(dest)


def _format_dest(
    file: Path,
    base_dir: str,
    format_string: str,
    /,
    mtime: float,
    sort_dir: Path,
    **kwargs: object,
) -> Path:
    file_date = datetime.datetime.fromtimestamp(mtime).replace(microsecond=0)  # noqa: DTZ006

    dest, _ = strings.safe_format(
        format_string,
        base_dir=base_dir,
        ext=file.suffix,
        file_date=file_date,
        file_date_iso=file_date.strftime("%Y-%m-%d"),
        file_date_us=file_date.strftime("%Y-%d-%m"),
        filename=file.stem,
        parent_dir=file.parent.name,
        sort_dir=sort_dir,
        **kwargs,
    )

    return Path(dest)


def _move_but_not_overwrite(source: Path, dest: Path) -> Path:
    if dest.exists():
        raise FileExistsError(dest)
    _ = shutil.move(source, dest)
    return dest


def _have_same_content(source: Path, dest: Path) -> bool:
    if source.stat().st_size != dest.stat().st_size:
        return False

    with source.open("rb") as f_in, dest.open("rb") as f_out:
        return hashlib.file_digest(f_in, "md5").hexdigest() == hashlib.file_digest(f_out, "md5").hexdigest()


def _move_file(
    source: Path,
    dest: Path,
    incrementer_format: str = "{i}",
    *,
    max_retries: int = 10,
) -> Path | None:

    dest = dest.resolve()
    if source == dest:
        return dest

    dest_parent = dest.parent
    dest_parent.mkdir(parents=True, exist_ok=True)

    try:
        try:
            return _move_but_not_overwrite(source, dest)
        except FileExistsError:
            dest_stem = dest.stem
            for auto_index in range(1, max_retries + 1):
                if _have_same_content(source, dest):
                    source.unlink()
                    return dest

                new_filename = f"{dest_stem}{incrementer_format.format(i=auto_index)}{dest.suffix}"
                logger.warning(
                    "Found name collision when moving '%s' to '%s'. Retring with '%s'",
                    source,
                    dest,
                    dest := dest_parent / new_filename,
                )

                try:
                    return _move_but_not_overwrite(source, dest)
                except FileExistsError:
                    continue

            logger.error("Unable to move '%s'. Giving up after %s attempts", source, max_retries)
            return None
    except OSError:
        logger.exception("Unable to move '%s'", source)
        return None


async def _try_probe(kind: str, file: Path) -> ffmpeg.FFprobeResult | None:
    try:
        return await ffmpeg.probe(file)
    except (RuntimeError, CalledProcessError, OSError):
        logger.exception("Unable to get %s properties of '%s'", kind, file)


def _os_error_hint(e: OSError) -> str:
    if e.errno == errno.ENOSPC:
        return f"disk full ({e})"
    if e.errno in (errno.EACCES, errno.EPERM):
        return f"permission denied ({e})"
    return str(e)
