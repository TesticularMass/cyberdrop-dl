from unittest.mock import AsyncMock, patch

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
