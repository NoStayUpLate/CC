"""
爬虫抽象基类：定义统一接口与共享工具方法。

子类选择继承 BasePlaywrightScraper（JS 渲染站点）或 BaseHttpScraper（REST API 站点）。
"""
from abc import ABC, abstractmethod

# ─────────────────────────────────────────────────────────
# S_adapt 标签白名单（爬虫端预计算用，与历史 SQL 版本保持一致）
# ─────────────────────────────────────────────────────────
_S_TAGS = frozenset([
    "werewolf", "alpha", "werewolf/alpha", "rebirth", "reincarnation",
    "revenge", "villainess", "穿越", "重生", "复仇",
])
_A_TAGS = frozenset([
    "ceo", "billionaire", "system", "litrpg", "contract marriage",
    "transmigration", "isekai", "regression", "banished", "契约婚姻",
])


class BaseScraper(ABC):
    """所有平台爬虫的抽象基类，仅含共享工具与接口定义。"""

    platform: str = ""
    lang: str = ""

    @abstractmethod
    async def scrape(self, genre: str = "", limit: int = 50) -> list[dict]:
        """入口方法：执行抓取并返回 NovelRow dict 列表。"""
        ...

    # ─────────────────────────────────────────────────────────
    # 共享工具方法
    # ─────────────────────────────────────────────────────────
    def _safe_int(self, text: str | None) -> int:
        """将 '1.2M'、'23K'、'1,234' 等字符串解析为整数，解析失败返回 0。"""
        if not text:
            return 0
        text = text.strip().replace(",", "").replace(" ", "")
        try:
            if text.upper().endswith("M"):
                return int(float(text[:-1]) * 1_000_000)
            if text.upper().endswith("K"):
                return int(float(text[:-1]) * 1_000)
            return int(float(text))
        except (ValueError, TypeError):
            return 0

    def _safe_int_or_none(self, text: str | None) -> int | None:
        """将数字字符串解析为整数，文本为空或解析失败时返回 None（不造假原则）。"""
        if text is None:
            return None
        text = text.strip().replace(",", "").replace(" ", "")
        if not text:
            return None
        try:
            if text.upper().endswith("M"):
                return int(float(text[:-1]) * 1_000_000)
            if text.upper().endswith("K"):
                return int(float(text[:-1]) * 1_000)
            return int(float(text))
        except (ValueError, TypeError):
            return None

    def _calc_s_adapt(self, tags: list[str]) -> float:
        """根据标签列表计算 S_adapt 基础分（0-100）。
        镜像原 ClickHouse SQL multiIf 逻辑，在爬虫端预计算并持久化存储。
        """
        lower_tags = {t.lower() for t in tags}
        s_hit = len(lower_tags & _S_TAGS)
        a_hit = len(lower_tags & _A_TAGS)
        if s_hit >= 2:
            return min(min(90.0 + s_hit * 2.0, 100.0) * 1.15, 100.0)
        if s_hit == 1:
            return 92.0
        if a_hit >= 1:
            return min(70.0 + a_hit * 5.0, 89.0)
        return 50.0

    def _make_row(self, **kwargs) -> dict:
        """构造标准 NovelRow dict，自动注入 platform、lang 和 s_adapt。
        views / likes 若未提供则保持 None（不造假原则）。
        top_keywords 由各平台爬虫在章节抓取后填充，默认 None。
        """
        v = kwargs.get("views")
        lk = kwargs.get("likes")
        tags = kwargs.get("tags", [])
        return {
            "title": kwargs.get("title", ""),
            "summary": kwargs.get("summary", ""),
            "tags": tags,
            "views": int(v) if v is not None else None,
            "likes": int(lk) if lk is not None else None,
            "original_url": kwargs.get("original_url", ""),
            "platform": self.platform,
            "lang": self.lang,
            "s_adapt": self._calc_s_adapt(tags),
            "top_keywords": None,
            "rank_type": kwargs.get("rank_type", ""),
        }
