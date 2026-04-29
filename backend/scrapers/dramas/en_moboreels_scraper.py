"""MoboReels 首页与剧库页爬虫。"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .shortdrama_base import BaseShortDramaScraper, EP_RE, SECTION_BLACKLIST


class MoboReelsScraper(BaseShortDramaScraper):
    platform = "moboreels"
    lang = "en"
    list_url = "https://www.moboreels.com/"
    library_url = "https://www.moboreels.com/dramas"
    section_limit = 10
    section_order = ["近期热门", "推荐栏位", "最近上新"]

    async def scrape(self, genre: str = "", limit: int = 10) -> list[dict]:
        home_html = await self._get_html(self.list_url, extra_headers={"Accept": "text/html"})
        library_html = await self._get_html(self.library_url, extra_headers={"Accept": "text/html"})
        items = await self._scrape_homepage_and_library(home_html, library_html, limit)
        items = await self._enrich_moboreels_items(items)
        return items[: limit * len(self.section_order)]

    async def _scrape_homepage_and_library(
        self, home_html: str, library_html: str, limit: int
    ) -> list[dict]:
        home_soup = BeautifulSoup(home_html, "html.parser")
        library_soup = BeautifulSoup(library_html, "html.parser")
        library_items = self._parse_listing_page(library_html, "近期热门", limit * 3)

        section_items: dict[str, list[dict]] = {sec: [] for sec in self.section_order}
        section_items["近期热门"] = await self._parse_trending_items(library_soup, limit)

        featured = self._parse_featured_item(home_soup, library_items)
        if featured is not None:
            section_items["推荐栏位"].append(featured)
        self._append_unique(
            section_items["推荐栏位"],
            self._parse_section_links(home_soup, ".popular-short", "推荐栏位"),
            limit,
            "推荐栏位",
        )

        self._append_unique(
            section_items["最近上新"],
            self._parse_section_links(home_soup, ".new-released", "最近上新"),
            limit,
            "最近上新",
        )

        out: list[dict] = []
        for sec in self.section_order:
            for idx, item in enumerate(section_items[sec][:limit], start=1):
                item["rank_in_platform"] = idx
                out.append(item)
        return out

    async def _parse_trending_items(self, soup: BeautifulSoup, limit: int) -> list[dict]:
        out: list[dict] = []
        search_links: list[tuple[str, str]] = []
        for a in soup.select("a[href*='/search/']"):
            title = self._clean_title(a.get_text(" ", strip=True))
            href = self._normalize_href(a.get("href", ""), base_url="https://www.moboreels.com")
            if title and self._is_valid_title(title):
                search_links.append((title, href))
            if len(search_links) >= limit:
                break

        if not search_links:
            self._append_unique(
                out,
                [
                    item
                    for item in (
                        self._make_item(a, "近期热门")
                        for a in soup.select("a[href*='/drama/']")
                    )
                    if item is not None
                ],
                limit,
                "近期热门",
            )
            return out

        for title, search_url in search_links:
            try:
                html = await self._get_html(search_url, extra_headers={"Accept": "text/html"})
            except Exception:
                continue
            search_items = self._parse_listing_page(html, "近期热门", limit)
            exact = next(
                (item for item in search_items if item["title"].lower() == title.lower()),
                search_items[0] if search_items else None,
            )
            if exact is None:
                continue
            self._append_unique(out, [exact], limit, "近期热门")
            if len(out) >= limit:
                break
        return out

    def _parse_featured_item(
        self, soup: BeautifulSoup, library_items: list[dict]
    ) -> dict | None:
        title_node = soup.select_one(".home-top-title")
        if title_node is None:
            return None
        title = self._clean_title(title_node.get_text(" ", strip=True))
        if not self._is_valid_title(title):
            return None
        summary_node = soup.select_one(".home-top-subTitle")
        summary = (
            self._clean_title(summary_node.get_text(" ", strip=True)) if summary_node else ""
        )
        match = next(
            (item for item in library_items if item["title"].lower() == title.lower()),
            None,
        )
        if match is None:
            return None
        return {
            **match,
            "summary": summary or match.get("summary", ""),
            "tags": self._merge_tags(["推荐栏位"], match.get("tags", [])),
            "rank_type": "推荐栏位",
        }

    def _parse_section_links(
        self, soup: BeautifulSoup, section_selector: str, rank_type: str
    ) -> list[dict]:
        section = soup.select_one(section_selector)
        if section is None:
            return []
        return [
            item
            for item in (
                self._make_item(a, rank_type)
                for a in section.select("a[href*='/drama/']")
            )
            if item is not None
        ]

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
        href = self._normalize_href(node.get("href", ""), base_url="https://www.moboreels.com")
        if "/drama/" not in href:
            return None
        return {
            "title": title,
            "summary": self._extract_following_summary(node),
            "cover_url": self._extract_image_url(node, "https://www.moboreels.com"),
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
        heading = node.find_next(["h2", "h3", "h4"]) if hasattr(node, "find_next") else None
        if heading is not None:
            return self._clean_title(heading.get_text(" ", strip=True))
        return text

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

    async def _enrich_moboreels_items(self, items: list[dict]) -> list[dict]:
        for item in items:
            detail_url = item.get("source_url", "")
            if not detail_url.startswith("http"):
                continue
            try:
                html = await self._get_html(detail_url, extra_headers={"Accept": "text/html"})
            except Exception:
                continue
            soup = BeautifulSoup(html, "html.parser")
            detail = self._extract_detail_metadata(soup, detail_url)
            if detail.get("summary") and not item.get("summary"):
                item["summary"] = detail["summary"]
            if detail.get("cover_url") and not item.get("cover_url"):
                item["cover_url"] = detail["cover_url"]
            item["tags"] = self._merge_tags(item.get("tags", []), detail.get("tags", []))
            if not item.get("episodes"):
                item["episodes"] = self._extract_detail_episode_count(soup)
        return items

    def _extract_detail_episode_count(self, soup: BeautifulSoup) -> int | None:
        candidates = []
        for selector in ["meta[name='description']", "meta[property='og:description']"]:
            meta = soup.select_one(selector)
            if meta and meta.get("content"):
                candidates.append(meta.get("content", ""))
        candidates.extend(a.get_text(" ", strip=True) for a in soup.select("a[href*='/episode/']"))
        for text in candidates:
            match = EP_RE.search(self._clean_title(text))
            if match:
                return int(match.group(1))
        episode_numbers = []
        for a in soup.select("a[href*='/episode/']"):
            text = self._clean_title(a.get_text(" ", strip=True))
            if text.upper().startswith("EP"):
                digits = "".join(ch for ch in text if ch.isdigit())
                if digits:
                    episode_numbers.append(int(digits))
        return max(episode_numbers) if episode_numbers else None

    def _append_unique(
        self,
        target: list[dict],
        candidates: list[dict],
        limit: int,
        rank_type: str | None = None,
        exclude_titles: set[str] | None = None,
    ) -> None:
        seen = {item["title"].lower() for item in target}
        excluded = exclude_titles if exclude_titles is not None else set()
        for item in candidates:
            key = item["title"].lower()
            if key in seen or key in excluded:
                continue
            copied = item.copy()
            if rank_type:
                copied["rank_type"] = rank_type
                copied["tags"] = self._merge_tags([rank_type], copied.get("tags", []))
            target.append(copied)
            seen.add(key)
            excluded.add(key)
            if len(target) >= limit:
                break
