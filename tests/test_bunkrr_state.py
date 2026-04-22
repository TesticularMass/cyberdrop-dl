from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cyberdrop_dl.crawlers.bunkrr import HOST_OPTIONS, BunkrrCrawler
from cyberdrop_dl.data_structures.url_objects import AbsoluteHttpURL


@pytest.mark.asyncio
async def test_new_bunkrr_crawler_does_not_inherit_bad_hosts(manager, monkeypatch) -> None:
    first = BunkrrCrawler(manager)
    second = BunkrrCrawler(manager)
    url = AbsoluteHttpURL("https://bunkr.site/a/test")

    async def fail_and_mark_bad(request_url):
        first.known_bad_hosts.add(request_url.host)
        return None

    monkeypatch.setattr(first, "_try_request_soup", fail_and_mark_bad)
    monkeypatch.setattr(first, "request_soup", AsyncMock(side_effect=RuntimeError("all hosts failed")))

    with pytest.raises(RuntimeError, match="all hosts failed"):
        await first._request_soup_lenient(url)

    assert first.known_bad_hosts == HOST_OPTIONS
    assert not second.known_bad_hosts

    second_try = AsyncMock(return_value=object())
    monkeypatch.setattr(second, "_try_request_soup", second_try)
    monkeypatch.setattr(
        second,
        "request_soup",
        AsyncMock(side_effect=AssertionError("fresh crawler should retry hosts before falling back")),
    )

    await second._request_soup_lenient(url)

    second_try.assert_awaited()
