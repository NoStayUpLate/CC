"""
海外短剧列表 & 爬虫 API。
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from database import get_client
from models import DramaOut, DramasResponse, ScrapeRequest, ScrapeStatusResponse
from services.drama_scraper_service import (
    create_task,
    get_task,
    run_scrape_task,
)

router = APIRouter(prefix="/api/dramas", tags=["dramas"])


def _build_where(
    platform: Optional[str],
    title: Optional[str],
    date_range: Optional[str],
    rank_type: Optional[str],
) -> tuple[str, dict]:
    conditions: list[str] = []
    params: dict = {}

    if platform:
        conditions.append("platform = {platform:String}")
        params["platform"] = platform

    if title:
        conditions.append("lower(title) LIKE {title_pat:String}")
        params["title_pat"] = f"%{title.lower()}%"

    if date_range == "today":
        conditions.append("toDate(created_at) = today()")
    elif date_range == "week":
        conditions.append("created_at >= toMonday(today())")
    elif date_range == "month":
        conditions.append("created_at >= toStartOfMonth(today())")

    if rank_type:
        conditions.append("rank_type = {rank_type:String}")
        params["rank_type"] = rank_type

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
    )


@router.get("", response_model=DramasResponse)
def list_dramas(
    platform: Optional[str] = Query(None, description="平台名称，如 reelshort"),
    title: Optional[str] = Query(None, description="短剧标题关键词"),
    date_range: Optional[str] = Query(None, description="时间范围: today / week / month"),
    rank_type: Optional[str] = Query(None, description="榜单类型，如 轮播推荐 / 推荐栏位 / 最近上新"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    where_clause, params = _build_where(platform, title, date_range, rank_type)
    offset = (page - 1) * page_size
    sql = f"""
    SELECT
        id, title, summary, cover_url, tags, episodes, rank_in_platform,
        heat_score, platform, lang, rank_type, crawl_date, source_url, created_at
    FROM dramas
    {where_clause}
    ORDER BY crawl_date DESC, heat_score DESC, created_at DESC
    LIMIT {page_size} OFFSET {offset}
    """
    count_sql = f"SELECT count() FROM dramas {where_clause}"

    client = get_client()
    try:
        result = client.query(sql, parameters=params)
        count_result = client.query(count_sql, parameters=params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse 查询失败: {exc}")

    total = int(count_result.first_row[0]) if count_result.first_row else 0
    items = [_row_to_drama(r) for r in result.named_results()]
    return DramasResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/meta/platforms")
def get_platforms():
    client = get_client()
    result = client.query("SELECT DISTINCT platform FROM dramas ORDER BY platform")
    return {"platforms": [r[0] for r in result.result_rows]}


@router.get("/meta/langs")
def get_langs():
    client = get_client()
    result = client.query("SELECT DISTINCT lang FROM dramas ORDER BY lang")
    return {"langs": [r[0] for r in result.result_rows]}


@router.get("/meta/tags")
def get_tags():
    client = get_client()
    result = client.query("""
        SELECT tag, count() AS cnt
        FROM (
            SELECT arrayJoin(tags) AS tag FROM dramas
        )
        GROUP BY tag
        ORDER BY cnt DESC
        LIMIT 50
    """)
    return {"tags": [r[0] for r in result.result_rows]}


@router.get("/{drama_id}", response_model=DramaOut)
def get_drama(drama_id: str):
    client = get_client()
    sql = """
    SELECT
        id, title, summary, cover_url, tags, episodes, rank_in_platform,
        heat_score, platform, lang, rank_type, crawl_date, source_url, created_at
    FROM dramas
    WHERE toString(id) = {drama_id:String}
    LIMIT 1
    """
    try:
        result = client.query(sql, parameters={"drama_id": drama_id})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse 查询失败: {exc}")
    rows = list(result.named_results())
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
