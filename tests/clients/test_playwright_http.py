import contextlib
from http.cookies import SimpleCookie
from unittest.mock import AsyncMock

import pytest
from multidict import CIMultiDict, CIMultiDictProxy

from cyberdrop_dl.clients.flaresolverr import Solution
from cyberdrop_dl.clients.http import HTTPClient
from cyberdrop_dl.clients.response import AbstractResponse
from cyberdrop_dl.config import Config
from cyberdrop_dl.exceptions import DownloadError
from cyberdrop_dl.url_objects import AbsoluteHttpURL


def solution(status=200, content="<html>Success</html>"):
    return Solution(
        content=content,
        cookies=SimpleCookie(),
        headers=CIMultiDictProxy(CIMultiDict({"Content-Type": "text/html"})),
        url=AbsoluteHttpURL("https://example.com/test"),
        user_agent=Config().network.user_agent,
        status=status,
    )


async def test_playwright_fallback_rejects_http_errors(monkeypatch):
    client = HTTPClient(Config())
    client.config.network.playwright = True
    monkeypatch.setattr(client.playwright, "request", AsyncMock(return_value=solution(403)))
    with pytest.raises(DownloadError):
        await client._playwright_request(AbsoluteHttpURL("https://example.com/test"))


async def test_playwright_retries_original_post_after_browser_challenge(monkeypatch):
    client = HTTPClient(Config())
    client.config.network.playwright = True
    monkeypatch.setattr(client.playwright, "request", AsyncMock(return_value=solution()))
    requests = []

    @contextlib.asynccontextmanager
    async def raw_request(url, method="GET", **kwargs):
        requests.append((url, method, kwargs))
        yield AbstractResponse.create(solution(403 if len(requests) == 1 else 200, "original POST response"))

    monkeypatch.setattr(client, "raw_request", raw_request)
    url = AbsoluteHttpURL("https://example.com/test")
    async with client.request(url, "POST", json={"id": 123}, headers={"X-Test": "value"}) as response:
        assert await response.text() == "original POST response"
    assert len(requests) == 2
    assert requests[0] == requests[1]


async def test_playwright_cookies_are_not_sent_to_other_hosts(monkeypatch):
    client = HTTPClient(Config())
    client.config.network.playwright = True
    result = solution()
    result.cookies["session"] = "private-session"
    monkeypatch.setattr(client.playwright, "request", AsyncMock(return_value=result))
    await client._playwright_request(result.url)
    assert client.cookies.filter_cookies(result.url)["session"].value == "private-session"
    assert "session" not in client.cookies.filter_cookies(AbsoluteHttpURL("https://other.example/"))


async def test_playwright_replays_implicit_form_post(monkeypatch):
    client = HTTPClient(Config())
    client.config.network.playwright = True
    monkeypatch.setattr(client.playwright, "request", AsyncMock(return_value=solution()))
    requests = []

    @contextlib.asynccontextmanager
    async def raw_request(url, method="GET", **kwargs):
        requests.append((url, method, kwargs))
        yield AbstractResponse.create(solution(403 if len(requests) == 1 else 200, "form response"))

    monkeypatch.setattr(client, "raw_request", raw_request)
    async with client.request(AbsoluteHttpURL("https://example.com/test"), data={"id": 123}) as response:
        assert await response.text() == "form response"
    assert len(requests) == 2
    assert requests[0] == requests[1]


async def test_playwright_replay_uses_browser_cookie_transport(monkeypatch):
    client = HTTPClient(Config())
    client.config.network.playwright = True
    result = solution()
    result.cookies["session"] = "browser-cookie"
    monkeypatch.setattr(client.playwright, "request", AsyncMock(return_value=result))
    requests = []

    @contextlib.asynccontextmanager
    async def request_transport(request):
        requests.append(request)
        if len(requests) > 1:
            assert request.impersonate is False
            assert request.headers["User-Agent"] == result.user_agent
            assert client.cookies.filter_cookies(request.url)["session"].value == "browser-cookie"
        yield AbstractResponse.create(solution(403 if len(requests) == 1 else 200, "POST response"))

    monkeypatch.setattr(client, "_request", request_transport)
    async with client.request(result.url, "POST", data={"id": 123}, impersonate=True) as response:
        assert await response.text() == "POST response"
    assert len(requests) == 2
