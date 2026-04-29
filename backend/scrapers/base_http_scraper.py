"""
HTTP/REST API 爬虫抽象基类：封装重试、代理回退与请求头管理。

子类实现 scrape() 方法，通过 _get_json() / _get_html() 发起请求。
"""
import asyncio
import logging
import random
from abc import abstractmethod

import requests

from .base_scraper import BaseScraper
from config import settings

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

_DEFAULT_HEADERS = {
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _sync_get(url: str, proxy: str | None, headers: dict) -> requests.Response:
    """同步 GET，最多重试 3 次；代理握手失败或 SSL EOF 时回退直连。"""
    import time
    proxies = {"http": proxy, "https": proxy} if proxy else None
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=45)
            resp.raise_for_status()
            return resp
        except requests.exceptions.Timeout as e:
            last_exc = e
            if attempt < 2:
                time.sleep(2 ** attempt)
        except (requests.exceptions.ProxyError, requests.exceptions.SSLError) as e:
            last_exc = e
            proxies = None          # 回退直连后重试
            if attempt < 2:
                time.sleep(2 ** attempt)
        except requests.exceptions.ConnectionError as e:
            last_exc = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise last_exc
    raise RuntimeError(f"Failed to fetch {url} after 3 attempts")


class BaseHttpScraper(BaseScraper):
    """HTTP/REST API 驱动的爬虫基类，含重试与代理回退逻辑。"""

    @property
    def _proxy(self) -> str | None:
        return settings.http_proxy or None

    def _build_headers(self, extra: dict | None = None) -> dict:
        """构造请求头，随机选取 User-Agent。"""
        h = {**_DEFAULT_HEADERS, "User-Agent": random.choice(_USER_AGENTS)}
        if extra:
            h.update(extra)
        return h

    async def _get_json(self, url: str, extra_headers: dict | None = None) -> dict:
        """异步 GET 并解析 JSON，含重试与代理回退。"""
        headers = self._build_headers(extra_headers)
        resp = await asyncio.to_thread(_sync_get, url, self._proxy, headers)
        return resp.json()

    async def _get_html(self, url: str, extra_headers: dict | None = None) -> str:
        """异步 GET 并返回 HTML 文本，含重试与代理回退。"""
        headers = self._build_headers(extra_headers)
        resp = await asyncio.to_thread(_sync_get, url, self._proxy, headers)
        return resp.text

    @abstractmethod
    async def scrape(self, genre: str = "", limit: int = 50) -> list[dict]:
        """子类实现具体抓取逻辑（含分页）。"""
        ...
