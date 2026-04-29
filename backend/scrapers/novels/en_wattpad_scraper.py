"""
Wattpad 爬虫（英语市场）。

使用 Wattpad 公开 REST API，通过 BaseHttpScraper 提供重试与代理支持。

Wattpad 题材 category ID：
  9  = Werewolf    4  = Romance     6  = Fantasy
  2  = Adventure   10 = Teen Fiction 14 = Humor

章节抓取：
  - 列表  GET /api/v3/stories/{story_id}?fields=parts  → parts[].id
  - 正文  GET /apiv2/storytext?id={part_id}            → HTML 正文
  遵守 Wattpad robots.txt，仅读取公开章节，不绕过登录墙。
"""
import logging
import re

from ..base_http_scraper import BaseHttpScraper
from services.keyword_extractor import extract_keywords

logger = logging.getLogger(__name__)

# 提取阅读页正文段落（服务端渲染，无需 JS）
_PARA_RE = re.compile(r'<p[^>]+data-p-id="[^"]+"[^>]*>(.*?)</p>', re.DOTALL)
_TAG_RE  = re.compile(r'<[^>]+>')

_GENRE_CATEGORY: dict[str, int] = {
    "werewolf":    9,
    "romance":     4,
    "fantasy":     6,
    "adventure":   2,
    "teen":        10,
    "billionaire": 4,
    "":            9,
}


class WattpadScraper(BaseHttpScraper):
    platform = "wattpad"
    lang = "en"

    def build_url(self, genre: str = "", page: int = 1) -> str:
        cat = _GENRE_CATEGORY.get(genre.lower(), 9)
        offset = (page - 1) * 20
        return (
            f"https://www.wattpad.com/api/v3/stories"
            f"?categories={cat}&limit=20&offset={offset}"
        )

    async def scrape(self, genre: str = "", limit: int = 50) -> list[dict]:
        results: list[dict] = []
        story_ids: list[int | None] = []
        page = 1

        while len(results) < limit and page <= 5:
            url = self.build_url(genre, page)
            try:
                data = await self._get_json(
                    url,
                    extra_headers={"Accept": "application/json"},
                )
            except Exception as e:
                logger.error("Wattpad page %d fetch failed: %s", page, e, exc_info=True)
                raise

            stories = data.get("stories", [])
            if not stories:
                break

            for s in stories:
                if len(results) >= limit:
                    break
                tags = [t.lower() for t in (s.get("tags") or [])]
                views_raw = s.get("readCount") or s.get("reads")
                likes_raw = s.get("voteCount")
                story_ids.append(s.get("id"))
                results.append(self._make_row(
                    title=s.get("title") or "",
                    summary=s.get("description") or "",
                    tags=tags,
                    views=int(views_raw) if views_raw is not None else None,
                    likes=int(likes_raw) if likes_raw is not None else None,
                    original_url=s.get("url") or "",
                ))

            page += 1

        # 章节文本抓取 → 关键词提取（最多取前三章，失败保持 None）
        for row, story_id in zip(results, story_ids):
            if not story_id:
                continue
            try:
                row["top_keywords"] = await self._fetch_chapter_keywords(story_id)
            except Exception as e:
                logger.debug("Wattpad keyword fetch skipped for story %s: %s", story_id, e)

        return results[:limit]

    async def _fetch_chapter_keywords(
        self, story_id: int | str
    ) -> dict[str, int] | None:
        """
        抓取前三章正文并提取英语关键词。

        流程（全部使用公开页面，无需登录）：
          1. GET /api/v3/stories/{id}?fields=parts  → 拿每章的 url 字段
          2. GET {chapter_url}                      → 阅读页 HTML（服务端渲染）
          3. 提取 <p data-p-id="..."> 标签内的文字  → 纯正文
        """
        try:
            parts_resp = await self._get_json(
                f"https://www.wattpad.com/api/v3/stories/{story_id}?fields=parts",
                extra_headers={"Accept": "application/json"},
            )
            parts = (parts_resp.get("parts") or [])[:3]
            if not parts:
                return None

            combined: list[str] = []
            for part in parts:
                chapter_url = part.get("url")
                if not chapter_url:
                    continue
                try:
                    html = await self._get_html(chapter_url)
                    # 阅读页正文段落：<p data-p-id="...">文字</p>（服务端渲染，无需 JS）
                    paras = _PARA_RE.findall(html)
                    text = " ".join(
                        _TAG_RE.sub(" ", p).replace("&apos;", "'")
                                            .replace("&amp;", "&")
                                            .replace("&lt;", "<")
                                            .replace("&gt;", ">")
                        for p in paras
                    ).strip()
                    if text:
                        combined.append(text)
                except Exception:
                    continue

            if not combined:
                return None
            return extract_keywords("\n".join(combined), lang="en")

        except Exception:
            return None
