from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from multidict import CIMultiDict

from cyberdrop_dl.clients.playwright import PlaywrightClient
from cyberdrop_dl.url_objects import AbsoluteHttpURL


@pytest.fixture
def playwright_client() -> PlaywrightClient:
    return PlaywrightClient(headless=True)


@pytest.mark.asyncio
async def test_playwright_request(playwright_client: PlaywrightClient) -> None:
    url = AbsoluteHttpURL("https://example.com/test")
    user_agent = "TestAgent/1.0"

    mock_pw = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.on = MagicMock()
    mock_resp = AsyncMock()

    mock_resp.status = 200
    mock_resp.headers = CIMultiDict({"Content-Type": "text/html"})
    mock_page.goto.return_value = mock_resp
    mock_page.title.return_value = "Success Page"
    mock_page.content.return_value = "<html>Success</html>"
    mock_page.url = str(url)
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "test_val"}]

    mock_context.new_page.return_value = mock_page
    mock_browser.new_context.return_value = mock_context
    mock_pw.chromium.launch.return_value = mock_browser

    with patch("cyberdrop_dl.clients.playwright.async_playwright") as mock_async_pw:
        # async_playwright returns an async context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_pw
        mock_async_pw.return_value = mock_cm

        solution = await playwright_client.request(url, user_agent=user_agent)

        # Assertions
        assert solution.url == url
        assert solution.status == 200
        assert solution.content == "<html>Success</html>"
        assert solution.user_agent == user_agent
        assert "cf_clearance" in solution.cookies
        assert solution.cookies["cf_clearance"].value == "test_val"

        # Verify playwright was called correctly
        mock_browser.new_context.assert_called_once_with(user_agent=user_agent)
        mock_page.goto.assert_called_once_with(str(url), wait_until="domcontentloaded")
        mock_page.wait_for_load_state.assert_called_once_with("networkidle", timeout=15000)

    await playwright_client.aclose()
    mock_browser.close.assert_called_once()


async def test_browser_preserves_cookie_scope(playwright_client):
    browser = AsyncMock()
    context = browser.new_context.return_value
    page = context.new_page.return_value
    page.on = MagicMock()
    page.goto.return_value.status = 200
    page.goto.return_value.headers = {"Content-Type": "text/html"}
    page.title.return_value = "Success"
    page.content.return_value = "<html>Success</html>"
    page.url = "https://example.com/test"
    context.cookies.return_value = [
        {"name": "session", "value": "secret", "domain": ".example.com", "path": "/private", "secure": True},
    ]
    playwright_client._browser = browser
    with patch.object(playwright_client, "_start", AsyncMock()):
        result = await playwright_client.request(AbsoluteHttpURL(page.url))
    assert result.cookies["session"]["domain"] == ".example.com"
    assert result.cookies["session"]["path"] == "/private"
    assert result.cookies["session"]["secure"]


async def test_browser_closes_context_when_page_creation_fails(playwright_client):
    browser = AsyncMock()
    context = browser.new_context.return_value
    context.new_page.side_effect = RuntimeError("page creation failed")
    playwright_client._browser = browser
    with (
        patch.object(playwright_client, "_start", AsyncMock()),
        pytest.raises(RuntimeError, match="page creation failed"),
    ):
        await playwright_client.request(AbsoluteHttpURL("https://example.com/"))
    context.close.assert_awaited_once()


async def test_concurrent_browser_start_launches_once(playwright_client):
    import asyncio

    pw = AsyncMock()

    async def enter():
        await asyncio.sleep(0)
        return pw

    with patch("cyberdrop_dl.clients.playwright.async_playwright") as factory:
        cm = AsyncMock()
        cm.__aenter__.side_effect = enter
        factory.return_value = cm
        await asyncio.gather(playwright_client._start(), playwright_client._start())
        pw.chromium.launch.assert_awaited_once()
    await playwright_client.aclose()


async def test_browser_uses_final_navigation_status(playwright_client):
    browser = AsyncMock()
    context = browser.new_context.return_value
    page = context.new_page.return_value
    page.on = MagicMock()
    page.on = MagicMock()
    page.goto.return_value.status = 403
    page.goto.return_value.headers = {"Content-Type": "text/html"}
    page.url = "https://example.com/"
    page.title.return_value = "Success"
    page.content.return_value = "<html>Success</html>"
    context.cookies.return_value = []
    final_response = MagicMock()
    final_response.status = 200
    final_response.headers = {"Content-Type": "text/html"}
    final_response.frame = page.main_frame
    final_response.request.is_navigation_request.return_value = True

    async def load(*_args, **_kwargs):
        for call in page.on.call_args_list:
            if call.args[0] == "response":
                call.args[1](final_response)

    page.wait_for_load_state.side_effect = load
    playwright_client._browser = browser
    with patch.object(playwright_client, "_start", AsyncMock()):
        result = await playwright_client.request(AbsoluteHttpURL(page.url))
    assert result.status == 200
