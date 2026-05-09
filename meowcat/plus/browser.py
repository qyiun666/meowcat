# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus Browser tool — Playwright-based browser automation.

Provides headless (or headed) browser control for web interaction tasks:
navigate, click, type, screenshot, and content extraction.

Usage::

    from meowcat.plus.browser import BrowserTool

    browser = BrowserTool(headless=True)
    await browser.start()
    html = await browser.navigate("https://example.com")
    await browser.click("#submit")
    await browser.close()

    # or as context manager
    async with BrowserTool(headless=True) as browser:
        content = await browser.navigate("https://example.com")
"""

from __future__ import annotations

import logging
from pathlib import Path

from meowcat.constants import (
    BROWSER_MAX_HTML_CHARS,
    BROWSER_MAX_RESULT_CHARS,
    BROWSER_MAX_TEXT_CHARS,
)

logger = logging.getLogger(__name__)


class BrowserTool:
    """Playwright-powered browser automation tool.

    Lazily imports Playwright on first use. Supports headless
    and headed modes with common browser actions.

    Args:
        headless: Run browser without a visible window (default True).
        browser_type: ``"chromium"`` | ``"firefox"`` | ``"webkit"`` (default chromium).
        viewport_width: Browser viewport width in pixels (default 1280).
        viewport_height: Browser viewport height in pixels (default 720).

    Implements ``diagnose()`` for :class:`meowcat.diagnose.Stethoscope`.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        browser_type: str = "chromium",
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> None:
        self._headless = headless
        self._browser_type = browser_type
        self._viewport_width = viewport_width
        self._viewport_height = viewport_height
        self._pw_func: object | None = None  # async_playwright factory
        self._playwright: object | None = None  # Playwright instance
        self._browser: object | None = None
        self._page: object | None = None
        self._started: bool = False

    # -- Diagnosable interface ---------------------------------------

    def diagnose(self) -> dict[str, object]:
        """Read-only snapshot for Stethoscope probing."""
        return {
            "started": self._started,
            "browser_type": self._browser_type,
            "headless": self._headless,
            "viewport": f"{self._viewport_width}x{self._viewport_height}",
        }

    # -- Lifecycle ---------------------------------------------------

    async def start(self) -> None:
        """Start the browser and create a new page.

        Installs Playwright browsers on first run if needed.
        """
        if self._started:
            return

        pw_func = self._get_playwright()
        # type: ignore[union-attr]
        self._playwright = await pw_func().__aenter__()  # type: ignore[operator]
        browser_launcher = getattr(self._playwright, self._browser_type)
        self._browser = await browser_launcher.launch(
            headless=self._headless,
        )
        self._page = await self._browser.new_page(  # type: ignore[union-attr]
            viewport={"width": self._viewport_width, "height": self._viewport_height},
        )
        self._started = True
        logger.info(
            "Browser started: %s (headless=%s)",
            self._browser_type,
            self._headless,
        )

    async def close(self) -> None:
        """Close the browser and release resources."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()  # type: ignore[union-attr]
            self._playwright = None
        self._page = None
        self._started = False
        logger.info("Browser closed")

    async def __aenter__(self) -> BrowserTool:
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # -- Browser actions ---------------------------------------------

    async def navigate(self, url: str) -> str:
        """Navigate to a URL and return the page text content.

        Args:
            url: Full URL to navigate to (e.g. ``https://example.com``).

        Returns:
            Page text content (max BROWSER_MAX_TEXT_CHARS chars).
        """
        page = self._require_page()
        await page.goto(url, wait_until="domcontentloaded")
        content = await page.text_content("body") or ""
        return content[:BROWSER_MAX_TEXT_CHARS]

    async def click(self, selector: str) -> str:
        """Click an element matching the CSS selector.

        Args:
            selector: CSS selector (e.g. ``#submit``, ``.btn-primary``).

        Returns:
            Page text content after click (max BROWSER_MAX_TEXT_CHARS chars).
        """
        page = self._require_page()
        await page.click(selector)
        content = await page.text_content("body") or ""
        return content[:BROWSER_MAX_TEXT_CHARS]

    async def type_text(self, selector: str, text: str) -> str:
        """Type text into an input element.

        Args:
            selector: CSS selector for the input element.
            text: Text to type.

        Returns:
            Current page text content (max BROWSER_MAX_TEXT_CHARS chars).
        """
        page = self._require_page()
        await page.fill(selector, text)
        content = await page.text_content("body") or ""
        return content[:BROWSER_MAX_TEXT_CHARS]

    async def screenshot(
        self,
        path: str | Path | None = None,
        *,
        full_page: bool = False,
    ) -> bytes:
        """Take a screenshot of the current page.

        Args:
            path: File path to save screenshot. If None, returns bytes.
            full_page: Capture the full scrollable page.

        Returns:
            Screenshot as PNG bytes.
        """
        page = self._require_page()
        kwargs: dict[str, object] = {"full_page": full_page}
        if path is not None:
            kwargs["path"] = str(path)
        return await page.screenshot(**kwargs)  # type: ignore[arg-type]

    async def get_content(self) -> str:
        """Get the full HTML content of the current page.

        Returns:
            Page HTML content (max BROWSER_MAX_HTML_CHARS chars).
        """
        page = self._require_page()
        content = await page.content()
        return content[:BROWSER_MAX_HTML_CHARS]

    async def get_text(self, selector: str = "body") -> str:
        """Get text content of an element.

        Args:
            selector: CSS selector (default ``"body"``).

        Returns:
            Element text content (max BROWSER_MAX_TEXT_CHARS chars).
        """
        page = self._require_page()
        text = await page.text_content(selector) or ""
        return text[:BROWSER_MAX_TEXT_CHARS]

    async def evaluate(self, expression: str) -> str:
        """Execute JavaScript in the page context.

        Args:
            expression: JavaScript expression to evaluate.

        Returns:
            Result as string.
        """
        page = self._require_page()
        result = await page.evaluate(expression)
        return str(result)[:BROWSER_MAX_RESULT_CHARS]

    # -- Internal helpers --------------------------------------------

    def _require_page(self) -> object:
        """Ensure browser is started, return the active page."""
        if not self._started or self._page is None:
            raise RuntimeError("Browser not started. Call await browser.start() first.")
        return self._page

    def _get_playwright(self) -> object:
        """Lazy-import Playwright factory function."""
        if self._pw_func is not None:
            return self._pw_func
        try:
            # type: ignore[import-untyped]
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "playwright not installed. Install with: pip install playwright && "
                "playwright install chromium"
            ) from None
        self._pw_func = async_playwright
        return self._pw_func
