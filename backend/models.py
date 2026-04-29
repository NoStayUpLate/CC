from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class NovelRow(BaseModel):
    """ClickHouse 写入行结构（爬虫端 -> 存储端）"""
    title: str
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    views: Optional[int] = None
    likes: Optional[int] = None
    original_url: str
    platform: str
    lang: str
    s_adapt: float = 50.0
    top_keywords: Optional[dict[str, int]] = None
    rank_type: str = ""


class NovelOut(BaseModel):
    """API 对外输出结构（含 GHI 分析结果）"""
    id: str
    title: str
    summary: Optional[str] = None
    tags: list[str]
    views: Optional[int] = None
    likes: Optional[int] = None
    original_url: str
    platform: str
    lang: str
    created_at: datetime
    # GHI 各分项
    s_popular: float
    s_engage: float
    s_adapt: float
    ghi: float
    # 黄金三秒判定
    has_hook: bool
    # 关键词云（列表端点不返回，详情端点 GET /api/novels/{id} 返回）
    top_keywords: Optional[dict[str, int]] = None
    rank_type: str = ""


class NovelsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[NovelOut]


class ScrapeRequest(BaseModel):
    platform: str          # 例如 wattpad / royal_road / syosetu_weekly / shortdrama_top5
    genre: str = ""        # 抓取的题材关键词，平台不同含义不同
    limit: int = Field(default=50, ge=1, le=200)


class ScrapeStatusResponse(BaseModel):
    task_id: str
    status: str            # pending | running | done | failed
    scraped: int = 0
    inserted: int = 0
    error: Optional[str] = None


class DramaRow(BaseModel):
    """短剧写入行结构（爬虫端 -> 存储端）"""
    title: str
    summary: str = ""
    cover_url: str = ""
    tags: list[str] = Field(default_factory=list)
    episodes: Optional[int] = None
    rank_in_platform: int = 0
    heat_score: float = 0.0
    platform: str
    lang: str = "en"
    rank_type: str = ""
    crawl_date: Optional[date] = None
    source_url: str = ""


class DramaOut(BaseModel):
    """短剧列表/详情输出结构"""
    id: str
    title: str
    summary: Optional[str] = None
    cover_url: str = ""
    tags: list[str]
    episodes: Optional[int] = None
    rank_in_platform: int = 0
    heat_score: float = 0.0
    platform: str
    lang: str
    rank_type: str = ""
    crawl_date: Optional[date] = None
    source_url: str = ""
    created_at: datetime


class DramasResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[DramaOut]
