"""
定时爬取调度器。

任务表：
  每天凌晨      → Wattpad / Syosetu 日榜
  每周一凌晨    → Royal Road 周榜 + Syosetu 周榜
  每月 1 号凌晨 → Syosetu 月榜

执行时间通过环境变量调整（默认凌晨 02:00 Asia/Shanghai）：
  SCHEDULE_ENABLED=false   关闭所有定时任务
  SCHEDULE_HOUR=3          改为凌晨 3 点
  SCHEDULE_LIMIT=100       每平台每次爬取上限
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from services.scraper_service import create_task, run_scrape_task

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 每天跑的平台（仅日榜）
_DAILY_PLATFORMS = ["wattpad", "syosetu_daily"]


async def _run_platforms(platforms: list[str], label: str) -> None:
    """顺序爬取指定平台列表，异常不中断后续任务。"""
    logger.info("[Scheduler] %s 开始，平台: %s", label, platforms)
    for platform in platforms:
        task_id = create_task()
        logger.info("[Scheduler] 平台=%s  task_id=%s", platform, task_id)
        try:
            await run_scrape_task(
                task_id=task_id,
                platform=platform,
                genre="",
                limit=settings.schedule_limit,
            )
            logger.info("[Scheduler] 平台=%s 完成", platform)
        except Exception:
            logger.exception("[Scheduler] 平台=%s 爬取异常", platform)
    logger.info("[Scheduler] %s 结束", label)


async def _daily_job() -> None:
    await _run_platforms(_DAILY_PLATFORMS, "日常爬取")


async def _weekly_job() -> None:
    await _run_platforms(["royal_road", "syosetu_weekly"], "周榜爬取（Royal Road + Syosetu）")


async def _monthly_job() -> None:
    await _run_platforms(["syosetu_monthly"], "Syosetu 月榜")


def setup_scheduler() -> AsyncIOScheduler:
    """注册所有 cron 任务，返回 scheduler（不启动）。"""
    if not settings.schedule_enabled:
        logger.info("[Scheduler] schedule_enabled=false，跳过注册")
        return scheduler

    h, m = settings.schedule_hour, settings.schedule_minute

    # 每天凌晨
    scheduler.add_job(
        _daily_job,
        trigger="cron",
        hour=h, minute=m,
        id="daily_scrape",
        replace_existing=True,
    )

    # 每周一凌晨
    scheduler.add_job(
        _weekly_job,
        trigger="cron",
        day_of_week="mon",
        hour=h, minute=m,
        id="weekly_syosetu",
        replace_existing=True,
    )

    # 每月 1 号凌晨
    scheduler.add_job(
        _monthly_job,
        trigger="cron",
        day=1,
        hour=h, minute=m,
        id="monthly_syosetu",
        replace_existing=True,
    )

    logger.info(
        "[Scheduler] 已注册 3 个任务，执行时间均为 %02d:%02d (Asia/Shanghai)\n"
        "  daily  : 每天（wattpad / syosetu 日榜）\n"
        "  weekly : 每周一（royal_road 周榜 / syosetu 周榜）\n"
        "  monthly: 每月 1 号（syosetu 月榜）",
        h, m,
    )
    return scheduler
