"""
后台爬虫服务：异步任务调度 + 批量写入流水线。

流程：
  1. API 端点创建 task_id，立即返回给前端
  2. asyncio 后台任务运行爬虫，实时更新 _task_store 状态
  3. 爬虫每积累 BATCH_SIZE 条数据，触发一次 ClickHouse 批量写入
  4. 前端轮询 /api/scrape/{task_id} 获取进度
"""
import asyncio
import uuid
from datetime import datetime

from database import batch_insert_async
from scrapers import SCRAPER_REGISTRY
from config import settings

# 内存任务表（生产环境可替换为 Redis）
_task_store: dict[str, dict] = {}


def create_task() -> str:
    """生成并注册新任务，返回 task_id。"""
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
    """
    后台协程：爬取 -> 分批写入 ClickHouse。
    通过 _task_store 对外暴露实时进度。
    """
    store = _task_store[task_id]
    store["status"] = "running"

    scraper_cls = SCRAPER_REGISTRY.get(platform)
    if scraper_cls is None:
        store["status"] = "failed"
        store["error"] = f"未知平台: {platform}"
        return

    try:
        scraper = scraper_cls()
        rows = await scraper.scrape(genre=genre, limit=limit)

        # Royal Road 只有周榜入口，写入前做兜底，防止 rank_type 意外为空
        if platform == "royal_road":
            for row in rows:
                if not row.get("rank_type"):
                    row["rank_type"] = "weekly"

        store["scraped"] = len(rows)

        # 分批写入 ClickHouse，每批 BATCH_SIZE 条
        batch_size = settings.scraper_batch_size
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            inserted = await batch_insert_async(batch)
            store["inserted"] += inserted
            # 让出事件循环，避免阻塞其他请求
            await asyncio.sleep(0)

        store["status"] = "done"

    except Exception as exc:
        import traceback
        store["status"] = "failed"
        store["error"] = traceback.format_exc()
