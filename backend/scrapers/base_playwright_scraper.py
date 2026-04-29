"""
Playwright 爬虫抽象基类：封装浏览器生命周期、随机 UA、请求延迟与反检测。

子类只需实现 _scrape_page() 与 build_url()，返回 NovelRow dict 列表。
子类可覆盖 _enrich_results() 在列表抓取完成后，利用已打开的浏览器做二次扩充
（如章节文本抓取 → 关键词提取），无需重新启动浏览器。
"""
import asyncio
import random
from abc import abstractmethod

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from .base_scraper import BaseScraper
from config import settings

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


class BasePlaywrightScraper(BaseScraper):
    """Playwright 驱动的爬虫基类，含浏览器管理与反检测逻辑。"""

    def __init__(self, headless: bool | None = None):
        self.headless = headless if headless is not None else settings.scraper_headless

    async def scrape(self, genre: str = "", limit: int = 50) -> list[dict]:
        """启动浏览器 -> 遍历页面 -> 收集结果 -> 关闭浏览器。"""
        results: list[dict] = []
        async with async_playwright() as pw:
            browser: Browser = await pw.chromium.launch(headless=self.headless)
            context: BrowserContext = await browser.new_context(
                user_agent=random.choice(_USER_AGENTS),
                locale="en-US",
                viewport={"width": 1280, "height": 800},
            )
            # 屏蔽图片与媒体资源，加快加载速度
            await context.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,mp4,woff,woff2}",
                lambda route: route.abort(),
            )
            try:
                page: Page = await context.new_page()
                page.set_default_timeout(60_000)

                # 隐藏 Headless 特征，规避基础 Bot 检测
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
                    window.chrome = {runtime: {}};
                """)

                url = self.build_url(genre)
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                await self._random_delay()

                page_results = await self._scrape_page(page, genre, limit)
                results.extend(page_results)

                # 若首页不足则翻页补充
                page_num = 2
                while len(results) < limit and page_num <= 5:
                    next_url = self.build_url(genre, page=page_num)
                    if not next_url:
                        break
                    await page.goto(next_url, wait_until="domcontentloaded", timeout=60_000)
                    await self._random_delay()
                    more = await self._scrape_page(page, genre, limit - len(results))
                    if not more:
                        break
                    results.extend(more)
                    page_num += 1

                # 二次扩充钩子：子类可在此利用已打开的浏览器抓取章节文本等额外数据
                await self._enrich_results(context, results)

            finally:
                await browser.close()

        return results[:limit]

    @abstractmethod
    def build_url(self, genre: str = "", page: int = 1) -> str:
        """根据题材和页码构建目标 URL。"""
        ...

    @abstractmethod
    async def _scrape_page(self, page: Page, genre: str, limit: int) -> list[dict]:
        """从当前页面抓取小说列表，返回 dict 列表。"""
        ...

    async def _enrich_results(
        self, context: BrowserContext, results: list[dict]
    ) -> None:
        """列表抓取完成后的二次扩充钩子。
        子类可覆盖此方法，利用已打开的 BrowserContext 抓取额外数据
        （如章节正文 → 关键词提取）。默认为空操作。
        """

    async def _random_delay(self) -> None:
        """在配置范围内随机等待，模拟人工浏览节奏。"""
        delay = random.uniform(settings.scraper_delay_min, settings.scraper_delay_max)
        await asyncio.sleep(delay)
