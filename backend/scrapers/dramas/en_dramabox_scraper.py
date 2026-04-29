"""DramaBox 短剧首页与 More 页爬虫。"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .shortdrama_base import BaseShortDramaScraper


class DramaBoxScraper(BaseShortDramaScraper):
    platform = "dramabox"
    lang = "en"
    list_url = "https://www.dramabox.com/"
    section_limit = 10
    section_order = ["顶部推荐", "推荐栏位", "近期热门"]

    async def scrape(self, genre: str = "", limit: int = 10) -> list[dict]:
        html = await self._get_html(self.list_url, extra_headers={"Accept": "text/html"})
        items = await self._scrape_homepage_and_more(html, self.list_url, limit)
        items = await self._enrich_items_from_detail_pages(items)
        return items[: limit * len(self.section_order)]

    def _parse_homepage(self, html: str, source_url: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://www.dramabox.com"
        title_to_url: dict[str, str] = {}
        title_to_cover: dict[str, str] = {}
        title_to_tags: dict[str, list[str]] = {}
        title_to_episodes: dict[str, int | None] = {}

        for a in soup.select("a[href*='/drama/']"):
            title = self._clean_title(a.get_text(" ", strip=True))
            if not self._is_valid_title(title):
                continue
            normalized = self._normalize_href(a.get("href", ""), base_url=base_url)
            title_to_url[title] = normalized
            title_to_cover[title] = self._extract_image_url(a, base_url)
            title_to_tags[title] = self._extract_nearby_tags(a)
            title_to_episodes[title] = self._extract_episode_count(a)

        seen: set[tuple[str, str]] = set()
        section_label = "顶部推荐"
        section_items: dict[str, list[dict]] = {sec: [] for sec in self.section_order}

        for node in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
            if node.name in {"h1", "h2", "h3", "h4"}:
                heading_text = self._clean_title(node.get_text(" ", strip=True))
                low = heading_text.lower()
                if low == "must-sees":
                    section_label = "推荐栏位"
                elif low == "trending":
                    section_label = "近期热门"
                elif low in {"hidden gems", "about"}:
                    section_label = ""
                elif self._is_valid_title(heading_text):
                    continue
                continue

            href = (node.get("href") or "").strip()
            if not section_label or "/drama/" not in href:
                continue
            title = self._clean_title(node.get_text(" ", strip=True))
            if not self._is_valid_title(title):
                continue
            unique_key = (section_label, title)
            if unique_key in seen:
                continue
            seen.add(unique_key)

            section_items[section_label].append(
                {
                    "title": title,
                    "summary": "",
                    "cover_url": title_to_cover.get(title, ""),
                    "tags": self._merge_tags([section_label], title_to_tags.get(title, [])),
                    "episodes": title_to_episodes.get(title),
                    "rank_type": section_label,
                    "source_url": title_to_url.get(title, self._normalize_href(href, base_url=base_url)),
                }
            )

        out: list[dict] = []
        for sec in self.section_order:
            for idx, item in enumerate(section_items[sec][:limit], start=1):
                item["rank_in_platform"] = idx
                out.append(item)
        return out

    async def _scrape_homepage_and_more(
        self, html: str, source_url: str, limit: int
    ) -> list[dict]:
        items = self._parse_homepage(html, source_url, limit)
        section_items: dict[str, list[dict]] = {sec: [] for sec in self.section_order}
        for item in items:
            rank_type = item.get("rank_type", "")
            if rank_type in section_items:
                section_items[rank_type].append(item)

        more_pages = {
            "推荐栏位": "https://www.dramabox.com/more/must-sees",
            "近期热门": "https://www.dramabox.com/more/trending",
        }
        for rank_type, page_url in more_pages.items():
            if len(section_items[rank_type]) >= limit:
                continue
            try:
                more_html = await self._get_html(page_url, extra_headers={"Accept": "text/html"})
            except Exception:
                continue
            for item in self._parse_more_page(more_html, page_url, rank_type, limit):
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

    def _parse_more_page(
        self, html: str, source_url: str, rank_type: str, limit: int
    ) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://www.dramabox.com"
        out: list[dict] = []
        seen: set[str] = set()

        for a in soup.select("a[href*='/drama/']"):
            title = self._clean_title(a.get_text(" ", strip=True))
            if not self._is_valid_title(title):
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            href = self._normalize_href(a.get("href", ""), base_url=base_url)
            out.append(
                {
                    "title": title,
                    "summary": "",
                    "cover_url": self._extract_image_url(a, base_url),
                    "tags": self._merge_tags([rank_type], self._extract_nearby_tags(a)),
                    "episodes": self._extract_episode_count(a),
                    "rank_type": rank_type,
                    "source_url": href or source_url,
                }
            )
            if len(out) >= limit:
                break
        return out
