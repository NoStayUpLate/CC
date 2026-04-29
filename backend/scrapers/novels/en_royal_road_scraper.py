"""
Royal Road 爬虫（英语 LitRPG / 奇幻市场）。

目标页：https://www.royalroad.com/fictions/weekly-popular
页面结构（2024-Q2）：
  - 故事卡片：.fiction-list-item
  - 标题：.fiction-title
  - 简介：.description > p
  - 标签：.tags > .label
  - 阅读量：[data-original-title="Total Views"] .number
  - 评分：.rating-widget / .overall-score
  - 链接：.fiction-title href

章节结构：
  - 章节列表：.chapter-row td.title a
  - 章节正文：.chapter-content（公开章节，无需登录）

robots.txt：Royal Road 允许合理抓取公开内容，遵守每次请求间隔。
"""
import asyncio
import logging

from playwright.async_api import Page, BrowserContext

from ..base_playwright_scraper import BasePlaywrightScraper
from services.keyword_extractor import extract_keywords

logger = logging.getLogger(__name__)

_WEEKLY_BASE = "weekly-popular"


class RoyalRoadScraper(BasePlaywrightScraper):
    platform = "royal_road"
    lang = "en"

    def build_url(self, genre: str = "", page: int = 1) -> str:
        # Royal Road 当前仅保留周榜入口，统一抓 weekly-popular。
        return f"https://www.royalroad.com/fictions/{_WEEKLY_BASE}?page={page}"

    async def _scrape_page(self, page: Page, genre: str, limit: int) -> list[dict]:
        results: list[dict] = []

        try:
            await page.wait_for_selector(".fiction-list-item", timeout=15_000)
        except Exception:
            return results

        cards = await page.query_selector_all(".fiction-list-item")

        for card in cards[:limit]:
            try:
                title_el = await card.query_selector(".fiction-title")
                title = (await title_el.inner_text()).strip() if title_el else None
                if not title:
                    continue

                # href 在 <h2.fiction-title> 内部的 <a> 上，不在 h2 本身
                href = ""
                link_el = await card.query_selector(".fiction-title a")
                if link_el:
                    href = await link_el.get_attribute("href") or ""
                    if href and not href.startswith("http"):
                        href = "https://www.royalroad.com" + href

                # 简介 div 默认 display:none，用 text_content() 绕过可见性限制
                desc_el = await card.query_selector("[id^='description-']")
                summary = (await desc_el.text_content()).strip() if desc_el else ""

                tag_els = await card.query_selector_all(".tags .label, .tags a")
                tags = [
                    (await t.inner_text()).strip()
                    for t in tag_els
                    if (await t.inner_text()).strip()
                ]

                # 阅读量：<i class="fa fa-eye"> 后紧跟 <span>26,298,114 Views</span>
                views_el = await card.query_selector(".stats i.fa-eye + span")
                views_text = None
                if views_el:
                    raw = (await views_el.inner_text()).strip()
                    views_text = raw.split()[0] if raw else None  # "26,298,114 Views" → "26,298,114"

                # 关注数作为 likes：<i class="fa fa-users"> 后紧跟 <span>31,309 Followers</span>
                likes_el = await card.query_selector(".stats i.fa-users + span")
                likes_text = None
                if likes_el:
                    raw = (await likes_el.inner_text()).strip()
                    likes_text = raw.split()[0] if raw else None  # "31,309 Followers" → "31,309"

                results.append(
                    self._make_row(
                        title=title,
                        summary=summary,
                        tags=tags,
                        views=self._safe_int_or_none(views_text),
                        likes=self._safe_int_or_none(likes_text),
                        original_url=href,
                        rank_type="weekly",
                    )
                )
            except Exception:
                continue

        return results

    # ─────────────────────────────────────────────────────────────
    # 章节文本抓取 & 关键词提取（_enrich_results 钩子实现）
    # ─────────────────────────────────────────────────────────────

    async def _fetch_chapter_text(self, page: Page, novel_url: str) -> str | None:
        """
        抓取指定小说前三章的合并正文。
        - 只读取公开章节（无需登录），若遇付费墙则跳过该章并继续
        - 单本超时 15 秒（含导航 + 3 章加载）
        """
        try:
            await page.goto(novel_url, wait_until="domcontentloaded", timeout=10_000)

            # 章节列表行（按时间顺序，最早的在最下方，需倒序取前三）
            chapter_links = await page.query_selector_all(
                ".chapter-row td.title a, table.chapter-list .chapter-row td a"
            )
            if not chapter_links:
                return None

            # Royal Road 章节列表最新在前，取最后 3 条（即前三章）
            first_three = chapter_links[-3:] if len(chapter_links) >= 3 else chapter_links
            # 倒序使其变为 chap1, chap2, chap3 顺序
            first_three = list(reversed(first_three))

            hrefs: list[str] = []
            for link in first_three:
                href = await link.get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = "https://www.royalroad.com" + href
                if href:
                    hrefs.append(href)

            if not hrefs:
                return None

            combined: list[str] = []
            for chapter_url in hrefs:
                try:
                    await page.goto(chapter_url, wait_until="domcontentloaded", timeout=8_000)
                    content_el = await page.query_selector(".chapter-content")
                    if content_el:
                        text = await content_el.inner_text()
                        if text.strip():
                            combined.append(text)
                except Exception:
                    continue

            return "\n".join(combined) if combined else None
        except Exception:
            return None

    async def _enrich_results(
        self, context: BrowserContext, results: list[dict]
    ) -> None:
        """
        列表抓取完成后，逐本抓取前三章正文并提取关键词。
        每本设 15 秒超时；失败时 top_keywords 保持 None（零数据保护）。
        """
        if not results:
            return

        chapter_page = await context.new_page()
        chapter_page.set_default_timeout(15_000)
        try:
            for row in results:
                novel_url = row.get("original_url", "")
                if not novel_url:
                    continue
                try:
                    text = await asyncio.wait_for(
                        self._fetch_chapter_text(chapter_page, novel_url),
                        timeout=15.0,
                    )
                    row["top_keywords"] = extract_keywords(text, lang="en") if text else None
                except (asyncio.TimeoutError, Exception) as e:
                    logger.debug("Royal Road keyword fetch skipped for %s: %s", novel_url, e)
                    row["top_keywords"] = None
        finally:
            await chapter_page.close()
