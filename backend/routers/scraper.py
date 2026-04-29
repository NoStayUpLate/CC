"""
爬虫触发 & 状态查询 API。

POST /api/scrape       → 触发异步爬取任务，立即返回 task_id
GET  /api/scrape/{id} → 查询任务状态与进度
"""
import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException

from models import ScrapeRequest, ScrapeStatusResponse
from services.scraper_service import create_task, get_task, run_scrape_task

router = APIRouter(prefix="/api/scrape", tags=["scraper"])


@router.post("", response_model=ScrapeStatusResponse, status_code=202)
async def trigger_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    触发后台爬取任务。
    立即返回 task_id（HTTP 202），前端通过 GET /api/scrape/{task_id} 轮询进度。
    """
    task_id = create_task()
    # 注册为 FastAPI BackgroundTask，与请求生命周期解耦
    background_tasks.add_task(
        run_scrape_task,
        task_id=task_id,
        platform=req.platform,
        genre=req.genre,
        limit=req.limit,
    )
    return ScrapeStatusResponse(task_id=task_id, status="pending")


@router.get("/{task_id}", response_model=ScrapeStatusResponse)
def get_scrape_status(task_id: str):
    """查询指定爬取任务的实时状态。"""
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
