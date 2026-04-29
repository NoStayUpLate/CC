"""NetShort 短剧首页栏位爬虫。"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .shortdrama_base import BaseShortDramaScraper


class NetShortScraper(BaseShortDramaScraper):
    platform = "netshort"
    lang = "en"
    list_url = "https://netshort.com/en"
    section_limit = 10
    section_order = ["轮播推荐", "推荐栏位", "最近上新"]

    async def scrape(self, genre: str = "", limit: int = 10) -> list[dict]:
        html = await self._get_html(self.list_url, extra_headers={"Accept": "text/html"})
        items = self._parse_homepage(html, self.list_url, limit)
        items = await self._enrich_items_from_detail_pages(items)
        return items[: limit * len(self.section_order)]

    def _parse_homepage(self, html: str, source_url: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        seen: set[tuple[str, str]] = set()
        title_to_url: dict[str, str] = {}
        title_to_cover: dict[str, str] = {}
        title_to_tags: dict[str, list[str]] = {}

        for a in soup.select("a[href]"):
            title = self._clean_title(a.get_text(" ", strip=True))
            href = (a.get("href") or "").strip()
            if not title or not href or "/episode/" not in href:
                continue
            if not self._is_valid_title(title):
                continue
            if href.startswith("/"):
                normalized = "https://netshort.com" + href
            elif href.startswith("http"):
                normalized = href
            else:
                normalized = "https://netshort.com/" + href.lstrip("/")
            title_to_url[title] = normalized
            title_to_cover[title] = self._extract_image_url(a, "https://netshort.com")
            title_to_tags[title] = self._extract_nearby_tags(a, include_drama_links=True)

        section_label = "轮播推荐"
        section_items: dict[str, list[dict]] = {sec: [] for sec in self.section_order}
        for node in soup.find_all(["h1", "h2", "h3", "a"]):
            if node.name in {"h1", "h2", "h3"}:
                text = self._clean_title(node.get_text(" ", strip=True))
                low = text.lower()
                if low == "new releases":
                    section_label = "最近上新"
                elif low == "recommended":
                    section_label = "推荐栏位"
                elif low in {"exclusive originals", "you might like"}:
                    section_label = ""
                elif low == "trending now" and section_label == "轮播推荐":
                    section_label = ""
                continue

            href = (node.get("href") or "").strip()
            if not section_label or "/episode/" not in href:
                continue
            title = self._clean_title(node.get_text(" ", strip=True))
            if not self._is_valid_title(title):
                continue
            unique_key = (section_label, title)
            if unique_key in seen:
                continue
            seen.add(unique_key)

            summary = ""
            nxt = node.find_next("p")
            if nxt:
                summary = nxt.get_text(" ", strip=True)[:320]

            section_items[section_label].append(
                {
                    "title": title,
                    "summary": summary,
                    "cover_url": title_to_cover.get(title, ""),
                    "tags": self._merge_tags([section_label], title_to_tags.get(title, [])),
                    "episodes": None,
                    "rank_type": section_label,
                    "source_url": title_to_url.get(title, source_url),
                }
            )

        out: list[dict] = []
        for sec in self.section_order:
            for idx, item in enumerate(section_items[sec][:limit], start=1):
                item["rank_in_platform"] = idx
                out.append(item)
        return out
