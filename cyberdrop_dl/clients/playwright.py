from __future__ import annotations

import asyncio
import logging
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING

from multidict import CIMultiDict, CIMultiDictProxy
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from cyberdrop_dl.clients.flaresolverr import Solution
from cyberdrop_dl.url_objects import AbsoluteHttpURL

if TYPE_CHECKING:
    from collections.abc import Iterable
    from http.cookies import Morsel

    from playwright.async_api import Browser, Playwright, PlaywrightContextManager, Response

logger = logging.getLogger(__name__)


class PlaywrightClient:
    def __init__(self, *, headless: bool = True) -> None:
        self.headless = headless
        self._pw: Playwright | None = None
        self._pw_cm: PlaywrightContextManager | None = None
        self._browser: Browser | None = None
        self._startup_lock = asyncio.Lock()

    async def _start(self) -> None:
        async with self._startup_lock:
            if self._pw is None:
                self._pw_cm = async_playwright()
                self._pw = await self._pw_cm.__aenter__()
            if self._browser is None:
                self._browser = await self._pw.chromium.launch(headless=self.headless)
                logger.debug("Started Playwright Chromium (headless=%s)", self.headless)

    async def aclose(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            assert self._pw_cm is not None
            await self._pw_cm.__aexit__(None, None, None)
            self._pw = None
            self._pw_cm = None

    async def request(
        self,
        url: AbsoluteHttpURL,
        *,
        user_agent: str | None = None,
        cookies: Iterable[Morsel[str]] | None = None,
    ) -> Solution:
        """Navigate to a page and wait for browser challenges to clear."""
        logger.debug("Playwright request: %s", url)
        await self._start()
        assert self._browser is not None
        context = await self._browser.new_context(user_agent=user_agent)
        try:
            if cookies:
                await context.add_cookies(
                    [
                        {
                            "name": cookie.key,
                            "value": cookie.value,
                            "domain": cookie["domain"] or url.host,
                            "path": cookie["path"] or "/",
                            "secure": bool(cookie["secure"]),
                            "httpOnly": bool(cookie["httponly"]),
                        }
                        for cookie in cookies
                    ]
                )

            page = await context.new_page()
            resp: Response | None = None

            def document_response(response: Response) -> None:
                nonlocal resp
                if response.request.is_navigation_request() and response.frame == page.main_frame:
                    resp = response

            page.on("response", document_response)
            logger.info("Playwright navigating to %s", url)
            initial_response = await page.goto(str(url), wait_until="domcontentloaded")
            resp = resp or initial_response
            if resp is None:
                raise RuntimeError(f"Playwright got no response from {url}")

            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.wait_for_function(
                    "() => !/just a moment|ddos-guard|cloudflare/i.test(document.title)", timeout=15000
                )
            except PlaywrightTimeoutError:
                # HTTPClient validates the page and rejects unsolved challenges.
                pass

            content = await page.content()
            simple_cookies = SimpleCookie()
            for cookie in await context.cookies():
                name, value = cookie.get("name"), cookie.get("value")
                if name is None or value is None:
                    continue
                simple_cookies[name] = value
                morsel = simple_cookies[name]
                morsel["domain"] = cookie.get("domain", "")
                morsel["path"] = cookie.get("path", "/")
                morsel["secure"] = bool(cookie.get("secure"))
                morsel["httponly"] = bool(cookie.get("httpOnly"))

            return Solution(
                content=content,
                cookies=simple_cookies,
                headers=CIMultiDictProxy(CIMultiDict(resp.headers)),
                url=AbsoluteHttpURL(page.url),
                user_agent=user_agent or "",
                status=resp.status,
            )
        finally:
            await context.close()
