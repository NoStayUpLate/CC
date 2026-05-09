from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DuckDB 数据库文件路径（嵌入式，无独立 server 进程）。
    # 生产 compose 把宿主卷 duckdb_data 挂到 /data，所以容器里默认 /data/dashboard.duckdb；
    # 本地开发自动落到项目根的 backend/dashboard.duckdb。
    duckdb_path: str = "./dashboard.duckdb"
    scraper_headless: bool = True
    scraper_batch_size: int = 50
    scraper_delay_min: float = 1.0
    scraper_delay_max: float = 3.5
    http_proxy: str = ""

    # 定时爬取配置
    schedule_enabled: bool = True
    schedule_hour: int = 2       # 每天凌晨 2 点执行
    schedule_minute: int = 0
    schedule_limit: int = 100    # 每平台每次爬取条数

    # ─────────────────────────────────────────────────────────
    # 鉴权 / 登录
    # auth_backend = "file"   → 用户写在 AUTH_USERS 环境变量
    #                           （格式 "user1:bcrypt_hash;user2:bcrypt_hash"）
    # auth_backend = "sqlite" → 用 stdlib sqlite3 存储，CLI 管理
    # cookie_secure 上云 HTTPS 时必须置 true，否则浏览器拒绝设 Set-Cookie
    # ─────────────────────────────────────────────────────────
    auth_backend: Literal["file", "sqlite"] = "file"
    auth_users: str = ""
    auth_sqlite_path: str = "./auth_users.db"
    jwt_secret: str = ""
    jwt_expire_hours: int = 8
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # 注册邀请码：空串 = 注册功能完全关闭；非空且 backend=sqlite 时启用
    # 配置举例（.env）：REGISTRATION_CODE=team-2026-spring
    # 修改邀请码相当于作废历史邀请，立即对未注册者生效
    registration_code: str = ""

    class Config:
        env_file = ".env"
        # 允许 .env 残留旧字段（如历史的 CLICKHOUSE_*）不导致启动失败 —
        # 上线后这些字段不再使用，但用户的本地/服务器 .env 可能还在
        extra = "ignore"


settings = Settings()
