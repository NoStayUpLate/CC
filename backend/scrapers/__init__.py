from functools import partial

from .novels.en_wattpad_scraper import WattpadScraper
from .novels.en_royal_road_scraper import RoyalRoadScraper
from .novels.ja_syosetu_scraper import SyosetuRankScraper
from .dramas.en_shortdrama_top5_scraper import ShortDramaTop5Scraper
from .dramas.en_netshort_scraper import NetShortScraper
from .dramas.en_reelshort_scraper import ReelShortScraper
from .dramas.en_dramabox_scraper import DramaBoxScraper
from .dramas.en_dramareels_scraper import DramaReelsScraper
from .dramas.en_dramawave_scraper import DramaWaveScraper
from .dramas.en_goodshort_scraper import GoodShortScraper
from .dramas.en_moboreels_scraper import MoboReelsScraper
from .dramas.en_shortmax_scraper import ShortMaxScraper

# partial 包装使每个 key 仍可以无参 scraper_cls() 方式调用
SCRAPER_REGISTRY: dict = {
    "wattpad":         WattpadScraper,
    "royal_road":      RoyalRoadScraper,
    "syosetu_daily":   partial(SyosetuRankScraper, rank_type="daily"),
    "syosetu_weekly":  partial(SyosetuRankScraper, rank_type="weekly"),
    "syosetu_monthly": partial(SyosetuRankScraper, rank_type="monthly"),
}

DRAMA_SCRAPER_REGISTRY: dict = {
    "shortdrama_top5": ShortDramaTop5Scraper,
}

__all__ = [
    "SCRAPER_REGISTRY",
    "WattpadScraper",
    "RoyalRoadScraper",
    "ShortDramaTop5Scraper",
    "NetShortScraper",
    "ReelShortScraper",
    "DramaBoxScraper",
    "DramaReelsScraper",
    "DramaWaveScraper",
    "GoodShortScraper",
    "MoboReelsScraper",
    "ShortMaxScraper",
    "SyosetuRankScraper",
    "DRAMA_SCRAPER_REGISTRY",
]
