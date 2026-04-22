from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from cyberdrop_dl.clients.download_client import DownloadClient
from cyberdrop_dl.data_structures.url_objects import AbsoluteHttpURL, MediaItem
from cyberdrop_dl.downloader.downloader import Downloader
from cyberdrop_dl.utils import ffmpeg

if TYPE_CHECKING:
    from pathlib import Path


def _make_media_item(tmp_path: Path) -> MediaItem:
    url = AbsoluteHttpURL("https://example.com/file?token=1")
    return MediaItem(
        url=url,
        domain="example.com",
        referer=url,
        download_folder=tmp_path,
        filename="file.mp4",
        original_filename="file.mp4",
        ext=".mp4",
        db_path="/file?token=1",
    )


async def test_run_skips_already_processed_db_path(
    running_manager, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    downloader = Downloader(running_manager, "example.com")
    media_item = _make_media_item(tmp_path)
    downloader.processed_items.add(media_item.db_path)

    @contextlib.asynccontextmanager
    async def noop_download_context(_media_item: MediaItem):
        yield

    start_download = mock.AsyncMock(return_value=True)
    monkeypatch.setattr(downloader, "_download_context", noop_download_context)
    monkeypatch.setattr(downloader, "start_download", start_download)

    assert await downloader.run(media_item) is False
    start_download.assert_not_awaited()


async def test_download_hls_skips_already_processed_db_path(
    running_manager, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    downloader = Downloader(running_manager, "example.com")
    media_item = _make_media_item(tmp_path)
    downloader.processed_items.add(media_item.db_path)

    @contextlib.asynccontextmanager
    async def noop_download_context(_media_item: MediaItem):
        yield

    start_hls_download = mock.AsyncMock()
    monkeypatch.setattr(downloader, "_download_context", noop_download_context)
    monkeypatch.setattr(downloader, "_start_hls_download", start_hls_download)
    monkeypatch.setattr(ffmpeg, "check_is_available", lambda: None)

    await downloader.download_hls(media_item, object())
    start_hls_download.assert_not_awaited()


async def test_impersonated_download_checks_curl_availability_before_using_session(manager) -> None:
    error = RuntimeError("curl unavailable")
    fake_client_manager = mock.Mock()
    fake_client_manager.check_curl_cffi_is_available.side_effect = error
    download_client = DownloadClient(manager, fake_client_manager)

    with pytest.raises(RuntimeError, match="curl unavailable"):
        async with download_client._DownloadClient__request_context(AbsoluteHttpURL("https://example.com"), "vsco", {}):
            pass

    fake_client_manager.check_curl_cffi_is_available.assert_called_once_with()
