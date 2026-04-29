"""ReelShort 短剧首页爬虫。"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .shortdrama_base import BaseShortDramaScraper


class ReelShortScraper(BaseShortDramaScraper):
    platform = "reelshort"
    lang = "en"
    list_url = "https://www.reelshort.com/"
    section_limit = 5
    section_order = ["最近上新"]

    async def scrape(self, genre: str = "", limit: int = 5) -> list[dict]:
        html = await self._get_html(self.list_url, extra_headers={"Accept": "text/html"})
        soup = BeautifulSoup(html, "html.parser")
        items = self._parse_section_by_headings(
            soup=soup,
            source_url=self.list_url,
            limit=limit,
            link_keyword="/episodes/",
            base_url="https://www.reelshort.com",
            normalize_url=self._normalize_reelshort_url,
        )
        items = await self._enrich_items_from_detail_pages(items)
        return items[:limit]
