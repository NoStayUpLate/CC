"""GoodShort 短剧首页与频道页爬虫。"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .shortdrama_base import (
    GOODSHORT_EP_RE,
    SECTION_BLACKLIST,
    BaseShortDramaScraper,
)


class GoodShortScraper(BaseShortDramaScraper):
    platform = "goodshort"
    lang = "en"
    list_url = "https://www.goodshort.com/"
    section_limit = 10
    section_order = ["近期热门", "推荐栏位", "热门榜单", "当前热门"]

    async def scrape(self, genre: str = "", limit: int = 10) -> list[dict]:
        html = await self._get_html(self.list_url, extra_headers={"Accept": "text/html"})
        items = await self._scrape_homepage_and_channels(html, self.list_url, limit)
        items = await self._enrich_items_from_detail_pages(items)
        return items[: limit * len(self.section_order)]

    async def _scrape_homepage_and_channels(
        self, html: str, source_url: str, limit: int
    ) -> list[dict]:
        base_url = "https://www.goodshort.com"
        section_items = self._parse_homepage(html, source_url, limit)
        more_pages = {
            "近期热门": f"{base_url}/channel/Most-Trending",
            "推荐栏位": f"{base_url}/channel/Top-in-GoodShort",
            "热门榜单": f"{base_url}/channel/Hot-List",
            "当前热门": f"{base_url}/channel/Popular-Now",
        }

        for rank_type, page_url in more_pages.items():
            if len(section_items[rank_type]) >= limit:
                continue
            try:
                more_html = await self._get_html(page_url, extra_headers={"Accept": "text/html"})
            except Exception:
                continue
            for item in self._parse_listing_page(more_html, rank_type, limit):
                if len(section_items[rank_type]) >= limit:
                    break
                key = item["title"].lower()
                if any(existing["title"].lower() == key for existing in section_items[rank_type]):
                    continue
                section_items[rank_type].append(item)

        out: list[dict] = []
        for sec in self.section_order:
            for idx, item in enumerate(section_items[sec][:limit], start=1):
                item["rank_in_platform"] = idx
                out.append(item)
        return out

    def _parse_homepage(
        self, html: str, source_url: str, limit: int
    ) -> dict[str, list[dict]]:
        soup = BeautifulSoup(html, "html.parser")
        section_map = {
            "most trending": "近期热门",
            "top in goodshort": "推荐栏位",
            "hot list": "热门榜单",
            "popular now": "当前热门",
        }
        section_items: dict[str, list[dict]] = {sec: [] for sec in self.section_order}
        section_label = ""
        seen: set[tuple[str, str]] = set()
        metadata = self._collect_metadata(soup)

        for node in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
            if node.name in {"h1", "h2", "h3", "h4"}:
                heading_text = self._clean_title(node.get_text(" ", strip=True))
                low = heading_text.lower()
                if low in section_map:
                    section_label = section_map[low]
                elif low in {"love stories", "counterattack", "cutie", "eng dubbed dramas"}:
                    section_label = ""
                continue

            href = (node.get("href") or "").strip()
            if not section_label or "/drama/" not in href:
                continue
            item = self._make_item(node, section_label, metadata)
            if item is None:
                continue
            unique_key = (section_label, item["title"].lower())
            if unique_key in seen:
                continue
            if len(section_items[section_label]) >= limit:
                continue
            seen.add(unique_key)
            section_items[section_label].append(item)

        return section_items

    def _parse_listing_page(self, html: str, rank_type: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        metadata = self._collect_metadata(soup)
        out: list[dict] = []
        seen: set[str] = set()
        for a in soup.select("a[href*='/drama/']"):
            item = self._make_item(a, rank_type, metadata)
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

    def _collect_metadata(self, soup: BeautifulSoup) -> dict[str, dict]:
        metadata: dict[str, dict] = {}
        for a in soup.select("a[href*='/drama/']"):
            href = self._normalize_href(a.get("href", ""), base_url="https://www.goodshort.com")
            text = self._clean_title(a.get_text(" ", strip=True))
            if not href:
                continue
            entry = metadata.setdefault(
                href,
                {"cover_url": "", "tags": [], "episodes": None, "summary": ""},
            )
            ep_match = GOODSHORT_EP_RE.match(text)
            if ep_match:
                entry["episodes"] = int(ep_match.group(1))
                entry["cover_url"] = entry["cover_url"] or self._extract_image_url(
                    a, "https://www.goodshort.com"
                )
                entry["tags"] = self._merge_tags(
                    entry.get("tags", []),
                    self._extract_nearby_tags(a),
                )
                continue
            if self._is_goodshort_title(text):
                summary = self._extract_following_summary(a)
                if summary:
                    entry["summary"] = entry.get("summary") or summary
                entry["cover_url"] = entry["cover_url"] or self._extract_image_url(
                    a, "https://www.goodshort.com"
                )
                entry["tags"] = self._merge_tags(
                    entry.get("tags", []),
                    self._extract_nearby_tags(a),
                )
        return metadata

    def _make_item(self, node, rank_type: str, metadata: dict[str, dict]) -> dict | None:
        title = self._clean_title(node.get_text(" ", strip=True))
        if not self._is_goodshort_title(title):
            return None
        href = self._normalize_href(node.get("href", ""), base_url="https://www.goodshort.com")
        meta = metadata.get(href, {})
        return {
            "title": title,
            "summary": meta.get("summary") or self._extract_following_summary(node),
            "cover_url": meta.get("cover_url", ""),
            "tags": self._merge_tags([rank_type], meta.get("tags", [])),
            "episodes": meta.get("episodes"),
            "rank_type": rank_type,
            "source_url": href,
        }

    def _is_goodshort_title(self, title: str) -> bool:
        if GOODSHORT_EP_RE.match(title):
            return False
        return self._is_valid_title(title)

    def _extract_following_summary(self, node) -> str:
        paragraph = node.find_next("p") if hasattr(node, "find_next") else None
        if paragraph is None:
            return ""
        summary = self._clean_title(paragraph.get_text(" ", strip=True))
        if not summary or summary.lower() in SECTION_BLACKLIST:
            return ""
        if len(summary) < 30:
            return ""
        return summary[:500]
