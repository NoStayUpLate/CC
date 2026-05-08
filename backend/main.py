"""
FastAPI 应用入口。

启动顺序：
  1. fail-fast 校验 JWT_SECRET（未配置直接退出，避免裸出 API）
  2. lifespan 上下文：执行 ClickHouse DDL（建表）+ 启动定时爬取调度器
  3. 注册路由：auth（开放）/ novels、dramas、scraper（require_user 守卫）
  4. CORS：仅本地 dev 源（生产同源走 nginx，不需要跨域）
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.dependencies import require_user
from config import settings
from database import init_db_async
from routers.auth import router as auth_router
from routers.dramas import router as dramas_router
from routers.novels import router as novels_router
from routers.overview import router as overview_router
from routers.scraper import router as scraper_router
from services.scheduler import setup_scheduler

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Fail-fast：JWT_SECRET 未设置时拒绝启动，防止裸出业务接口
# ─────────────────────────────────────────────────────────
if not settings.jwt_secret:
    raise RuntimeError(
        "JWT_SECRET 未配置。请在 backend/.env 设置 JWT_SECRET="
        "（建议 `openssl rand -hex 32` 生成）。"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时执行建表 DDL，并启动定时爬取调度器。"""
    await init_db_async()

    sched = setup_scheduler()
    if settings.schedule_enabled:
        sched.start()
        logger.info(
            "[Scheduler] 定时爬取已启动，每天 %02d:%02d 执行",
            settings.schedule_hour,
            settings.schedule_minute,
        )

    yield

    if settings.schedule_enabled and sched.running:
        sched.shutdown(wait=False)
        logger.info("[Scheduler] 调度器已关闭")


app = FastAPI(
    title="海外小说数据监测看板",
    version="8.0.0",
    description="基于 GHI 算法筛选具有短剧转化潜力的海外网文 IP",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 鉴权路由本身不上锁
app.include_router(auth_router)

# 业务路由全部走 require_user 守卫，未登录的请求会拿到 401
_protected = [Depends(require_user)]
app.include_router(novels_router, dependencies=_protected)
app.include_router(dramas_router, dependencies=_protected)
app.include_router(scraper_router, dependencies=_protected)
app.include_router(overview_router, dependencies=_protected)


@app.get("/health")
def health():
    return {"status": "ok", "version": "8.0.1-debug"}


@app.get("/debug/wattpad-chapter", dependencies=_protected)
async def debug_wattpad_chapter(story_id: str = "401824573"):
    """临时调试端点：测试容器内能否访问 Wattpad 章节文本 API。用完删除。"""
    import asyncio, traceback
    import requests as _req
    results = {}

    # 1. 拉章节列表
    try:
        r1 = _req.get(
            f"https://www.wattpad.com/api/v3/stories/{story_id}?fields=parts",
            headers={"Accept": "application/json",
                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=15,
        )
        parts = r1.json().get("parts", [])
        results["parts_status"] = r1.status_code
        results["parts_count"] = len(parts)
        first_part_id = parts[0]["id"] if parts else None
        results["first_part_id"] = first_part_id
    except Exception as e:
        results["parts_error"] = traceback.format_exc(limit=3)
        first_part_id = None

    # 2. 拉章节正文
    if first_part_id:
        try:
            r2 = _req.get(
                f"https://www.wattpad.com/apiv2/storytext?id={first_part_id}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=15,
            )
            results["text_status"] = r2.status_code
            results["text_preview"] = r2.text[:200]
        except Exception as e:
            results["text_error"] = traceback.format_exc(limit=3)

    return results
