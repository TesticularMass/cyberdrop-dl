from __future__ import annotations

import base64
import zipfile
from typing import TYPE_CHECKING

import py7zr
import pytest
import pyzipper

from cyberdrop_dl import archives

if TYPE_CHECKING:
    from pathlib import Path

# Stored-method zip with traditional PKWARE (ZipCrypto) encryption.
# Contains 'secret.txt' -> b'attack at dawn\n', password 'hunter2'.
_ZIPCRYPTO_B64 = (
    "UEsDBBQAAQAAAAAAIQD421jSGwAAAA8AAAAKAAAAc2VjcmV0LnR4dO3T1k0BPy3og/uPVSmwj820G2Q1eISryepGD1BLAQIU"
    "ABQAAQAAAAAAIQD421jSGwAAAA8AAAAKAAAAAAAAAAAAAAAAAAAAAABzZWNyZXQudHh0UEsFBgAAAAABAAEAOAAAAEMAAAAAAA=="
)
_PASSWORD = "hunter2"  # noqa: S105
_CONTENT = b"attack at dawn\n"


@pytest.fixture
def zipcrypto_zip(tmp_path: Path) -> Path:
    archive = tmp_path / "protected.zip"
    archive.write_bytes(base64.b64decode(_ZIPCRYPTO_B64))
    return archive


@pytest.fixture
def aes_zip(tmp_path: Path) -> Path:
    archive = tmp_path / "aes.zip"
    with pyzipper.AESZipFile(archive, "w", encryption=pyzipper.WZ_AES) as zip_file:
        zip_file.setpassword(_PASSWORD.encode())
        zip_file.writestr("secret.txt", _CONTENT)
    return archive


@pytest.fixture
def seven_zip(tmp_path: Path) -> Path:
    archive = tmp_path / "protected.7z"
    with py7zr.SevenZipFile(archive, "w", password=_PASSWORD) as seven_zip_file:
        seven_zip_file.writestr(_CONTENT, "secret.txt")
    return archive


def test_plain_zip_extracts(tmp_path: Path) -> None:
    archive = tmp_path / "plain.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("secret.txt", _CONTENT)

    archives.extract(archive)
    assert (tmp_path / "secret.txt").read_bytes() == _CONTENT


def test_extract_to_custom_dest(tmp_path: Path) -> None:
    archive = tmp_path / "plain.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("secret.txt", _CONTENT)

    dest = tmp_path / "out"
    archives.extract(archive, dest=dest)
    assert (dest / "secret.txt").read_bytes() == _CONTENT


def test_corrupt_zip(tmp_path: Path) -> None:
    archive = tmp_path / "corrupt.zip"
    archive.write_bytes(b"PK\x03\x04 this is not really a zip")

    with pytest.raises(archives.CorruptedArchiveError):
        archives.extract(archive)


def test_unsupported_suffix(tmp_path: Path) -> None:
    archive = tmp_path / "archive.rar"
    archive.write_bytes(b"Rar!")

    with pytest.raises(archives.UnsupportedArchiveError):
        archives.extract(archive)


def test_zipcrypto_no_password(zipcrypto_zip: Path) -> None:
    with pytest.raises(archives.EncryptedArchiveError):
        archives.extract(zipcrypto_zip)


def test_zipcrypto_wrong_password(zipcrypto_zip: Path) -> None:
    with pytest.raises(archives.WrongPasswordError):
        archives.extract(zipcrypto_zip, password="wrong")  # noqa: S106


def test_zipcrypto_right_password(zipcrypto_zip: Path) -> None:
    archives.extract(zipcrypto_zip, password=_PASSWORD)
    assert (zipcrypto_zip.parent / "secret.txt").read_bytes() == _CONTENT


def test_aes_zip_no_password(aes_zip: Path) -> None:
    with pytest.raises(archives.EncryptedArchiveError):
        archives.extract(aes_zip)


def test_aes_zip_wrong_password(aes_zip: Path) -> None:
    with pytest.raises(archives.WrongPasswordError):
        archives.extract(aes_zip, password="wrong")  # noqa: S106


def test_aes_zip_right_password(aes_zip: Path) -> None:
    archives.extract(aes_zip, password=_PASSWORD)
    assert (aes_zip.parent / "secret.txt").read_bytes() == _CONTENT


def test_7z_no_password(seven_zip: Path) -> None:
    with pytest.raises(archives.EncryptedArchiveError):
        archives.extract(seven_zip)


def test_7z_wrong_password(seven_zip: Path) -> None:
    with pytest.raises(archives.WrongPasswordError):
        archives.extract(seven_zip, password="wrong")  # noqa: S106


def test_7z_right_password(seven_zip: Path) -> None:
    archives.extract(seven_zip, password=_PASSWORD)
    assert (seven_zip.parent / "secret.txt").read_bytes() == _CONTENT


def test_plain_7z_extracts(tmp_path: Path) -> None:
    archive = tmp_path / "plain.7z"
    with py7zr.SevenZipFile(archive, "w") as seven_zip_file:
        seven_zip_file.writestr(_CONTENT, "secret.txt")

    archives.extract(archive)
    assert (tmp_path / "secret.txt").read_bytes() == _CONTENT
