from __future__ import annotations

from unittest import mock

import pytest

from cyberdrop_dl.crawlers import xhamster
from cyberdrop_dl.data_structures.url_objects import AbsoluteHttpURL, ScrapeItem


def _video_initials(*, mp4_url: str | None = None, hls_url: str | None = None) -> dict:
    sources: list[dict[str, str]] = []
    if mp4_url:
        sources.append({"url": mp4_url, "quality": "720p"})
    if hls_url:
        sources.append({"url": hls_url, "quality": "1080p"})

    return {
        "videoModel": {
            "idHashSlug": "xh123",
            "title": "Only HLS",
            "created": 1_700_000_000,
        },
        "xplayerSettings2": {
            "sources": {
                "standard": {
                    "h264": sources,
                }
            }
        },
    }


def test_parse_video_supports_hls_only_sources() -> None:
    video = xhamster._parse_video(_video_initials(hls_url="https://cdn.example/master.m3u8"))

    assert video.best_hls is not None
    assert video.best_hls.url == AbsoluteHttpURL("https://cdn.example/master.m3u8")
    assert video.best_mp4 is None


@pytest.mark.asyncio
async def test_video_uses_hls_when_mp4_sources_are_missing(manager) -> None:
    crawler = xhamster.XhamsterCrawler(manager)
    scrape_item = ScrapeItem(url=AbsoluteHttpURL("https://xhamster.com/videos/only-hls-xh123"))
    hls_group = object()

    with (
        mock.patch.object(crawler, "check_complete_from_referer", new=mock.AsyncMock(return_value=False)),
        mock.patch.object(
            crawler,
            "_get_window_initials",
            new=mock.AsyncMock(return_value=_video_initials(hls_url="https://cdn.example/master.m3u8")),
        ),
        mock.patch.object(
            crawler,
            "get_m3u8_from_playlist_url",
            new=mock.AsyncMock(return_value=(hls_group, object())),
        ) as get_playlist,
        mock.patch.object(crawler, "get_m3u8_from_index_url", new=mock.AsyncMock()) as get_index,
        mock.patch.object(crawler, "handle_file", new=mock.AsyncMock()) as handle_file,
    ):
        await crawler.video(scrape_item)

    get_playlist.assert_awaited_once_with(AbsoluteHttpURL("https://cdn.example/master.m3u8"))
    get_index.assert_not_awaited()
    handle_file.assert_awaited_once()
    assert handle_file.await_args.args[:2] == (
        scrape_item.url,
        scrape_item,
    )
    assert handle_file.await_args.kwargs["filename"] == "xh123.mp4"
    assert handle_file.await_args.kwargs["m3u8"] is hls_group
    assert "debrid_link" not in handle_file.await_args.kwargs
