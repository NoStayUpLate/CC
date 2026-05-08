"""
一次性脚本：直接调用 shortdrama_top5 聚合爬虫，重抓 8 平台短剧并写入 ClickHouse。

绕开 HTTP / 鉴权，复用 backend/services/drama_scraper_service.py 的写入路径。
完成后执行 OPTIMIZE FINAL 触发 ReplacingMergeTree 按 (platform, title) 去重，
同名旧记录会被新记录覆盖（crawl_date 刷新为今天，rank_in_platform 也是最新）。

用法（必须从项目根跑，脚本内部会切到 backend 目录加载 .env）：
    python scripts/rerun_drama_scrape.py
"""
import asyncio
import os
import sys
from pathlib import Path

# database.py 通过 pydantic-settings 读 backend/.env，所以 cwd 必须是 backend
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from scrapers import DRAMA_SCRAPER_REGISTRY  # noqa: E402
from database import batch_insert_dramas_async, optimize_dramas_final_async  # noqa: E402
from config import settings  # noqa: E402


async def main():
    print("[scrape] 启动 shortdrama_top5 聚合爬虫（NetShort / ShortMax / ReelShort / DramaBox / DramaReels / DramaWave / GoodShort / MoboReels）", flush=True)

    scraper_cls = DRAMA_SCRAPER_REGISTRY.get("shortdrama_top5")
    if scraper_cls is None:
        print("[scrape] ERROR: shortdrama_top5 未在 DRAMA_SCRAPER_REGISTRY 中注册", flush=True)
        return

    scraper = scraper_cls()
    rows = await scraper.scrape(genre="", limit=200)
    print(f"[scrape] 抓到 {len(rows)} 行", flush=True)

    if not rows:
        print("[scrape] 无数据，跳过写入", flush=True)
        return

    # 与 drama_scraper_service.run_scrape_task 保持一致：rank_type 兜底空串
    for row in rows:
        row["rank_type"] = row.get("rank_type") or ""

    # 分批写入
    batch_size = settings.scraper_batch_size
    total_inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        n = await batch_insert_dramas_async(batch)
        total_inserted += n
        print(f"[scrape] 已写入 {total_inserted}/{len(rows)}", flush=True)

    print("[scrape] 执行 OPTIMIZE FINAL 触发去重...", flush=True)
    await optimize_dramas_final_async()
    print(f"[scrape] 全部完成。共抓 {len(rows)} 行，写入 {total_inserted} 行。", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
