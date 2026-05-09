"""
数据抓取概览 API。

GET /api/overview → 返回每个平台的抓取统计 + 当前定时任务计划。

数据源：
  - novels / dramas 表的 GROUP BY platform 聚合
  - SCRAPER_REGISTRY / DRAMA_SCRAPER_REGISTRY 注册表（覆盖暂无数据的平台）
  - APScheduler 当前注册的 cron 任务
"""
from fastapi import APIRouter

from config import settings
from database import query_dicts
from scrapers import DRAMA_SCRAPER_REGISTRY, SCRAPER_REGISTRY
from services.scheduler import scheduler

router = APIRouter(prefix="/api/overview", tags=["overview"])


# 小说平台对应的定时任务粒度（与 services/scheduler.py 的注册顺序保持一致）
_NOVEL_SCHEDULE_HINT = {
    "wattpad": "daily",
    "syosetu_daily": "daily",
    "royal_road": "weekly",
    "syosetu_weekly": "weekly",
    "syosetu_monthly": "monthly",
}

# 短剧平台对应的定时任务粒度。
# shortdrama_top5 是聚合入口，每天跑一次 → 8 个子平台都被它覆盖。
_DRAMA_SCHEDULE_HINT = {
    "shortdrama_top5": "daily",
    "netshort": "daily",
    "shortmax": "daily",
    "reelshort": "daily",
    "dramabox": "daily",
    "dramareels": "daily",
    "dramawave": "daily",
    "goodshort": "daily",
    "moboreels": "daily",
}


_JOB_LABELS = {
    "daily_scrape": "每日抓取（小说日榜 + 短剧 shortdrama_top5 聚合 8 个平台）",
    "weekly_syosetu": "每周一抓取（Royal Road / Syosetu 周榜）",
    "monthly_syosetu": "每月 1 号 Syosetu 月榜",
}


# ─────────────────────────────────────────────────────────────
# 触发抓取的路由信息
# 1) 小说平台：与 SCRAPER_REGISTRY 一一对应 → kind=novel, key=自身
# 2) 短剧聚合 shortdrama_top5：可直接触发 → kind=drama, key=自身
# 3) 短剧 8 个子平台（netshort/.../shortmax）：未独立注册爬虫 →
#      kind=drama, key=shortdrama_top5（点按钮等于触发聚合任务）
# 不可触发的平台返回 trigger_key=None / trigger_kind=None。
# ─────────────────────────────────────────────────────────────
_DRAMA_AGGREGATE_KEY = "shortdrama_top5"
_DRAMA_SUBPLATFORMS = {
    "netshort", "shortmax", "reelshort", "dramabox",
    "dramareels", "dramawave", "goodshort", "moboreels",
}


def _build_trigger_meta(category: str, key: str) -> dict:
    if category == "novel" and key in SCRAPER_REGISTRY:
        return {"trigger_kind": "novel", "trigger_key": key, "trigger_via_aggregate": False}
    if category == "drama":
        if key == _DRAMA_AGGREGATE_KEY:
            return {"trigger_kind": "drama", "trigger_key": key, "trigger_via_aggregate": False}
        if key in _DRAMA_SUBPLATFORMS:
            return {"trigger_kind": "drama", "trigger_key": _DRAMA_AGGREGATE_KEY, "trigger_via_aggregate": True}
    return {"trigger_kind": None, "trigger_key": None, "trigger_via_aggregate": False}


def _platform_stats(table: str) -> dict[str, dict]:
    """读取 novels / dramas 的 per-platform 聚合统计。"""
    rows = query_dicts(
        f"""
        SELECT
            platform,
            count(*) AS total,
            max(created_at) AS last_crawled,
            count_if(created_at::DATE >= current_date - INTERVAL 7 DAY) AS recent_7d
        FROM {table}
        GROUP BY platform
        """
    )
    return {
        r["platform"]: {
            "total": int(r["total"]),
            "last_crawled": r["last_crawled"].isoformat() if r["last_crawled"] else None,
            "recent_7d": int(r["recent_7d"]),
        }
        for r in rows
    }


def _platform_rank_types(table: str) -> dict[str, list[dict]]:
    """
    按 (platform, rank_type) 聚合，返回 platform → [{rank_type, count}, ...]。
    每个 platform 内部按 count 降序，方便前端展示主力榜单类型。
    """
    rows = query_dicts(
        f"""
        SELECT platform, rank_type, count(*) AS cnt
        FROM {table}
        GROUP BY platform, rank_type
        ORDER BY platform ASC, cnt DESC
        """
    )
    out: dict[str, list[dict]] = {}
    for r in rows:
        platform = r["platform"]
        rank_type = r["rank_type"] or ""  # 空值统一成空串，前端展示「未分类」
        out.setdefault(platform, []).append({
            "rank_type": rank_type,
            "count": int(r["cnt"]),
        })
    return out


@router.get("")
def get_overview():
    """返回 [小说+短剧] 各平台的抓取情况 + 定时任务列表。"""
    novel_stats = _platform_stats("novels")
    drama_stats = _platform_stats("dramas")
    novel_ranks = _platform_rank_types("novels")
    drama_ranks = _platform_rank_types("dramas")

    platforms: list[dict] = []
    seen_novel: set[str] = set()
    seen_drama: set[str] = set()

    # 小说：先吐 DB 中已有数据的平台
    for key, s in novel_stats.items():
        platforms.append({
            "key": key,
            "category": "novel",
            "schedule": _NOVEL_SCHEDULE_HINT.get(key, "manual"),
            "rank_types": novel_ranks.get(key, []),
            **_build_trigger_meta("novel", key),
            **s,
        })
        seen_novel.add(key)

    # 注册了但暂时没数据的小说爬虫
    for key in SCRAPER_REGISTRY.keys():
        if key in seen_novel:
            continue
        platforms.append({
            "key": key,
            "category": "novel",
            "schedule": _NOVEL_SCHEDULE_HINT.get(key, "manual"),
            "rank_types": [],
            **_build_trigger_meta("novel", key),
            "total": 0,
            "last_crawled": None,
            "recent_7d": 0,
        })

    # 短剧：DB 中所有平台（含 shortdrama_top5 聚合产出的子平台 netshort/reelshort 等）
    for key, s in drama_stats.items():
        platforms.append({
            "key": key,
            "category": "drama",
            "schedule": _DRAMA_SCHEDULE_HINT.get(key, "manual"),
            "rank_types": drama_ranks.get(key, []),
            **_build_trigger_meta("drama", key),
            **s,
        })
        seen_drama.add(key)

    # 注册了但暂时没数据的短剧爬虫
    for key in DRAMA_SCRAPER_REGISTRY.keys():
        if key in seen_drama:
            continue
        platforms.append({
            "key": key,
            "category": "drama",
            "schedule": _DRAMA_SCHEDULE_HINT.get(key, "manual"),
            "rank_types": [],
            **_build_trigger_meta("drama", key),
            "total": 0,
            "last_crawled": None,
            "recent_7d": 0,
        })

    # 定时任务（设 schedule_enabled=false 时直接返回空列表）
    jobs: list[dict] = []
    if settings.schedule_enabled:
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "label": _JOB_LABELS.get(job.id, job.id),
                "trigger": str(job.trigger),
                "next_run": next_run.isoformat() if next_run else None,
            })

    return {
        "platforms": platforms,
        "schedule": {
            "enabled": settings.schedule_enabled,
            "hour": settings.schedule_hour,
            "minute": settings.schedule_minute,
            "limit_per_platform": settings.schedule_limit,
            "timezone": "Asia/Shanghai",
            "jobs": jobs,
        },
    }
