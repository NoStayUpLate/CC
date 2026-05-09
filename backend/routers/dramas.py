"""
海外短剧列表 & 爬虫 API。

DHI = (S_tag × 0.45) + (S_position × 0.35) + (S_recency × 0.20)
  S_tag      = least(50 + s_hits × 25 + a_hits × 12, 100)（S/A 标签命中数加权）
  S_position = greatest(100 - (rank_in_platform - 1) × 8, 0)（资源位名次线性换算）
  S_recency  = greatest(100 - 10 × date_diff('day', crawl_date, current_date), 0)（10 天衰减归零）
全部在 DuckDB SQL 内计算，与小说 GHI 模式对仗。
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from database import query_dicts, query_scalar
from models import DramaOut, DramasResponse, ScrapeRequest, ScrapeStatusResponse
from services.drama_scraper_service import (
    create_task,
    get_task,
    run_scrape_task,
)

router = APIRouter(prefix="/api/dramas", tags=["dramas"])


# ─────────────────────────────────────────────────────────────
# DHI 标签清单（基于真实数据 + 业务直觉，与小说 _S_TAGS / _A_TAGS 互不影响）
# 全部小写存储，匹配时 SQL 用 list_intersect(list_transform(tags, lower), [...]) 做大小写不敏感比对
# ─────────────────────────────────────────────────────────────
_S_TAGS_DRAMA = {
    "werewolf", "revenge", "rebirth", "reincarnation", "reborn",
    "karma payback", "hidden identity", "secret identity", "comeback", "mafia",
}
_A_TAGS_DRAMA = {
    "ceo", "billionaire", "modern romance", "contract marriage", "sweet",
    "underdog rise", "strong female lead", "urban fantasy", "one night stand", "family",
}


def _tag_array_literal(tags: set[str]) -> str:
    """把 Python set 转成 DuckDB list 字面量，如 ['ceo','billionaire']"""
    return "[" + ",".join(f"'{t}'" for t in sorted(tags)) + "]"


_S_TAGS_SQL = _tag_array_literal(_S_TAGS_DRAMA)
_A_TAGS_SQL = _tag_array_literal(_A_TAGS_DRAMA)


# ─────────────────────────────────────────────────────────────
# DHI SQL 模板（内层算分项 → 外层加权）
# 嵌套 replace：先填入 S/A 标签字面量，运行时再填 where_clause / limit / offset。
# ─────────────────────────────────────────────────────────────
_DHI_SQL_TEMPLATE = """
SELECT
    id, title, summary, cover_url, tags, episodes, rank_in_platform,
    heat_score, platform, lang, rank_type, crawl_date, source_url, created_at,
    round(s_tag, 2)      AS s_tag,
    round(s_position, 2) AS s_position,
    round(s_recency, 2)  AS s_recency,
    round((s_tag * 0.45) + (s_position * 0.35) + (s_recency * 0.20), 2) AS dhi
FROM (
    SELECT
        id, title, summary, cover_url, tags, episodes, rank_in_platform,
        heat_score, platform, lang, rank_type, crawl_date, source_url, created_at,
        least(50.0
              + len(list_intersect(list_transform(tags, x -> lower(x)), {s_tags})) * 25.0
              + len(list_intersect(list_transform(tags, x -> lower(x)), {a_tags})) * 12.0,
              100.0) AS s_tag,
        greatest(100.0 - (rank_in_platform::DOUBLE - 1.0) * 8.0, 0.0) AS s_position,
        greatest(100.0 - 10.0 * date_diff('day', crawl_date, current_date)::DOUBLE, 0.0) AS s_recency
    FROM dramas
    {where_clause}
) AS raw
"""

# 先固化 S/A 标签数组，run-time 再填 where/limit/offset
_DHI_SQL_BASE = (
    _DHI_SQL_TEMPLATE
    .replace("{s_tags}", _S_TAGS_SQL)
    .replace("{a_tags}", _A_TAGS_SQL)
)


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _build_where(
    platform: Optional[str],
    title: Optional[str],
    date_range: Optional[str],
    rank_type: Optional[str],
    lang: Optional[str] = None,
) -> tuple[str, dict]:
    conditions: list[str] = []
    params: dict = {}

    platforms = _split_csv(platform)
    if platforms:
        conditions.append("platform = ANY($platforms)")
        params["platforms"] = platforms

    langs = _split_csv(lang)
    if langs:
        conditions.append("lang = ANY($langs)")
        params["langs"] = langs

    if title:
        conditions.append("lower(title) LIKE $title_pat")
        params["title_pat"] = f"%{title.lower()}%"

    if date_range == "today":
        conditions.append("created_at::DATE = current_date")
    elif date_range == "week":
        conditions.append("created_at >= date_trunc('week', current_date)")
    elif date_range == "month":
        conditions.append("created_at >= date_trunc('month', current_date)")

    rank_types = _split_csv(rank_type)
    if rank_types:
        conditions.append("rank_type = ANY($rank_types)")
        params["rank_types"] = rank_types

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_clause, params


def _row_to_drama(row: dict) -> DramaOut:
    return DramaOut(
        id=str(row.get("id", "")),
        title=row.get("title") or "",
        summary=row.get("summary") or None,
        cover_url=row.get("cover_url") or "",
        tags=row.get("tags") or [],
        episodes=row.get("episodes"),
        rank_in_platform=int(row.get("rank_in_platform") or 0),
        heat_score=float(row.get("heat_score") or 0),
        platform=row.get("platform") or "",
        lang=row.get("lang") or "en",
        rank_type=row.get("rank_type") or "",
        crawl_date=row.get("crawl_date"),
        source_url=row.get("source_url") or "",
        created_at=row.get("created_at"),
        s_tag=float(row.get("s_tag") or 0),
        s_position=float(row.get("s_position") or 0),
        s_recency=float(row.get("s_recency") or 0),
        dhi=float(row.get("dhi") or 0),
    )


@router.get("", response_model=DramasResponse)
def list_dramas(
    platform: Optional[str] = Query(None, description="平台名称，多选用逗号分隔"),
    lang: Optional[str] = Query(None, description="内容语言，多选用逗号分隔"),
    title: Optional[str] = Query(None, description="短剧标题关键词"),
    date_range: Optional[str] = Query(None, description="时间范围: today / week / month"),
    rank_type: Optional[str] = Query(None, description="榜单类型，多选用逗号分隔"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    where_clause, params = _build_where(platform, title, date_range, rank_type, lang)
    offset = (page - 1) * page_size

    sql = _DHI_SQL_BASE.replace("{where_clause}", where_clause)
    sql = f"{sql}\n    ORDER BY dhi DESC\n    LIMIT {page_size} OFFSET {offset}"

    count_sql = f"SELECT count(*) FROM dramas {where_clause}"

    try:
        rows = query_dicts(sql, params)
        total = int(query_scalar(count_sql, params) or 0)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DuckDB 查询失败: {exc}")

    items = [_row_to_drama(r) for r in rows]
    return DramasResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/meta/platforms")
def get_platforms():
    rows = query_dicts("SELECT DISTINCT platform FROM dramas ORDER BY platform")
    return {"platforms": [r["platform"] for r in rows]}


@router.get("/meta/langs")
def get_langs():
    rows = query_dicts("SELECT DISTINCT lang FROM dramas ORDER BY lang")
    return {"langs": [r["lang"] for r in rows]}


@router.get("/meta/tags")
def get_tags():
    rows = query_dicts("""
        SELECT tag, count(*) AS cnt
        FROM (SELECT unnest(tags) AS tag FROM dramas)
        GROUP BY tag
        ORDER BY cnt DESC
        LIMIT 50
    """)
    return {"tags": [r["tag"] for r in rows]}


@router.get("/{drama_id}", response_model=DramaOut)
def get_drama(drama_id: str):
    """单条详情：复用 DHI 模板，确保前端 DramaModal 拿到分项分。"""
    where_clause = "WHERE CAST(id AS VARCHAR) = $drama_id"
    sql = _DHI_SQL_BASE.replace("{where_clause}", where_clause) + "\n    LIMIT 1"

    try:
        rows = query_dicts(sql, {"drama_id": drama_id})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DuckDB 查询失败: {exc}")

    if not rows:
        raise HTTPException(status_code=404, detail="短剧不存在")
    return _row_to_drama(rows[0])


@router.post("/scrape", response_model=ScrapeStatusResponse, status_code=202)
async def trigger_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    task_id = create_task()
    background_tasks.add_task(
        run_scrape_task,
        task_id=task_id,
        platform=req.platform,
        genre=req.genre,
        limit=req.limit,
    )
    return ScrapeStatusResponse(task_id=task_id, status="pending")


@router.get("/scrape/{task_id}", response_model=ScrapeStatusResponse)
def get_scrape_status(task_id: str):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ScrapeStatusResponse(
        task_id=task_id,
        status=task["status"],
        scraped=task["scraped"],
        inserted=task["inserted"],
        error=task.get("error"),
    )
