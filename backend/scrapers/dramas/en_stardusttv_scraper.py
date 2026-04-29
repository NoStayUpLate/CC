"""StardustTV 英文首页短剧爬虫。"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .shortdrama_base import BaseShortDramaScraper, EP_RE


class StardustTVScraper(BaseShortDramaScraper):
    platform = "stardusttv"
    lang = "en"
    list_url = "https://www.stardusttv.net/"
    section_limit = 10
    section_order = ["近期热门", "最近上新", "当前热门", "推荐栏位"]

    async def scrape(self, genre: str = "", limit: int = 10) -> list[dict]:
        html = await self._get_html(self.list_url, extra_headers={"Accept": "text/html"})
        items = await self._parse_homepage(html, limit)
        items = await self._enrich_stardust_items(items)
        return items[: limit * len(self.section_order)]

    async def _parse_homepage(self, html: str, limit: int) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        section_map = {
            "trending now": "近期热门",
            "new releases": "最近上新",
            "now streaming": "当前热门",
            "exclusive series": "推荐栏位",
        }
        section_items: dict[str, list[dict]] = {sec: [] for sec in self.section_order}
        section_label = ""
        seen: set[tuple[str, str]] = set()

        for node in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
            if node.name in {"h1", "h2", "h3", "h4"}:
                heading = self._clean_title(node.get_text(" ", strip=True))
                mapped = section_map.get(heading.lower())
                if mapped:
                    section_label = mapped
                continue

            href = (node.get("href") or "").strip()
            if not section_label or "/episodes/" not in href:
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

    def _make_item(self, node, rank_type: str) -> dict | None:
        href = self._normalize_href(node.get("href", ""), base_url="https://www.stardusttv.net")
        if "/episodes/" not in href:
            return None
        raw_text = self._clean_title(node.get_text(" ", strip=True))
        title = self._extract_title(node, raw_text)
        if not self._is_valid_title(title):
            return None
        summary = self._extract_summary(raw_text, title)
        return {
            "title": title,
            "summary": summary,
            "cover_url": self._extract_image_url(node, "https://www.stardusttv.net"),
            "tags": self._merge_tags([rank_type], self._extract_nearby_tags(node)),
            "episodes": None,
            "rank_type": rank_type,
            "source_url": href,
        }

    def _extract_title(self, node, raw_text: str) -> str:
        heading = node.find(["h2", "h3", "h4"]) if hasattr(node, "find") else None
        if heading is not None:
            text = self._clean_title(heading.get_text(" ", strip=True))
            if self._is_valid_title(text):
                return text
        img = node.select_one("img") if hasattr(node, "select_one") else None
        if img is not None:
            alt = self._clean_title(img.get("alt", ""))
            if self._is_valid_title(alt) and alt.lower() not in {"bg", "poster"}:
                return alt
        # 标题链接本身通常只有标题；长卡片链接则把标题与简介拼在一起。
        if self._is_valid_title(raw_text):
            return raw_text
        for candidate in raw_text.split("  "):
            clean = self._clean_title(candidate.removeprefix("AI "))
            if self._is_valid_title(clean):
                return clean
        return raw_text

    def _extract_summary(self, raw_text: str, title: str) -> str:
        text = self._clean_title(raw_text.removeprefix("AI "))
        if len(text) <= len(title) + 20:
            return ""
        if text.lower().startswith(title.lower()):
            return text[len(title):].strip()[:500]
        return ""

    async def _enrich_stardust_items(self, items: list[dict]) -> list[dict]:
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
                item["episodes"] = self._extract_episode_count_from_detail(soup)
        return items

    def _extract_episode_count_from_detail(self, soup: BeautifulSoup) -> int | None:
        for a in soup.select("a[href*='/full-episodes/']"):
            text = self._clean_title(a.get_text(" ", strip=True))
            match = EP_RE.search(text)
            if match:
                return int(match.group(1))
        return None
