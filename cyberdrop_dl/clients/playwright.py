from __future__ import annotations

import asyncio
import logging
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING, Any

from multidict import CIMultiDict, CIMultiDictProxy
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from cyberdrop_dl.clients.flaresolverr import Solution
from cyberdrop_dl.url_objects import AbsoluteHttpURL

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)


class PlaywrightClient:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._pw: Playwright | None = None
        self._browser: Browser | None = None

    async def _start(self) -> None:
        if not self._pw:
            self._pw_cm = async_playwright()
            self._pw = await self._pw_cm.__aenter__()
            self._browser = await self._pw.chromium.launch(headless=self.headless)
            logger.debug("Started Playwright Chromium (headless=%s)", self.headless)

    async def aclose(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw_cm.__aexit__(None, None, None)
            self._pw = None

    async def request(self, url: AbsoluteHttpURL, data: Any = None, user_agent: str | None = None, cookies: Any = None) -> Solution:
        """Navigates to URL using Playwright and waits for Cloudflare/DDos-Guard to be bypassed."""
        print("PLAYWRIGHT CLIENT REQUEST CALLED", flush=True)
        await self._start()
        assert self._browser is not None

        context: BrowserContext = await self._browser.new_context(user_agent=user_agent)
        
        if cookies:
            pw_cookies = []
            for cookie in cookies:
                pw_cookies.append({
                    "name": cookie.key,
                    "value": cookie.value,
                    "domain": cookie["domain"] or url.host,
                    "path": cookie["path"] or "/"
                })
            if pw_cookies:
                await context.add_cookies(pw_cookies)

        page: Page = await context.new_page()
        try:
            logger.info("Playwright navigating to %s", url)
            # We don't support POST data via Playwright easily for initial navigation,
            # but usually anti-bot is encountered on GET requests (e.g. initial thread load).
            resp = await page.goto(str(url), wait_until="domcontentloaded")
            
            if resp is None:
                raise RuntimeError(f"Playwright got no response from {url}")

            status = resp.status
            
            logger.debug("Playwright waiting for Anti-bot challenges to clear...")
            
            # Wait for DDOS-Guard or Cloudflare turnstile to disappear.
            # Usually Cloudflare has title "Just a moment..." and DDOS Guard redirects or has specific div.
            # A simple heuristic: wait until network is mostly idle.
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightError:
                pass # Timeout is fine, we just hope it's loaded

            # Sometimes Cloudflare needs more time
            title = await page.title()
            if "Just a moment..." in title or "DDOS-GUARD" in title or "Cloudflare" in title:
                logger.debug("Still challenged, waiting up to 15s...")
                try:
                    await page.wait_for_selector('body:not(.no-js)', timeout=15000)
                except PlaywrightError:
                    pass

            content = await page.content()
            pw_cookies = await context.cookies()
            
            # Convert Playwright cookies to SimpleCookie
            simple_cookies = SimpleCookie()
            for c in pw_cookies:
                simple_cookies[c["name"]] = c["value"]

            # Headers - Playwright doesn't expose response headers cleanly after JS modifications,
            # but we can grab the initial response headers.
            headers = CIMultiDictProxy(CIMultiDict(resp.headers))
            
            final_url = AbsoluteHttpURL(page.url)

            return Solution(
                content=content,
                cookies=simple_cookies,
                headers=headers,
                url=final_url,
                user_agent=user_agent or "",
                status=resp.status,
            )
        finally:
            await page.close()
            await context.close()
