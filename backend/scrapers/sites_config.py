"""
目标爬取站点配置表。

tech 字段说明：
  http_api   - 使用公开 REST API，无需浏览器渲染
  playwright - 需要 Playwright 动态渲染（含 JS 异步加载）

status 字段说明：
  done    - 爬虫已实现
  pending - 待实现
"""
from typing import TypedDict


class SiteConfig(TypedDict):
    platform: str   # 平台唯一标识（与 ClickHouse platform 字段对应）
    lang: str       # ISO 639-1 语种代码
    name: str       # 平台展示名
    url: str        # 平台首页 URL
    tech: str       # "http_api" 或 "playwright"
    status: str     # "done" 或 "pending"


SITES: list[SiteConfig] = [
    {
        "platform": "wattpad",
        "lang": "en",
        "name": "Wattpad",
        "url": "https://www.wattpad.com/",
        "tech": "http_api",
        "status": "done",
    },
    {
        "platform": "royal_road",
        "lang": "en",
        "name": "Royal Road",
        "url": "https://www.royalroad.com/",
        "tech": "playwright",
        "status": "done",
    },
    {
        "platform": "inkitt",
        "lang": "en",
        "name": "Inkitt",
        "url": "https://www.inkitt.com/",
        "tech": "playwright",
        "status": "pending",
    },
    {
        "platform": "webnovel",
        "lang": "en",
        "name": "Webnovel",
        "url": "https://www.webnovel.com/",
        "tech": "playwright",
        "status": "pending",
    },
    {
        "platform": "syosetu",
        "lang": "ja",
        "name": "小説家になろう",
        "url": "https://syosetu.com/",
        "tech": "playwright",
        "status": "done",
    },
    {
        "platform": "kakuyomu",
        "lang": "ja",
        "name": "Kakuyomu",
        "url": "https://kakuyomu.jp/",
        "tech": "playwright",
        "status": "pending",
    },
    {
        "platform": "kakaopage",
        "lang": "ko",
        "name": "KakaoPage",
        "url": "https://page.kakao.com/",
        "tech": "playwright",
        "status": "pending",
    },
    {
        "platform": "naver_series",
        "lang": "ko",
        "name": "Naver Series",
        "url": "https://series.naver.com/",
        "tech": "playwright",
        "status": "pending",
    },
    {
        "platform": "munpia",
        "lang": "ko",
        "name": "Munpia",
        "url": "https://www.munpia.com/",
        "tech": "playwright",
        "status": "pending",
    },
    {
        "platform": "delitoon",
        "lang": "fr",
        "name": "Delitoon",
        "url": "https://www.delitoon.com/",
        "tech": "playwright",
        "status": "pending",
    },
]

# 按 platform 快速查找
SITES_BY_PLATFORM: dict[str, SiteConfig] = {s["platform"]: s for s in SITES}
