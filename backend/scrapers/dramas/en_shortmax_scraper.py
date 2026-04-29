"""ShortMax 英文首页与剧库页爬虫。"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .shortdrama_base import BaseShortDramaScraper


class ShortMaxScraper(BaseShortDramaScraper):
    platform = "shortmax"
    lang = "en"
    list_url = "https://www.shorttv.live/"
    library_url = "https://www.shorttv.live/dramas"
    section_limit = 10
    section_order = ["推荐栏位", "最近上新", "近期热门"]

    async def scrape(self, genre: str = "", limit: int = 10) -> list[dict]:
        home_html = await self._get_html(self.list_url, extra_headers={"Accept": "text/html"})
        library_html = await self._get_html(self.library_url, extra_headers={"Accept": "text/html"})
        items = self._parse_homepage(home_html, limit)
        items = self._fill_new_releases_from_library(items, library_html, limit)
        items = await self._enrich_items_from_detail_pages(items)
        return items[: limit * len(self.section_order)]

    def _parse_homepage(self, html: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        section_items: dict[str, list[dict]] = {sec: [] for sec in self.section_order}
        section_label = "推荐栏位"
        seen: set[tuple[str, str]] = set()

        for node in soup.find_all(["h1", "h2", "h3", "a"]):
            if node.name in {"h1", "h2", "h3"}:
                heading = self._clean_heading(node.get_text(" ", strip=True))
                low = heading.lower()
                if low == "new release":
                    section_label = "最近上新"
                elif low == "most popular":
                    section_label = "近期热门"
                elif heading and heading not in {"ShortMax"} and self._is_valid_title(heading):
                    continue
                continue

            href = (node.get("href") or "").strip()
            if not section_label or "/drama/" not in href:
                continue
            if len(section_items[section_label]) >= limit:
                continue
            item = self._make_item(node, section_label)
            if item is None:
                continue
            key = (section_label, item["title"].lower())
            if key in seen:
                continue
            seen.add(key)
            section_items[section_label].append(item)

        out: list[dict] = []
        for section in self.section_order:
            for idx, item in enumerate(section_items[section][:limit], start=1):
                item["rank_in_platform"] = idx
                out.append(item)
        return out

    def _fill_new_releases_from_library(
        self, items: list[dict], library_html: str, limit: int
    ) -> list[dict]:
        section_items: dict[str, list[dict]] = {sec: [] for sec in self.section_order}
        for item in items:
            if item.get("rank_type") in section_items:
                section_items[item["rank_type"]].append(item)

        if len(section_items["最近上新"]) < limit:
            for item in self._parse_listing_page(library_html, "最近上新", limit * 2):
                if len(section_items["最近上新"]) >= limit:
                    break
                key = item["title"].lower()
                if any(existing["title"].lower() == key for existing in section_items["最近上新"]):
                    continue
                section_items["最近上新"].append(item)

        out: list[dict] = []
        for section in self.section_order:
            for idx, item in enumerate(section_items[section][:limit], start=1):
                item["rank_in_platform"] = idx
                out.append(item)
        return out

    def _parse_listing_page(self, html: str, rank_type: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[dict] = []
        seen: set[str] = set()
        for a in soup.select("a[href*='/drama/']"):
            item = self._make_item(a, rank_type)
            if item is None:
                continue
            key = item["title"].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def _make_item(self, node, rank_type: str) -> dict | None:
        title = self._extract_title(node)
        if not self._is_valid_title(title):
            return None
        href = self._normalize_href(node.get("href", ""), base_url="https://www.shorttv.live")
        if "/drama/" not in href:
            return None
        return {
            "title": title,
            "summary": self._extract_following_summary(node),
            "cover_url": self._extract_image_url(node, "https://www.shorttv.live"),
            "tags": self._merge_tags([rank_type], self._extract_nearby_tags(node)),
            "episodes": self._extract_episode_count(node),
            "rank_type": rank_type,
            "source_url": href,
        }

    def _extract_title(self, node) -> str:
        text = self._clean_title(node.get_text(" ", strip=True))
        if self._is_valid_title(text):
            return text
        img = node.select_one("img") if hasattr(node, "select_one") else None
        if img is not None:
            alt = self._clean_title(img.get("alt", ""))
            if self._is_valid_title(alt):
                return alt
        return text

    def _extract_following_summary(self, node) -> str:
        paragraph = node.find_next("p") if hasattr(node, "find_next") else None
        if paragraph is None:
            return ""
        summary = self._clean_title(paragraph.get_text(" ", strip=True))
        return summary[:500] if len(summary) >= 30 else ""

    def _clean_heading(self, text: str) -> str:
        return "".join(ch for ch in self._clean_title(text) if ch.isalnum() or ch.isspace()).strip()
