"""Synchronous archive extraction with a typed error taxonomy.

All extract functions are blocking; run them in a thread (e.g. `asyncio.to_thread`).
"""

from __future__ import annotations

import zipfile
import zlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_INSTALL_HINT = "install 'cyberdrop-dl-patched[archives]' to extract it"

SUPPORTED_SUFFIXES = frozenset({".zip", ".7z"})


class ArchiveError(Exception):
    """Base error for archive extraction failures."""


class CorruptedArchiveError(ArchiveError):
    """The archive is damaged or is not actually an archive."""


class EncryptedArchiveError(ArchiveError):
    """The archive requires a password."""


class WrongPasswordError(EncryptedArchiveError):
    """The provided password does not match."""


class UnsupportedArchiveError(ArchiveError):
    """The archive uses a format, compression or encryption method we can not handle."""


def extract(archive: Path, dest: Path | None = None, password: str | None = None) -> None:
    """Extracts `archive` into `dest` (defaults to the archive's own folder)."""
    dest = dest or archive.parent
    suffix = archive.suffix.lower()
    if suffix == ".zip":
        return _extract_zip(archive, dest, password)
    if suffix == ".7z":
        return _extract_7z(archive, dest, password)
    raise UnsupportedArchiveError(f"'{archive.name}' is not a supported archive type")


def _extract_zip(archive: Path, dest: Path, password: str | None) -> None:
    pwd = password.encode() if password else None
    try:
        zip_file = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as e:
        raise CorruptedArchiveError(f"'{archive.name}' is not a valid zip file: {e}") from e

    with zip_file:
        encrypted = any(info.flag_bits & 0x1 for info in zip_file.infolist())
        if encrypted and pwd is None:
            raise EncryptedArchiveError(f"'{archive.name}' is password protected")
        try:
            zip_file.extractall(dest, pwd=pwd)
        except NotImplementedError as e:
            # AES encryption (compression type 99) or an unsupported compression method
            _extract_zip_w_pyzipper(archive, dest, pwd, stdlib_error=e)
        except RuntimeError as e:
            if encrypted:
                raise WrongPasswordError(f"wrong password for '{archive.name}'") from e
            raise
        except (zipfile.BadZipFile, zlib.error) as e:
            if encrypted:
                # ZipCrypto's check byte can pass with a wrong password; the CRC then fails
                raise WrongPasswordError(f"wrong password for '{archive.name}'") from e
            raise CorruptedArchiveError(f"'{archive.name}' is corrupted: {e}") from e


def _extract_zip_w_pyzipper(archive: Path, dest: Path, pwd: bytes | None, stdlib_error: NotImplementedError) -> None:
    try:
        import pyzipper
    except ImportError:
        msg = f"'{archive.name}' needs a method the standard library does not support ({stdlib_error}); {_INSTALL_HINT}"
        raise UnsupportedArchiveError(msg) from stdlib_error

    try:
        with pyzipper.AESZipFile(archive) as zip_file:
            zip_file.extractall(dest, pwd=pwd)
    except RuntimeError as e:
        if pwd is not None:
            raise WrongPasswordError(f"wrong password for '{archive.name}'") from e
        raise EncryptedArchiveError(f"'{archive.name}' is password protected") from e
    except NotImplementedError as e:
        raise UnsupportedArchiveError(f"'{archive.name}' uses an unsupported compression method: {e}") from e
    except (zipfile.BadZipFile, zlib.error) as e:
        if pwd is not None:
            raise WrongPasswordError(f"wrong password for '{archive.name}'") from e
        raise CorruptedArchiveError(f"'{archive.name}' is corrupted: {e}") from e


def _extract_7z(archive: Path, dest: Path, password: str | None) -> None:
    try:
        import py7zr
        import py7zr.exceptions
    except ImportError as e:
        raise UnsupportedArchiveError(f"can not extract '{archive.name}'; {_INSTALL_HINT}") from e

    import lzma

    try:
        with py7zr.SevenZipFile(archive, password=password) as seven_zip:
            if password is None and seven_zip.needs_password():
                raise EncryptedArchiveError(f"'{archive.name}' is password protected")
            seven_zip.extractall(dest)
    except py7zr.exceptions.PasswordRequired as e:
        raise EncryptedArchiveError(f"'{archive.name}' is password protected") from e
    except py7zr.exceptions.Bad7zFile as e:
        raise CorruptedArchiveError(f"'{archive.name}' is not a valid 7z file: {e}") from e
    except (lzma.LZMAError, py7zr.exceptions.CrcError) as e:
        if password is not None:
            raise WrongPasswordError(f"wrong password for '{archive.name}'") from e
        raise CorruptedArchiveError(f"'{archive.name}' is corrupted: {e}") from e
