import asyncio
import os
from pathlib import Path
from http.cookies import SimpleCookie
import pytest
from multidict import CIMultiDict, CIMultiDictProxy
import yarl

from cyberdrop_dl.url_objects import AbsoluteHttpURL, MediaItem
from cyberdrop_dl.utils.m3u8 import M3U8, HLSKey
from cyberdrop_dl.scrape_source import _regex_links
from cyberdrop_dl.crawlers.crawler import compose_title
from cyberdrop_dl.config import Config
from cyberdrop_dl.crawlers._forum import clean_link_str
from cyberdrop_dl.downloader.http import Capacity


def test_regex_links_invalid_url_no_crash() -> None:
    urls = list(_regex_links("https://example.com:99999/test https://valid.com/image.png"))
    assert len(urls) == 1
    assert str(urls[0]) == "https://valid.com/image.png"


def test_hls_relative_key_uri_and_default_iv() -> None:
    content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:42
#EXT-X-KEY:METHOD=AES-128,URI="keys/video.key"
#EXTINF:10,
seg1.ts
#EXT-X-ENDLIST
"""
    m = M3U8(content, base_uri=AbsoluteHttpURL("https://cdn.example.com/hls/master.m3u8"))
    key = HLSKey.parse(m.segments[0])
    assert key is not None
    assert key.uri == AbsoluteHttpURL("https://cdn.example.com/hls/keys/video.key")
    assert key.iv == (42).to_bytes(16, "big")


def test_compose_title_collapses_whitespace() -> None:
    config = Config()
    title = compose_title(config, "example.com", "My    Test   Title", album_id="123", force_album_id=True)
    assert "    " not in title
    assert "  " not in title
    assert title == "My Test Title 123 (example.com)"


def test_clean_link_str_preserves_unrelated_ifr() -> None:
    assert clean_link_str("https://example.com/ifr/12345") == "https://example.com/watch/12345"
    assert clean_link_str("https://example.com/boyfriend/pic.jpg") == "https://example.com/boyfriend/pic.jpg"
    assert clean_link_str("https://example.com/different/pic.th.jpg") == "https://example.com/different/pic.jpg"


async def test_capacity_wait_notifies_all_waiters() -> None:
    cap = Capacity(limit=2)
    cap.waiting = 3
    woken = []

    async def worker(idx: int) -> None:
        await cap.wait("test")
        woken.append(idx)

    tasks = [asyncio.create_task(worker(i)) for i in range(4)]
    await asyncio.sleep(0)
    assert len(woken) == 0

    cap.waiting = 2
    async with cap.condition:
        cap.condition.notify_all()
    await asyncio.sleep(0.01)

    assert len(woken) == 4
    for t in tasks:
        t.cancel()

