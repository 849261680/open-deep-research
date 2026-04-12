from __future__ import annotations

import asyncio
import html
import logging
import re

import requests

logger = logging.getLogger(__name__)


class ContentExtractionService:
    """Fetch and normalize webpage content for stronger evidence records."""

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            )
        }

    async def extract_content(self, url: str) -> str:
        if not url:
            return ""
        return await asyncio.to_thread(self._extract_content_sync, url)

    def _extract_content_sync(self, url: str) -> str:
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=8,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("内容抓取失败 %s: %s", url, exc)
            return ""

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            text = response.text.strip()
            return text[:3000]

        body = response.text
        body = re.sub(r"(?is)<script.*?>.*?</script>", " ", body)
        body = re.sub(r"(?is)<style.*?>.*?</style>", " ", body)
        body = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", body)
        body = re.sub(r"(?s)<[^>]+>", " ", body)
        body = html.unescape(body)
        body = re.sub(r"\s+", " ", body).strip()
        return body[:3000]


content_extraction_service = ContentExtractionService()
