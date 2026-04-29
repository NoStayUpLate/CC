"""
短剧爬虫后台服务：异步任务调度 + 批量写入 dramas 表。
"""
import asyncio
import uuid
from datetime import datetime

from config import settings
from database import batch_insert_dramas_async, optimize_dramas_final_async
from scrapers import DRAMA_SCRAPER_REGISTRY

_task_store: dict[str, dict] = {}


def create_task() -> str:
    task_id = str(uuid.uuid4())
    _task_store[task_id] = {
        "status": "pending",
        "scraped": 0,
        "inserted": 0,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    return task_id


def get_task(task_id: str) -> dict | None:
    return _task_store.get(task_id)


async def run_scrape_task(
    task_id: str,
    platform: str,
    genre: str,
    limit: int,
) -> None:
    store = _task_store[task_id]
    store["status"] = "running"

    scraper_cls = DRAMA_SCRAPER_REGISTRY.get(platform)
    if scraper_cls is None:
        store["status"] = "failed"
        store["error"] = f"未知短剧平台: {platform}"
        return

    try:
        scraper = scraper_cls()
        rows = await scraper.scrape(genre=genre, limit=limit)
        for row in rows:
            row["rank_type"] = row.get("rank_type") or ""

        store["scraped"] = len(rows)
        batch_size = settings.scraper_batch_size
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            inserted = await batch_insert_dramas_async(batch)
            store["inserted"] += inserted
            await asyncio.sleep(0)

        # 抓取完成后执行 CH FINAL 合并，确保按 (platform, title) 去重
        await optimize_dramas_final_async()

        store["status"] = "done"
    except Exception:
        import traceback
        store["status"] = "failed"
        store["error"] = traceback.format_exc()
