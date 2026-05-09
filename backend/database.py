"""
DuckDB 嵌入式数据库连接管理。

替代 ClickHouse 的轻量化方案：
  - 单文件 (settings.duckdb_path)，无独立 server 进程，省 600MB+ 内存
  - 单进程内多线程：共享一个 connection + 显式锁（DuckDB 写入串行化）
  - 列式存储 + Map / Array 都原生支持，GHI/DHI 的 SQL 结构基本平移即可

关键差异（与 CH 时代相比）：
  - top_keywords 改用 JSON 字符串落盘（DuckDB 的 MAP 在 Python 绑定上较生涩，
    用 VARCHAR + json.dumps/json.loads 反而最省心）
  - tags 仍是 VARCHAR[]（DuckDB 原生 list 类型，list_has_any/list_transform 都可用）
  - 去重通过 PRIMARY KEY + ON CONFLICT DO UPDATE 实现，对应原 ReplacingMergeTree
    语义；id (UUID) 在第一次插入时生成，后续 rescrape 不变
"""
import asyncio
import json
import threading
from datetime import date
from pathlib import Path

import duckdb

from config import settings

# 数据库文件路径（绝对化，确保挂载卷里能定位）
_DB_PATH = Path(settings.duckdb_path).expanduser().resolve()
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# DuckDB 单文件不允许多进程同时持有写锁；单进程多线程则需要应用层串行化
# （DuckDB 的 Python connection 不是线程安全的，要么每线程 cursor()，要么加锁）。
# 单用户看板写入极少、读取也不重，全局锁的开销可以忽略。
_lock = threading.RLock()
_con: duckdb.DuckDBPyConnection | None = None


def get_client() -> duckdb.DuckDBPyConnection:
    """返回模块级 DuckDB 连接；首次调用时按需 open。"""
    global _con
    with _lock:
        if _con is None:
            _con = duckdb.connect(str(_DB_PATH))
        return _con


# ─────────────────────────────────────────────────────────────
# DDL（DuckDB 语法；与 CH 时代字段一一对应）
# ─────────────────────────────────────────────────────────────
_CREATE_NOVELS_SQL = """
CREATE TABLE IF NOT EXISTS novels (
    id            UUID         DEFAULT uuid(),
    title         VARCHAR      NOT NULL,
    summary       VARCHAR      DEFAULT '',
    tags          VARCHAR[]    DEFAULT [],
    views         BIGINT,
    likes         BIGINT,
    original_url  VARCHAR      NOT NULL,
    platform      VARCHAR      NOT NULL,
    lang          VARCHAR      DEFAULT 'en',
    s_adapt       FLOAT        DEFAULT 50.0,
    top_keywords  VARCHAR      DEFAULT '{}',
    rank_type     VARCHAR      DEFAULT '',
    created_at    TIMESTAMP    DEFAULT current_timestamp,
    PRIMARY KEY (platform, lang, title)
)
"""

_CREATE_DRAMAS_SQL = """
CREATE TABLE IF NOT EXISTS dramas (
    id                UUID       DEFAULT uuid(),
    title             VARCHAR    NOT NULL,
    summary           VARCHAR    DEFAULT '',
    cover_url         VARCHAR    DEFAULT '',
    tags              VARCHAR[]  DEFAULT [],
    episodes          INTEGER,
    rank_in_platform  SMALLINT   DEFAULT 0,
    heat_score        FLOAT      DEFAULT 0,
    platform          VARCHAR    NOT NULL,
    lang              VARCHAR    DEFAULT 'en',
    rank_type         VARCHAR    DEFAULT '',
    crawl_date        DATE       DEFAULT current_date,
    source_url        VARCHAR    DEFAULT '',
    created_at        TIMESTAMP  DEFAULT current_timestamp,
    PRIMARY KEY (platform, title)
)
"""


def init_db() -> None:
    """启动时建表（幂等）。"""
    con = get_client()
    with _lock:
        con.execute(_CREATE_NOVELS_SQL)
        con.execute(_CREATE_DRAMAS_SQL)


async def init_db_async() -> None:
    await asyncio.to_thread(init_db)


# ─────────────────────────────────────────────────────────────
# 查询辅助：把 DuckDB 的 (cols, rows) 拼回 dict 列表，方便 router 复用 _row_to_xxx
# ─────────────────────────────────────────────────────────────
def query_dicts(sql: str, params: dict | list | None = None) -> list[dict]:
    """执行 SELECT，把每一行打成 {column: value} dict。"""
    con = get_client()
    with _lock:
        cur = con.execute(sql, params if params is not None else [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def query_scalar(sql: str, params: dict | list | None = None):
    """执行 SELECT 取第一行第一列；常用于 COUNT。"""
    con = get_client()
    with _lock:
        cur = con.execute(sql, params if params is not None else [])
        row = cur.fetchone()
        return row[0] if row else None


# ─────────────────────────────────────────────────────────────
# 批量写入（小说）
# ON CONFLICT (platform, lang, title) DO UPDATE 实现 rescrape upsert，
# id / created_at 保持首次写入的值，对应 CH 的 ReplacingMergeTree 语义
# ─────────────────────────────────────────────────────────────
_INSERT_NOVELS_SQL = """
INSERT INTO novels
    (title, summary, tags, views, likes, original_url, platform, lang, s_adapt, top_keywords, rank_type)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (platform, lang, title) DO UPDATE SET
    summary      = EXCLUDED.summary,
    tags         = EXCLUDED.tags,
    views        = EXCLUDED.views,
    likes        = EXCLUDED.likes,
    original_url = EXCLUDED.original_url,
    s_adapt      = EXCLUDED.s_adapt,
    top_keywords = EXCLUDED.top_keywords,
    rank_type    = EXCLUDED.rank_type
"""


def batch_insert(rows: list[dict]) -> int:
    if not rows:
        return 0
    data = [
        (
            r.get("title", ""),
            r.get("summary", ""),
            r.get("tags") or [],
            r.get("views"),
            r.get("likes"),
            r.get("original_url", ""),
            r.get("platform", ""),
            r.get("lang", ""),
            float(r.get("s_adapt", 50.0)),
            json.dumps(r.get("top_keywords") or {}, ensure_ascii=False),
            r.get("rank_type", ""),
        )
        for r in rows
    ]
    con = get_client()
    with _lock:
        con.executemany(_INSERT_NOVELS_SQL, data)
    return len(data)


async def batch_insert_async(rows: list[dict]) -> int:
    return await asyncio.to_thread(batch_insert, rows)


# ─────────────────────────────────────────────────────────────
# 批量写入（短剧）
# ─────────────────────────────────────────────────────────────
_INSERT_DRAMAS_SQL = """
INSERT INTO dramas
    (title, summary, cover_url, tags, episodes, rank_in_platform, heat_score,
     platform, lang, rank_type, crawl_date, source_url)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (platform, title) DO UPDATE SET
    summary          = EXCLUDED.summary,
    cover_url        = EXCLUDED.cover_url,
    tags             = EXCLUDED.tags,
    episodes         = EXCLUDED.episodes,
    rank_in_platform = EXCLUDED.rank_in_platform,
    heat_score       = EXCLUDED.heat_score,
    lang             = EXCLUDED.lang,
    rank_type        = EXCLUDED.rank_type,
    crawl_date       = EXCLUDED.crawl_date,
    source_url       = EXCLUDED.source_url
"""


def batch_insert_dramas(rows: list[dict]) -> int:
    if not rows:
        return 0
    data = [
        (
            r.get("title", ""),
            r.get("summary", ""),
            r.get("cover_url", ""),
            r.get("tags") or [],
            r.get("episodes"),
            int(r.get("rank_in_platform") or 0),
            float(r.get("heat_score") or 0),
            r.get("platform", ""),
            r.get("lang", "en"),
            r.get("rank_type", ""),
            r.get("crawl_date") or date.today(),
            r.get("source_url", ""),
        )
        for r in rows
    ]
    con = get_client()
    with _lock:
        con.executemany(_INSERT_DRAMAS_SQL, data)
    return len(data)


async def batch_insert_dramas_async(rows: list[dict]) -> int:
    return await asyncio.to_thread(batch_insert_dramas, rows)


# ─────────────────────────────────────────────────────────────
# 兼容 ClickHouse 时代的 OPTIMIZE FINAL 入口：DuckDB 不需要后台合并，
# ON CONFLICT 已在写入路径完成去重，保留同名 stub 让 services 层不用改
# ─────────────────────────────────────────────────────────────
def optimize_dramas_final() -> None:
    return None


async def optimize_dramas_final_async() -> None:
    return None
