"""
ClickHouse 连接管理模块。

FastAPI sync 端点在线程池中运行；clickhouse-connect 的 Client 不能在
并发请求间共享，因此每次获取独立客户端，后台异步任务通过 asyncio.to_thread()
调用同步方法。
"""
import asyncio
import os
from datetime import date
from time import time
import clickhouse_connect
from clickhouse_connect.driver.client import Client

from config import settings

# ClickHouse 主机加入 NO_PROXY，防止 HTTP_PROXY 拦截内网/本机请求
# 实际 host 由 settings.clickhouse_host 决定（来自 backend/.env），不在代码里硬编码
_no_proxy = os.environ.get("NO_PROXY", "")
_ch_hosts = ",".join(filter(None, [settings.clickhouse_host, "localhost", "127.0.0.1"]))
os.environ["NO_PROXY"] = f"{_ch_hosts},{_no_proxy}".strip(",")

# ─────────────────────────────────────────────────────────────
# DDL：完整建表语句（含表注释与字段注释）
# ─────────────────────────────────────────────────────────────
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS novels
(
    id           UUID                DEFAULT generateUUIDv4()
                     COMMENT '小说唯一标识符，由 ClickHouse 自动生成的 UUID，全局不重复',

    title        String
                     COMMENT '小说标题，保留原始语言，不做翻译或截断',

    summary      String
                     COMMENT '小说简介 / 故事梗概，来源于平台展示文案，保留原始语言',

    tags         Array(String)
                     COMMENT '题材标签数组，统一转小写，如 werewolf、romance、litrpg 等',

    views        Nullable(UInt64)
                     COMMENT '累计阅读量；平台不公开或抓取失败时为 NULL，禁止以 0 填充',

    likes        Nullable(UInt64)
                     COMMENT '累计点赞 / 互动量（Wattpad=voteCount，Royal Road=Followers）；不可获取时为 NULL',

    original_url String
                     COMMENT '小说在来源平台的原始页面链接，用于跳转和去重校验',

    platform     LowCardinality(String)
                     COMMENT '来源平台标识符，如 wattpad / royal_road / syosetu，低基数用 LowCardinality 节省存储',

    lang         LowCardinality(String)
                     COMMENT '内容语言代码（ISO 639-1），如 en / ja / ko / fr，低基数用 LowCardinality 节省存储',

    s_adapt      Float32             DEFAULT 50.0
                     COMMENT 'AI 短剧改编适配分（0-100），爬虫端按标签预计算后写入：S 级标签（狼人/重生/复仇/恶役千金）90+ 分，A 级标签 70-89 分，无标签默认 50 分',

    top_keywords Map(String, UInt32) DEFAULT map()
                     COMMENT '前三章高频关键词词频表，格式 {词: 出现次数}，由 Python 端分词后写入；空 Map 表示内容受限或章节尚未抓取',

    rank_type    LowCardinality(String) DEFAULT ''
                     COMMENT '榜单类型：daily=日榜 / weekly=周榜 / monthly=月榜 / 空=非榜单来源',

    created_at   DateTime            DEFAULT now()
                     COMMENT '记录首次写入时间，用于按月分区（PARTITION BY toYYYYMM）'
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (platform, lang, title)
SETTINGS index_granularity = 8192
COMMENT '海外小说元数据主表，存储爬虫抓取的原始信息及 GHI 算法所需的预计算字段，支持 AI 短剧改编潜力分析'
"""

_CREATE_DRAMAS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dramas
(
    id             UUID                   DEFAULT generateUUIDv4()
                       COMMENT '短剧唯一标识符，由 ClickHouse 自动生成 UUID',

    title          String
                       COMMENT '短剧标题（原文）',

    summary        String
                       COMMENT '短剧简介（抓取不到时为空字符串）',

    cover_url      String                 DEFAULT ''
                       COMMENT '短剧封面图 URL',

    tags           Array(String)
                       COMMENT '短剧标签/题材关键词',

    episodes       Nullable(UInt32)
                       COMMENT '总集数；无法解析时为 NULL',

    rank_in_platform UInt16               DEFAULT 0
                       COMMENT '平台内榜单名次（1 开始）',

    heat_score     Float32                DEFAULT 0
                       COMMENT '热度分，按名次换算（名次越靠前越高）',

    platform       LowCardinality(String)
                       COMMENT '短剧平台标识，如 netshort/shortmax/reelshort/dramabox/dramareels/dramawave',

    lang           LowCardinality(String) DEFAULT 'en'
                       COMMENT '内容语言代码（ISO 639-1）',

    rank_type      LowCardinality(String) DEFAULT ''
                       COMMENT '榜单类型：轮播推荐 / 推荐栏位 / 最近上新',

    crawl_date     Date                   DEFAULT today()
                       COMMENT '抓取日期（按自然日）',

    source_url     String
                       COMMENT '来源页面 URL（榜单页或详情页）',

    created_at     DateTime               DEFAULT now()
                       COMMENT '记录写入时间'
)
ENGINE = ReplacingMergeTree(created_at)
PARTITION BY toYYYYMM(created_at)
ORDER BY (platform, title)
SETTINGS index_granularity = 8192
COMMENT '海外短剧监测数据表，独立于 novels 表存储'
"""

# 存量表迁移，幂等执行（字段增删 + 注释回填）
_MIGRATE_SQL = [
    # ── 历史字段类型修正 ──────────────────────────────────────
    "ALTER TABLE novels MODIFY COLUMN views Nullable(UInt64)",
    "ALTER TABLE novels MODIFY COLUMN likes Nullable(UInt64)",
    # ── 新增字段（幂等）─────────────────────────────────────
    "ALTER TABLE novels ADD COLUMN IF NOT EXISTS s_adapt Float32 DEFAULT 50.0",
    "ALTER TABLE novels ADD COLUMN IF NOT EXISTS top_keywords Map(String, UInt32) DEFAULT map()",
    "ALTER TABLE novels ADD COLUMN IF NOT EXISTS rank_type LowCardinality(String) DEFAULT ''",
    # ── 表级注释 ────────────────────────────────────────────
    "ALTER TABLE novels MODIFY COMMENT '海外小说元数据主表，存储爬虫抓取的原始信息及 GHI 算法所需的预计算字段，支持 AI 短剧改编潜力分析'",
    # ── 字段注释回填（对存量表生效）────────────────────────
    "ALTER TABLE novels COMMENT COLUMN id           '小说唯一标识符，由 ClickHouse 自动生成的 UUID，全局不重复'",
    "ALTER TABLE novels COMMENT COLUMN title        '小说标题，保留原始语言，不做翻译或截断'",
    "ALTER TABLE novels COMMENT COLUMN summary      '小说简介 / 故事梗概，来源于平台展示文案，保留原始语言'",
    "ALTER TABLE novels COMMENT COLUMN tags         '题材标签数组，统一转小写，如 werewolf、romance、litrpg 等'",
    "ALTER TABLE novels COMMENT COLUMN views        '累计阅读量；平台不公开或抓取失败时为 NULL，禁止以 0 填充'",
    "ALTER TABLE novels COMMENT COLUMN likes        '累计点赞 / 互动量（Wattpad=voteCount，Royal Road=Followers）；不可获取时为 NULL'",
    "ALTER TABLE novels COMMENT COLUMN original_url '小说在来源平台的原始页面链接，用于跳转和去重校验'",
    "ALTER TABLE novels COMMENT COLUMN platform     '来源平台标识符，如 wattpad / royal_road / syosetu，低基数用 LowCardinality 节省存储'",
    "ALTER TABLE novels COMMENT COLUMN lang         '内容语言代码（ISO 639-1），如 en / ja / ko / fr，低基数用 LowCardinality 节省存储'",
    "ALTER TABLE novels COMMENT COLUMN s_adapt      'AI 短剧改编适配分（0-100），爬虫端按标签预计算后写入：S 级标签（狼人/重生/复仇/恶役千金）90+ 分，A 级标签 70-89 分，无标签默认 50 分'",
    "ALTER TABLE novels COMMENT COLUMN top_keywords '前三章高频关键词词频表，格式 {词: 出现次数}，由 Python 端分词后写入；空 Map 表示内容受限或章节尚未抓取'",
    "ALTER TABLE novels COMMENT COLUMN created_at   '记录首次写入时间，用于按月分区（PARTITION BY toYYYYMM）'",
]

_MIGRATE_DRAMAS_SQL = [
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS summary String DEFAULT ''",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS cover_url String DEFAULT ''",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS tags Array(String) DEFAULT []",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS episodes Nullable(UInt32)",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS rank_in_platform UInt16 DEFAULT 0",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS heat_score Float32 DEFAULT 0",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS lang LowCardinality(String) DEFAULT 'en'",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS rank_type LowCardinality(String) DEFAULT ''",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS crawl_date Date DEFAULT today()",
    "ALTER TABLE dramas ADD COLUMN IF NOT EXISTS source_url String DEFAULT ''",
    "ALTER TABLE dramas MODIFY COMMENT '海外短剧监测数据表，独立于 novels 表存储'",
]


def get_client() -> Client:
    """返回独立 ClickHouse 同步客户端，避免并发请求共享同一会话。"""
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
        username=settings.clickhouse_username,
        password=settings.clickhouse_password,
        compress=True,
        autogenerate_session_id=False,
    )


def init_db() -> None:
    """服务启动时执行建表 DDL 及迁移，幂等操作。"""
    client = get_client()
    client.command(_CREATE_TABLE_SQL)
    client.command(_CREATE_DRAMAS_TABLE_SQL)
    for sql in _MIGRATE_SQL:
        try:
            client.command(sql)
        except Exception:
            pass  # 列已是 Nullable 类型时 ClickHouse 静默跳过
    for sql in _MIGRATE_DRAMAS_SQL:
        try:
            client.command(sql)
        except Exception:
            pass
    _ensure_dramas_sort_key(client)


def _ensure_dramas_sort_key(client: Client) -> None:
    """
    确保 dramas 的去重键是 (platform, title)。
    老表无法直接 MODIFY ORDER BY 时，采用重建表并原子改名迁移。
    """
    try:
        ddl = client.command("SHOW CREATE TABLE dramas")
    except Exception:
        return
    normalized = ddl.replace("`", "").replace("\n", " ")
    if "ORDER BY (platform, title)" in normalized:
        return

    tmp_table = "dramas_rekey_tmp"
    backup_table = f"dramas_backup_{int(time())}"
    create_tmp_sql = """
    CREATE TABLE IF NOT EXISTS dramas_rekey_tmp
    (
        id             UUID                   DEFAULT generateUUIDv4(),
        title          String,
        summary        String,
        cover_url      String                 DEFAULT '',
        tags           Array(String),
        episodes       Nullable(UInt32),
        rank_in_platform UInt16               DEFAULT 0,
        heat_score     Float32                DEFAULT 0,
        platform       LowCardinality(String),
        lang           LowCardinality(String) DEFAULT 'en',
        rank_type      LowCardinality(String) DEFAULT '',
        crawl_date     Date                   DEFAULT today(),
        source_url     String,
        created_at     DateTime               DEFAULT now()
    )
    ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY toYYYYMM(created_at)
    ORDER BY (platform, title)
    SETTINGS index_granularity = 8192
    """
    client.command(f"DROP TABLE IF EXISTS {tmp_table}")
    client.command(create_tmp_sql)
    client.command(
        f"""
        INSERT INTO {tmp_table}
        (
            id, title, summary, cover_url, tags, episodes, rank_in_platform, heat_score,
            platform, lang, rank_type, crawl_date, source_url, created_at
        )
        SELECT
            id, title, summary, cover_url, tags, episodes, rank_in_platform, heat_score,
            platform, lang, rank_type, coalesce(crawl_date, toDate(created_at)), source_url, created_at
        FROM dramas
        """
    )
    client.command(f"RENAME TABLE dramas TO {backup_table}, {tmp_table} TO dramas")


async def init_db_async() -> None:
    """在 asyncio 上下文中执行 DDL（用于 FastAPI lifespan）。"""
    await asyncio.to_thread(init_db)


# ─────────────────────────────────────────────────────────────
# 批量写入辅助
# ─────────────────────────────────────────────────────────────
_INSERT_COLUMNS = [
    "title", "summary", "tags", "views",
    "likes", "original_url", "platform", "lang", "s_adapt", "top_keywords", "rank_type",
]

_DRAMA_INSERT_COLUMNS = [
    "title", "summary", "cover_url", "tags", "episodes", "rank_in_platform",
    "heat_score", "platform", "lang", "rank_type", "crawl_date", "source_url",
]


def batch_insert(rows: list[dict]) -> int:
    """
    同步批量插入。rows 为 dict 列表，key 与 _INSERT_COLUMNS 对应。
    在 asyncio.to_thread 中调用时创建独立 client，避免单例跨线程冲突。
    返回实际插入行数。
    """
    if not rows:
        return 0
    data = [
        [
            r.get("title", ""),
            r.get("summary", ""),
            r.get("tags", []),
            r.get("views"),                     # None 表示无法抓取，保持 NULL
            r.get("likes"),                     # None 表示无法抓取，保持 NULL
            r.get("original_url", ""),
            r.get("platform", ""),
            r.get("lang", ""),
            float(r.get("s_adapt", 50.0)),
            r.get("top_keywords") or {},        # None → 空 Map（ClickHouse 不支持 Nullable(Map)）
            r.get("rank_type", ""),
        ]
        for r in rows
    ]
    client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
        username=settings.clickhouse_username,
        password=settings.clickhouse_password,
        compress=True,
        autogenerate_session_id=False,
    )
    client.insert("novels", data, column_names=_INSERT_COLUMNS)
    return len(data)


async def batch_insert_async(rows: list[dict]) -> int:
    """异步包装，供后台爬虫任务调用。"""
    return await asyncio.to_thread(batch_insert, rows)


def batch_insert_dramas(rows: list[dict]) -> int:
    """同步批量写入短剧数据。"""
    if not rows:
        return 0

    data = [
        [
            r.get("title", ""),
            r.get("summary", ""),
            r.get("cover_url", ""),
            r.get("tags", []),
            r.get("episodes"),
            int(r.get("rank_in_platform") or 0),
            float(r.get("heat_score") or 0),
            r.get("platform", ""),
            r.get("lang", "en"),
            r.get("rank_type", ""),
            r.get("crawl_date") or date.today(),
            r.get("source_url", ""),
        ]
        for r in rows
    ]

    client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
        username=settings.clickhouse_username,
        password=settings.clickhouse_password,
        compress=True,
        autogenerate_session_id=False,
    )
    client.insert("dramas", data, column_names=_DRAMA_INSERT_COLUMNS)
    return len(data)


async def batch_insert_dramas_async(rows: list[dict]) -> int:
    """异步包装，供短剧后台任务调用。"""
    return await asyncio.to_thread(batch_insert_dramas, rows)


def optimize_dramas_final() -> None:
    """执行短剧表 FINAL 合并，触发 ReplacingMergeTree 去重。"""
    client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
        username=settings.clickhouse_username,
        password=settings.clickhouse_password,
        compress=True,
        autogenerate_session_id=False,
    )
    client.command("OPTIMIZE TABLE dramas FINAL")


async def optimize_dramas_final_async() -> None:
    """异步包装：短剧抓取后执行 CH 合并去重。"""
    await asyncio.to_thread(optimize_dramas_final)
