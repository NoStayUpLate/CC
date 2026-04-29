"""
海外短剧平台聚合爬虫。

平台级解析逻辑拆分在 scrapers/dramas 子目录；本模块只负责按统一顺序
调度各平台 scraper，并把输出补齐为 dramas 表需要的通用字段。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..base_http_scraper import BaseHttpScraper
from .en_dramabox_scraper import DramaBoxScraper
from .en_dramareels_scraper import DramaReelsScraper
from .en_dramawave_scraper import DramaWaveScraper
from .en_goodshort_scraper import GoodShortScraper
from .en_moboreels_scraper import MoboReelsScraper
from .en_netshort_scraper import NetShortScraper
from .en_reelshort_scraper import ReelShortScraper
from .en_shortmax_scraper import ShortMaxScraper
from .shortdrama_base import BaseShortDramaScraper


@dataclass(frozen=True)
class DramaSourceConfig:
    platform: str
    scraper_cls: type[BaseShortDramaScraper]
    limit: int


_PLATFORM_SCRAPERS: list[DramaSourceConfig] = [
    DramaSourceConfig("netshort", NetShortScraper, NetShortScraper.section_limit),
    DramaSourceConfig("shortmax", ShortMaxScraper, ShortMaxScraper.section_limit),
    DramaSourceConfig("reelshort", ReelShortScraper, ReelShortScraper.section_limit),
    DramaSourceConfig("dramabox", DramaBoxScraper, DramaBoxScraper.section_limit),
    DramaSourceConfig("dramareels", DramaReelsScraper, DramaReelsScraper.section_limit),
    DramaSourceConfig("dramawave", DramaWaveScraper, DramaWaveScraper.section_limit),
    DramaSourceConfig("goodshort", GoodShortScraper, GoodShortScraper.section_limit),
    DramaSourceConfig("moboreels", MoboReelsScraper, MoboReelsScraper.section_limit),
]


class ShortDramaTop5Scraper(BaseHttpScraper):
    platform = "shortdrama_top5"
    lang = "en"

    async def scrape(self, genre: str = "", limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        today = date.today()
        effective_limit = max(limit, self._minimum_full_platform_limit())

        for cfg in _PLATFORM_SCRAPERS:
            scraper = cfg.scraper_cls()
            items = await scraper.scrape(genre=genre, limit=cfg.limit)
            for idx, item in enumerate(items, start=1):
                if len(rows) >= effective_limit:
                    return rows[:effective_limit]
                rank_in_platform = int(item.get("rank_in_platform") or idx)
                rows.append(
                    {
                        "title": item["title"],
                        "summary": item.get("summary", ""),
                        "cover_url": item.get("cover_url", ""),
                        "tags": item.get("tags", []),
                        "episodes": item.get("episodes"),
                        "rank_in_platform": rank_in_platform,
                        "heat_score": float(max(0, 100 - (rank_in_platform - 1) * 8)),
                        "platform": cfg.platform,
                        "lang": getattr(scraper, "lang", "en"),
                        "rank_type": item.get("rank_type", ""),
                        "crawl_date": today,
                        "source_url": item.get("source_url") or getattr(scraper, "list_url", ""),
                    }
                )

        return rows[:effective_limit]

    def _minimum_full_platform_limit(self) -> int:
        """保证聚合抓取不会截断多栏位平台的完整输出。"""
        total = 0
        for cfg in _PLATFORM_SCRAPERS:
            section_count = max(1, len(getattr(cfg.scraper_cls, "section_order", [])))
            total += cfg.limit * section_count
        return total
