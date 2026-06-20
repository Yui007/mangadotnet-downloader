"""Cloudflare-aware API client for MangaDotNet.

Architecture (based on working test.py pattern):
1. Launch undetected_chromedriver, solve CF at mangadot.net
2. Warm session by visiting a manga page
3. Use fetch() from within the page with proper headers for all API calls
4. Keep browser alive — CF clearance is bound to TLS fingerprint
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from typing import Any

from manga_dotnet.core.config import Config
from manga_dotnet.core.exceptions import ConnectionError

logger = logging.getLogger(__name__)

# JavaScript template for fetch() calls — matches the working test.py pattern
_FETCH_JS = """
async function _fetchApi(url) {
    const r = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'accept': 'application/json',
            'x-requested-with': 'XMLHttpRequest',
            'referer': window.location.href
        }
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.text();
}
return await _fetchApi(arguments[0]);
"""


class MangaDotNetClient:
    """Cloudflare-aware API client for MangaDotNet.

    Uses undetected_chromedriver to solve CF, warms the session,
    then uses fetch() from within the browser page for API calls.
    """

    BASE_URL = "https://mangadot.net"
    API_BASE = "https://mangadot.net/api"

    def __init__(self, config: Config):
        self.config = config
        self._driver: Any = None
        self._initialized = False
        self._driver_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Cloudflare bypass + session warming
    # ------------------------------------------------------------------

    def _solve_cloudflare(self) -> None:
        """Launch browser, solve CF, and warm the session."""
        import undetected_chromedriver as uc

        self._close_driver()

        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.page_load_strategy = "eager"

        chrome_version = self._detect_chrome_version()
        logger.info("Detected Chrome version: %s", chrome_version)

        kwargs: dict[str, Any] = {"options": options}
        if chrome_version:
            kwargs["version_main"] = chrome_version

        self._driver = uc.Chrome(**kwargs)
        self._driver.get(self.BASE_URL)

        # Poll for cf_clearance or title change — max 120 × 0.5s = 60s
        for _ in range(120):
            cookies = self._driver.get_cookies()
            cf_clearance = next(
                (c["value"] for c in cookies if c["name"] == "cf_clearance"),
                None,
            )
            title = ""
            try:
                title = self._driver.title
            except Exception:
                pass

            if cf_clearance or (title and "Just a moment" not in title and "Cloudflare" not in title and "Attention Required" not in title):
                logger.info("Cloudflare bypass detected (clearance_cookie=%s, title=%r)", cf_clearance is not None, title)
                break
            time.sleep(0.5)
        else:
            raise ConnectionError(
                "Failed to solve Cloudflare challenge",
                suggestion="Ensure Chrome is installed and try again.",
            )

        logger.info("Cloudflare challenge solved")

        # Warm session — visit a manga page to establish session context
        self._warm_session()

    def _warm_session(self) -> None:
        """Warm the session by visiting a manga page.

        This is critical — the API calls won't work without first
        establishing a proper session on the site.
        """
        logger.info("Warming session...")
        try:
            self._driver.get(f"{self.BASE_URL}/manga/166")
            # Wait dynamically for document readyState
            for _ in range(10):
                state = self._driver.execute_script("return document.readyState")
                if state == "complete":
                    break
                time.sleep(0.5)
        except Exception as e:
            logger.warning("Session warming navigation failed: %s", e)
        logger.info("Session warmed")

    def _close_driver(self) -> None:
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def initialize(self) -> None:
        if self._initialized:
            return
        logger.info("Initializing MangaDotNet client...")
        self._solve_cloudflare()
        
        # Test if API is actually accessible (warmup check)
        logger.info("Verifying API accessibility...")
        test_url = f"{self.API_BASE}/manga/166"
        for i in range(20):
            try:
                res = self._fetch_json(test_url)
                if res and (isinstance(res, dict) or "title" in res or "manga" in res):
                    logger.info("API verification succeeded on attempt %d", i + 1)
                    break
            except Exception as e:
                logger.info("API verification attempt %d failed: %s. Retrying...", i + 1, e)
                time.sleep(0.5)
        else:
            raise ConnectionError(
                "API accessibility check failed after Cloudflare bypass.",
                suggestion="Restart the application or try again later."
            )
            
        self._initialized = True

    # ------------------------------------------------------------------
    # HTTP helpers — fetch() from within the browser page
    # ------------------------------------------------------------------

    def _fetch_json(self, url: str) -> Any:
        """Fetch JSON using fetch() inside the browser page."""
        with self._driver_lock:
            raw = self._driver.execute_script(_FETCH_JS, url)
        return json.loads(raw)

    def _get_json(self, path: str) -> Any:
        url = f"{self.API_BASE}{path}"
        return self._fetch_json(url)

    def get_image_bytes(self, url: str) -> bytes:
        """Download image bytes via XMLHttpRequest inside the browser.

        Uses XMLHttpRequest (not fetch()) because Cloudflare blocks
        fetch() for static image paths under /chapters/.
        """
        if not url.startswith("http"):
            url = f"{self.BASE_URL}{url}"

        js = """
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', arguments[0], true);
            xhr.responseType = 'arraybuffer';
            xhr.withCredentials = true;
            xhr.onload = function() {
                if (xhr.status === 200) {
                    const bytes = new Uint8Array(xhr.response);
                    let binary = '';
                    for (let i = 0; i < bytes.byteLength; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    resolve(btoa(binary));
                } else {
                    reject(new Error('HTTP ' + xhr.status));
                }
            };
            xhr.onerror = function() { reject(new Error('XHR network error')); };
            xhr.send();
        });
        """
        import base64
        with self._driver_lock:
            b64 = self._driver.execute_script(js, url)
        return base64.b64decode(b64)

    # ------------------------------------------------------------------
    # API Methods
    # ------------------------------------------------------------------

    def search(self, query: str, per_page: int = 500) -> Any:
        """Search manga — note: search endpoint is NOT under /api/."""
        url = f"{self.BASE_URL}/search.data?search={query}&perPage={per_page}"
        return self._fetch_json(url)

    def get_manga(self, manga_id: int) -> dict[str, Any]:
        return self._get_json(f"/manga/{manga_id}/")

    def get_chapters(self, manga_id: int) -> list[dict[str, Any]]:
        return self._get_json(f"/manga/{manga_id}/chapters/list")

    def get_volumes(self, manga_id: int) -> list[dict[str, Any]]:
        return self._get_json(f"/manga/{manga_id}/volumes")

    def get_images(self, chapter_id: int) -> dict[str, Any]:
        return self._get_json(f"/uploads/{chapter_id}/images")

    def close(self) -> None:
        self._close_driver()
        self._initialized = False

    # ------------------------------------------------------------------
    # Chrome version detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_chrome_version() -> int | None:
        candidates = []
        if os.name == "nt":
            for base in [
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                os.environ.get("LOCALAPPDATA", ""),
            ]:
                if base:
                    candidates.append(
                        os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
                    )
        else:
            candidates.extend([
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/snap/bin/chromium",
            ])

        for path in candidates:
            if not os.path.isfile(path):
                continue
            chrome_dir = os.path.dirname(path)
            if os.path.isdir(chrome_dir):
                for item in os.listdir(chrome_dir):
                    match = re.match(r"(\d+)\.\d+\.\d+\.\d+", item)
                    if match:
                        return int(match.group(1))
        return None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> MangaDotNetClient:
        self.initialize()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
