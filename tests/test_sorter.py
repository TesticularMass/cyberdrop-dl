import base64
import datetime
import itertools
import shutil
import zipfile
from pathlib import Path
from typing import Never

import pytest

from cyberdrop_dl.database import Database
from cyberdrop_dl.sorter import Sorter, _format_dest, _have_same_content, _move_file
from tests.test_archives import _CONTENT, _PASSWORD, _ZIPCRYPTO_B64

DOWNLOADS = Path("/mnt/home/user/downloads/cdl/")
SORT_DIR = DOWNLOADS.parent / "cdl_sorted"
MTIME = datetime.datetime(2023, 7, 14, 12, 34, 56, tzinfo=datetime.UTC).timestamp()


@pytest.mark.parametrize(
    ("base_dir", "format_str", "expected"),
    [
        (
            "album 1 (site)",
            ("{sort_dir}/{base_dir}/audios/{parent_dir}___{filename}{ext}"),
            "/mnt/home/user/downloads/cdl_sorted/album 1 (site)/audios/sub album___song.mp3",
        ),
        ("foo (Mega.NZ)", "{base_dir}/{file_date_iso}/{filename}{ext}", "foo (Mega.NZ)/2023-07-14/song.mp3"),
        (
            "folder 1",
            "/mnt/data/{base_dir}/{file_date_us}/{filename}{ext}",
            "/mnt/data/folder 1/2023-14-07/song.mp3",
        ),
        ("folder 1", "{base_dir}/{file_date:%Y}/{filename}{ext}", "folder 1/2023/song.mp3"),
        ("folder 1", "{base_dir}/{invalid_param}/{filename}{ext}", "folder 1/UNKNOWN_INVALID_PARAM/song.mp3"),
    ],
)
def test_destination_format(base_dir: str, format_str: str, expected: str) -> None:
    file = DOWNLOADS / base_dir / "sub album/song.mp3"
    result = _format_dest(file, base_dir, format_str, MTIME, SORT_DIR)
    assert result == Path(expected)


class TestHaveSameContent:
    def test_same_file_returns_true(self, tmp_path: Path) -> None:
        foo = tmp_path / "foo.bin"
        foo.write_bytes(b"12345")
        assert _have_same_content(foo, foo)

    def test_same_content_same_size_returns_true(self, tmp_path: Path) -> None:
        foo, bar = tmp_path / "foo.bin", tmp_path / "bar.bin"
        data = b"0" * 1_000
        foo.write_bytes(data)
        bar.write_bytes(data)
        assert _have_same_content(foo, bar)

    def test_different_size_returns_false(self, tmp_path: Path) -> None:
        foo, bar = tmp_path / "foo.bin", tmp_path / "bar.bin"
        foo.write_bytes(b"x")
        bar.write_bytes(b"x" * 10)
        assert not _have_same_content(foo, bar)

    def test_same_size_different_content_returns_false(self, tmp_path: Path) -> None:
        foo, bar = tmp_path / "foo.bin", tmp_path / "bar.bin"
        foo.write_bytes(b"\x00" * 512)
        bar.write_bytes(b"\xff" * 512)
        assert not _have_same_content(foo, bar)

    def test_empty_files_return_true(self, tmp_path: Path) -> None:
        foo, bar = tmp_path / "foo.bin", tmp_path / "bar.bin"
        foo.touch()
        bar.touch()
        assert _have_same_content(foo, bar)

    def test_large_files_same_content_return_true(self, tmp_path: Path) -> None:
        foo, bar = tmp_path / "foo.bin", tmp_path / "bar.bin"
        data_10MB = b"A" * 1024 * 1024 * 10
        foo.write_bytes(data_10MB)
        bar.write_bytes(data_10MB)
        assert _have_same_content(foo, bar)


class TestMoveFile:
    def test_same_file_returns_immediately(self, tmp_path: Path) -> None:
        foo = tmp_path / "foo.txt"
        foo.write_text("x")
        assert _move_file(foo, foo) == foo
        assert foo.exists()

    def test_simple_move(self, tmp_path: Path) -> None:
        src = tmp_path / "foo.txt"
        src.write_text("data")
        dst = tmp_path / "sub" / "bar.txt"
        out = _move_file(src, dst)
        assert out == dst
        assert not src.exists()
        assert dst.read_text() == "data"

    def test_name_collision_same_size_diferent_content(self, tmp_path: Path) -> None:
        src = tmp_path / "foo.txt"
        src.write_text("abc")
        dst = tmp_path / "bar.txt"
        dst.write_text("123")
        out = _move_file(src, dst)

        assert out
        assert out != dst
        assert not src.exists()
        assert dst.read_text() == "123"
        assert out.read_text() == "abc"

    def test_name_collision_different_size(self, tmp_path: Path) -> None:
        src = tmp_path / "foo.jpg"
        src.write_bytes(b"0" * 100)
        dst = tmp_path / "bar.jpg"
        dst.write_bytes(b"1" * 50)
        out = _move_file(src, dst)
        assert out
        assert out == tmp_path / "bar1.jpg"
        assert not src.exists()
        assert out.stat().st_size == 100

    def test_custom_incrementer_format(self, tmp_path: Path) -> None:
        src = tmp_path / "foo.log"
        src.write_text("a")
        dest = tmp_path / "bar.log"
        dest.write_text("x")
        for i in range(1, 4):
            (tmp_path / f"bar_{i}.log").write_text("x")
        out = _move_file(src, dest, incrementer_format="_{i}")
        assert out == tmp_path / "bar_4.log"

    def test_max_retries_exceeded(self, tmp_path: Path) -> None:
        src = tmp_path / "foo.txt"
        src.write_text("x")
        dest = tmp_path / "bar.txt"
        dest.touch()
        for i in range(1, 12):
            (tmp_path / f"bar{i}.txt").touch()

        assert _move_file(src, dest) is None
        assert src.exists()

    def test_os_error_during_move_cancels_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "foo.txt"
        src.write_text("x")
        dst = tmp_path / "bar.txt"

        def boom(*_: object, **_k: object) -> Never:
            raise OSError

        monkeypatch.setattr(shutil, "move", boom)
        assert _move_file(src, dst) is None
        assert src.exists()


class Files:
    VIDEOS = "video.mp4", "movies/4K/a_movie.mkv"
    OTHERS = (
        "docker-compose.yml",
        "index.html",
        "styles.css",
        "tests/scripts/notes.txt",
        "tests/scripts/script.js",
        "tests/setup.sh",
        "tests/utils.py",
    )
    AUDIOS = ("music/song.mp3",)
    IMAGES = ("logo.png", "tests/logo.jpg")
    TEMP = ("tmp/download.part",)

    ALL = *VIDEOS, *OTHERS, *AUDIOS, *IMAGES, *TEMP


async def test_sorter(tmp_path: Path) -> None:
    assert len(Files.ALL) == len(set(Files.ALL))
    input_dir = tmp_path / "cdl_downloads"
    output_dir = tmp_path / "cdl_sorted_downloads"
    sorter = Sorter(
        input_dir=input_dir,
        output_dir=output_dir,
        audio_format="{sort_dir}/audio/{filename}{ext}",
        image_format="{sort_dir}/image/{filename}{ext}",
        video_format="{sort_dir}/video/{filename}{ext}",
        non_media_format="{sort_dir}/other/{filename}{ext}",
    )

    for idx, file in enumerate(Files.ALL):
        path = input_dir / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(idx))

    await sorter.run(disable_tui=True)
    stats = sorter.stats
    assert stats.total == len(Files.ALL) - len(Files.TEMP)
    assert stats.videos == len(Files.VIDEOS)
    assert stats.others == len(Files.OTHERS)

    assert sorted(f for f in output_dir.rglob("*") if f.is_file()) == sorted(
        itertools.chain.from_iterable(
            (output_dir / kind / file.name for file in map(Path, files))
            for kind, files in [
                ("audio", Files.AUDIOS),
                ("image", Files.IMAGES),
                ("video", Files.VIDEOS),
                ("other", Files.OTHERS),
            ]
        )
    )


def _make_sorter(input_dir: Path, output_dir: Path, database: Database | None = None) -> Sorter:
    return Sorter(
        input_dir=input_dir,
        output_dir=output_dir,
        audio_format=None,
        image_format=None,
        video_format=None,
        non_media_format="{sort_dir}/other/{filename}{ext}",
        unzip_archives=True,
        database=database,
    )


async def _seed_password(db: Database, download_path: Path, filename: str, password: str) -> None:
    query = """
    INSERT INTO media (domain, url_path, referer, download_path, download_filename, original_filename,
                       password, completed, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
    """
    params = ("test", f"/{filename}", "https://example.com", str(download_path), filename, filename, password)
    await db.conn.execute(query, params)
    await db.conn.commit()


async def test_sorter_extracts_archive_with_db_password(tmp_path: Path) -> None:
    input_dir = tmp_path / "downloads"
    input_dir.mkdir()
    archive = input_dir / "protected.zip"
    archive.write_bytes(base64.b64decode(_ZIPCRYPTO_B64))

    async with Database(tmp_path / "test_db.db") as db:
        await _seed_password(db, input_dir, archive.name, _PASSWORD)
        sorter = _make_sorter(input_dir, tmp_path / "sorted", db)
        await sorter.run(disable_tui=True)

    assert not archive.exists()
    assert (tmp_path / "sorted/other/secret.txt").read_bytes() == _CONTENT
    assert sorter.stats.errors == 0


async def test_sorter_keeps_archive_when_no_password_matches(tmp_path: Path) -> None:
    input_dir = tmp_path / "downloads"
    input_dir.mkdir()
    archive = input_dir / "protected.zip"
    archive.write_bytes(base64.b64decode(_ZIPCRYPTO_B64))

    async with Database(tmp_path / "test_db.db") as db:
        await _seed_password(db, input_dir, archive.name, "not-the-password")
        sorter = _make_sorter(input_dir, tmp_path / "sorted", db)
        await sorter.run(disable_tui=True)

    # extraction failed so the archive is kept, but the sort pass still moves it as non-media
    assert (tmp_path / "sorted/other/protected.zip").exists()
    assert not (tmp_path / "sorted/other/secret.txt").exists()
    assert sorter.stats.errors == 1


async def test_sorter_extracts_plain_archive_without_db(tmp_path: Path) -> None:
    input_dir = tmp_path / "downloads"
    input_dir.mkdir()
    archive = input_dir / "plain.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("notes.txt", _CONTENT)

    sorter = _make_sorter(input_dir, tmp_path / "sorted")
    await sorter.run(disable_tui=True)

    assert not archive.exists()
    assert (tmp_path / "sorted/other/notes.txt").read_bytes() == _CONTENT


async def test_sorter_corrupted_archive_is_kept_and_counted(tmp_path: Path) -> None:
    input_dir = tmp_path / "downloads"
    input_dir.mkdir()
    archive = input_dir / "corrupt.zip"
    archive.write_bytes(b"PK\x03\x04 this is not really a zip")

    sorter = _make_sorter(input_dir, tmp_path / "sorted")
    await sorter.run(disable_tui=True)

    # extraction failed so the archive is kept, but the sort pass still moves it as non-media
    assert (tmp_path / "sorted/other/corrupt.zip").exists()
    assert sorter.stats.errors == 1
