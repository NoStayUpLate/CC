"""
短剧爬虫公共基类与解析工具。

各短剧平台 scraper 只保留自身页面结构解析逻辑，通用的清洗、补全、
封面提取和标签合并集中维护在这里。
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from ..base_http_scraper import BaseHttpScraper


SECTION_BLACKLIST = {
    "view all",
    "new release",
    "must-sees",
    "trending",
    "top recommendation",
    "top recommendations",
    "hidden gems",
    "drama",
    "dramas",
    "dramabox",
    "netshort",
    "reelshort",
    "dramawave",
    "dramareels",
    "goodshort",
    "moboreels",
    "shortmax",
    "play",
    "more",
}

TITLE_CLEAN_RE = re.compile(r"\s+")
EP_RE = re.compile(r"(\d+)\s*episodes?", re.IGNORECASE)
ONLY_EP_RE = re.compile(r"^\d+\s*episodes?$", re.IGNORECASE)
GOODSHORT_EP_RE = re.compile(r"^EP\s*(\d+)$", re.IGNORECASE)
DESCRIPTION_TAG_RE = re.compile(
    r"(?:cover|covers|genres?|tags?|type)\s+(.+?)(?:\.\s*(?:watch|read|stream|download)|\.\s|$)",
    re.IGNORECASE,
)

SECTION_LABEL_MAP = {
    "recommended": "推荐栏位",
    "recommendation": "推荐栏位",
    "trending": "推荐栏位",
    "for you": "推荐栏位",
    "new release": "最近上新",
    "new releases": "最近上新",
    "latest": "最近上新",
    "must-sees": "轮播推荐",
    "must sees": "轮播推荐",
    "featured": "轮播推荐",
    "banner": "轮播推荐",
}


class BaseShortDramaScraper(BaseHttpScraper):
    """短剧平台 scraper 基类。"""

    platform = ""
    lang = "en"
    list_url = ""
    section_limit = 10
    section_order: list[str] = []

    async def _enrich_items_from_detail_pages(self, items: list[dict]) -> list[dict]:
        """补充详情页里的简介、封面和标签。单条失败不影响整批抓取。"""
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
        return items

    def _parse_section_by_headings(
        self,
        soup: BeautifulSoup,
        source_url: str,
        limit: int,
        link_keyword: str,
        base_url: str,
        normalize_url=None,
    ) -> list[dict]:
        title_to_url: dict[str, str] = {}
        title_to_cover: dict[str, str] = {}
        title_to_tags: dict[str, list[str]] = {}
        for a in soup.select("a[href]"):
            title = self._clean_title(a.get_text(" ", strip=True))
            href = (a.get("href") or "").strip()
            if not title or not href or link_keyword not in href:
                continue
            if not self._is_valid_title(title):
                continue
            normalized = self._normalize_href(href, base_url=base_url)
            if normalize_url is not None:
                normalized = normalize_url(normalized)
            title_to_url[title] = normalized
            title_to_cover[title] = self._extract_image_url(a, base_url)
            title_to_tags[title] = self._extract_nearby_tags(a)

        out: list[dict] = []
        seen: set[tuple[str, str]] = set()
        section_label = ""
        for node in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
            if node.name in {"h1", "h2", "h3", "h4"}:
                heading_text = self._clean_title(node.get_text(" ", strip=True))
                if self._is_valid_title(heading_text):
                    continue
                section_label = SECTION_LABEL_MAP.get(heading_text.lower(), "")
                continue

            href = (node.get("href") or "").strip()
            if section_label == "" or link_keyword not in href:
                continue
            title = self._clean_title(node.get_text(" ", strip=True))
            if not self._is_valid_title(title):
                continue
            key = (section_label, title)
            if key in seen:
                continue
            seen.add(key)

            out.append(
                {
                    "title": title,
                    "summary": "",
                    "cover_url": title_to_cover.get(title, ""),
                    "tags": self._merge_tags([section_label], title_to_tags.get(title, [])),
                    "episodes": None,
                    "rank_type": section_label,
                    "source_url": title_to_url.get(title, source_url),
                }
            )
            if len(out) >= limit:
                break
        return out

    def _extract_detail_metadata(self, soup: BeautifulSoup, page_url: str) -> dict:
        summary = ""
        for selector in [
            "meta[property='og:description']",
            "meta[name='description']",
            "meta[name='twitter:description']",
        ]:
            meta = soup.select_one(selector)
            if meta and meta.get("content"):
                summary = self._clean_title(meta.get("content", ""))[:500]
                break

        cover_url = ""
        for selector in [
            "meta[property='og:image']",
            "meta[name='twitter:image']",
            "meta[property='twitter:image']",
        ]:
            meta = soup.select_one(selector)
            if meta and meta.get("content"):
                cover_url = urljoin(page_url, meta.get("content", "").strip())
                break
        if not cover_url:
            cover_url = self._extract_image_url(soup, page_url)

        tags: list[str] = []
        if summary:
            tags.extend(self._extract_tags_from_text(summary))
        for selector in ["meta[name='keywords']", "meta[property='article:tag']"]:
            meta = soup.select_one(selector)
            if meta and meta.get("content"):
                tags.extend(self._split_tag_text(meta.get("content", "")))
        for selector in [
            "a[href*='/browse/']",
            "a[href*='/genre']",
            "a[href*='/tag']",
            "a[href*='/dramas/']",
            "[class*='tag']",
            "[class*='genre']",
        ]:
            for node in soup.select(selector):
                text = self._clean_title(node.get_text(" ", strip=True))
                if self._is_valid_tag(text):
                    tags.append(text)

        return {
            "summary": summary,
            "cover_url": cover_url,
            "tags": self._merge_tags(tags),
        }

    def _normalize_href(self, href: str, base_url: str) -> str:
        if href.startswith("/"):
            return base_url + href
        if href.startswith("http"):
            return href
        return base_url + "/" + href.lstrip("/")

    def _normalize_reelshort_url(self, href: str) -> str:
        decoded = unquote(href)
        normalized = self._normalize_href(decoded, base_url="https://www.reelshort.com")
        normalized = normalized.replace("?playTime=", "?play_time=")
        normalized = normalized.replace("/episodes//episodes/", "/episodes/")
        return normalized

    def _extract_image_url(self, node, base_url: str) -> str:
        """从卡片/详情节点提取封面图，兼容懒加载与 srcset。"""
        img = node.select_one("img") if hasattr(node, "select_one") else None
        if img is None:
            return ""
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            raw = (img.get(attr) or "").strip()
            if raw and not raw.startswith("data:"):
                return urljoin(base_url, raw)
        srcset = (img.get("srcset") or "").strip()
        if srcset:
            first = srcset.split(",")[0].strip().split(" ")[0]
            if first:
                return urljoin(base_url, first)
        return ""

    def _extract_nearby_tags(self, node, include_drama_links: bool = False) -> list[str]:
        """从卡片附近的类型链接提取短剧标签。"""
        tags: list[str] = []
        root_title = self._clean_title(node.get_text(" ", strip=True))
        href_keys = ["/browse/", "/genre", "/tag", "/shelf/"]
        if include_drama_links:
            href_keys.append("/drama/")
        parent = node
        for _ in range(3):
            parent = parent.parent if parent is not None else None
            if parent is None:
                break
            for a in parent.select("a[href]"):
                href = (a.get("href") or "").lower()
                if not any(key in href for key in href_keys):
                    continue
                text = self._clean_title(a.get_text(" ", strip=True))
                if text.lower() == root_title.lower():
                    continue
                if self._is_valid_tag(text):
                    tags.append(text)
        return self._merge_tags(tags)

    def _extract_episode_count(self, node) -> int | None:
        """从卡片附近文本中解析集数。"""
        candidates = [self._clean_title(node.get_text(" ", strip=True))]
        parent = node
        for _ in range(2):
            parent = parent.parent if parent is not None else None
            if parent is None:
                break
            candidates.append(self._clean_title(parent.get_text(" ", strip=True)))

        for text in candidates:
            match = EP_RE.search(text)
            if match:
                return int(match.group(1))
        return None

    def _merge_tags(self, *groups: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for tag in group or []:
                clean = self._clean_title(tag)
                if not self._is_valid_tag(clean):
                    continue
                key = clean.lower()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(clean)
        return merged[:12]

    def _extract_tags_from_text(self, text: str) -> list[str]:
        """从详情页描述中解析题材标签，如 'cover CEO,Revenge. Watch ...'。"""
        clean = self._clean_title(text)
        tags: list[str] = []
        for match in DESCRIPTION_TAG_RE.finditer(clean):
            tags.extend(self._split_tag_text(match.group(1)))
        return self._merge_tags(tags)

    def _split_tag_text(self, text: str) -> list[str]:
        tags: list[str] = []
        for part in re.split(r"[,，/|;；]+", text or ""):
            clean = self._clean_title(part)
            clean = re.sub(
                r"^(?:and|with|such as|including)\s+",
                "",
                clean,
                flags=re.IGNORECASE,
            )
            if self._is_valid_tag(clean):
                tags.append(clean)
        return self._merge_tags(tags)

    def _clean_title(self, text: str) -> str:
        text = TITLE_CLEAN_RE.sub(" ", (text or "").strip()).strip(" -·•")
        return text

    def _is_valid_title(self, title: str) -> bool:
        if not title:
            return False
        if len(title) < 4 or len(title) > 100:
            return False
        if ONLY_EP_RE.match(title):
            return False
        lower = title.lower()
        if ".js" in lower or "/" in title or "\\" in title:
            return False
        if lower.startswith(("assets", "./", "app-", "index-", "chunk-")):
            return False
        if "episode" in lower and len(title.split()) <= 3:
            return False
        if title.lower() in SECTION_BLACKLIST:
            return False
        if lower.startswith("watch ") and not lower.startswith("watch out"):
            return False
        if lower.startswith(("download ", "view all")):
            return False
        return any(ch.isalpha() for ch in title)

    def _is_valid_tag(self, tag: str) -> bool:
        if not tag:
            return False
        if len(tag) < 2 or len(tag) > 40:
            return False
        lower = tag.lower()
        if lower in SECTION_BLACKLIST:
            return False
        if ONLY_EP_RE.match(tag) or EP_RE.search(tag):
            return False
        if lower.startswith(("http", "watch ", "episode", "more", "view all")):
            return False
        if "/" in tag or "\\" in tag or ".js" in lower:
            return False
        return any(ch.isalpha() for ch in tag)
