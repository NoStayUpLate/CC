"""
小说列表 & 元数据 API。

GHI = (S_popular × 0.3) + (S_engage × 0.3) + (S_adapt × 0.4)
  S_popular  = log10(views + 1) × 10  （上限 100，SQL 计算）
  S_engage   = (likes / views) × 100 × 语种系数  （上限 100，SQL 计算）
  S_adapt    = 爬虫端预计算并存入 novels.s_adapt 列（SQL 直接读取）
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database import get_client
from models import NovelsResponse, NovelOut

router = APIRouter(prefix="/api/novels", tags=["novels"])

# ─────────────────────────────────────────────────────────────
# 黄金三秒关键词（positionCaseInsensitive 逐一检测 summary）
# ─────────────────────────────────────────────────────────────
_HOOK_KEYWORDS = [
    "reborn", "rebirth", "revenge", "betrayed", "transmigrat",
    "identity", "reincarnation", "regression", "villainess",
    "abandoned", "second chance",
]


def _build_hook_expr() -> str:
    """生成 ClickHouse SQL 黄金三秒布尔表达式。"""
    clauses = [
        f"positionCaseInsensitive(summary, '{kw}') > 0"
        for kw in _HOOK_KEYWORDS
    ]
    return "(" + " OR ".join(clauses) + ")"


# ─────────────────────────────────────────────────────────────
# GHI 主查询模板（两层嵌套：raw -> ranked）
# S_adapt 由爬虫端预计算写入 novels.s_adapt 列，SQL 直接读取
# ─────────────────────────────────────────────────────────────
_GHI_SQL_TEMPLATE = """
SELECT
    id, title, summary, tags, views, likes, original_url,
    platform, lang, rank_type, created_at,
    round(s_popular, 2)  AS s_popular,
    round(s_engage,  2)  AS s_engage,
    round(s_adapt,   2)  AS s_adapt,
    round((s_popular * 0.3) + (s_engage * 0.3) + (s_adapt * 0.4), 2) AS ghi,
    {hook_expr}          AS has_hook
FROM (
    SELECT
        id, title, summary, tags, views, likes, original_url,
        platform, lang, rank_type, created_at, s_adapt,
        least(log10(toFloat64(ifNull(views, 0)) + 1.0) * 10.0, 100.0) AS s_popular,
        if(
            ifNull(views, 0) = 0, 0.0,
            least(
                (toFloat64(ifNull(likes, 0)) / toFloat64(ifNull(views, 0))) * 100.0
                * multiIf(lang = 'ko', 1.2, lang = 'en', 0.8, 1.0),
                100.0
            )
        ) AS s_engage
    FROM novels
    {where_clause}
) AS raw
ORDER BY ghi DESC
LIMIT {{limit}} OFFSET {{offset}}
"""

# 预先填入固定部分（黄金三秒表达式），剩余占位符按需填充
_GHI_SQL_BASE = _GHI_SQL_TEMPLATE.format(
    hook_expr=_build_hook_expr(),
    where_clause="{where_clause}",
)

_COUNT_SQL_TEMPLATE = "SELECT count() FROM novels {where_clause}"


# ─────────────────────────────────────────────────────────────
# 工具函数：安全构建 WHERE 子句（参数化防注入）
# ─────────────────────────────────────────────────────────────
def _build_where(
    platform: Optional[str],
    lang: Optional[str],
    tags: Optional[str],
    title: Optional[str],
    date_range: Optional[str] = None,
    rank_type: Optional[str] = None,
) -> tuple[str, dict]:
    """
    返回 (where_clause_str, params_dict)。
    ClickHouse 参数化占位符语法：{name:Type}
    """
    conditions: list[str] = []
    params: dict = {}

    if platform:
        conditions.append("platform = {platform:String}")
        params["platform"] = platform

    if lang:
        conditions.append("lang = {lang:String}")
        params["lang"] = lang

    if tags:
        # 多标签逗号分隔，转小写后用 hasAny 匹配
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        if tag_list:
            conditions.append(
                "hasAny(arrayMap(x -> lower(x), tags), {tag_list:Array(String)})"
            )
            params["tag_list"] = tag_list

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

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


def _row_to_novel(row: dict) -> NovelOut:
    """ClickHouse 行字典 -> NovelOut Pydantic 对象。"""
    kw = row.get("top_keywords")
    return NovelOut(
        id=str(row.get("id", "")),
        title=row.get("title") or "",
        summary=row.get("summary") or None,
        tags=row.get("tags") or [],
        views=int(row.get("views") or 0),
        likes=int(row.get("likes") or 0),
        original_url=row.get("original_url") or "",
        platform=row.get("platform") or "",
        lang=row.get("lang") or "",
        rank_type=row.get("rank_type") or "",
        created_at=row.get("created_at"),
        s_popular=float(row.get("s_popular") or 0),
        s_engage=float(row.get("s_engage") or 0),
        s_adapt=float(row.get("s_adapt") or 0),
        ghi=float(row.get("ghi") or 0),
        has_hook=bool(row.get("has_hook") or False),
        top_keywords=kw if kw else None,
    )


# ─────────────────────────────────────────────────────────────
# 路由
# ─────────────────────────────────────────────────────────────
@router.get("", response_model=NovelsResponse)
def list_novels(
    platform: Optional[str] = Query(None, description="平台名称，如 wattpad"),
    lang: Optional[str] = Query(None, description="语种代码，如 en / ja / ko"),
    tags: Optional[str] = Query(None, description="逗号分隔标签，如 werewolf,romance"),
    title: Optional[str] = Query(None, description="书名关键词（模糊搜索）"),
    date_range: Optional[str] = Query(None, description="时间范围: today / week / month"),
    rank_type: Optional[str] = Query(None, description="榜单类型: daily / weekly / monthly"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询小说列表，GHI 算法在 ClickHouse 内完成计算。"""
    where_clause, params = _build_where(platform, lang, tags, title, date_range, rank_type)

    offset = (page - 1) * page_size

    # 构建完整 SQL（用 replace 而非 format，避免 SQL 大括号被误解析）
    final_sql = (
        _GHI_SQL_BASE
        .replace("{where_clause}", where_clause)
        .replace("{limit}", str(page_size))
        .replace("{offset}", str(offset))
    )

    count_sql = _COUNT_SQL_TEMPLATE.replace("{where_clause}", where_clause)

    client = get_client()
    try:
        result = client.query(final_sql, parameters=params)
        count_result = client.query(count_sql, parameters=params)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse 查询失败: {exc}")

    total = int(count_result.first_row[0]) if count_result.first_row else 0
    rows = result.named_results()
    items = [_row_to_novel(r) for r in rows]

    return NovelsResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/meta/platforms")
def get_platforms():
    """获取库中所有平台名称。"""
    client = get_client()
    result = client.query("SELECT DISTINCT platform FROM novels ORDER BY platform")
    return {"platforms": [r[0] for r in result.result_rows]}


@router.get("/meta/langs")
def get_langs():
    """获取库中所有语种代码。"""
    client = get_client()
    result = client.query("SELECT DISTINCT lang FROM novels ORDER BY lang")
    return {"langs": [r[0] for r in result.result_rows]}


@router.get("/meta/tags")
def get_tags():
    """获取库中高频标签 Top 50（用于筛选器下拉联想）。"""
    client = get_client()
    result = client.query("""
        SELECT tag, count() AS cnt
        FROM (
            SELECT arrayJoin(tags) AS tag FROM novels
        )
        GROUP BY tag
        ORDER BY cnt DESC
        LIMIT 50
    """)
    return {"tags": [r[0] for r in result.result_rows]}


# ─────────────────────────────────────────────────────────────
# 单本详情（含 top_keywords 关键词云）
# 注：此路由必须在 /meta/* 路由之后注册，避免参数路由覆盖具体路径
# ─────────────────────────────────────────────────────────────
_DETAIL_SQL = """
SELECT
    id, title, summary, tags, views, likes, original_url,
    platform, lang, rank_type, created_at, top_keywords,
    round(s_popular, 2)  AS s_popular,
    round(s_engage,  2)  AS s_engage,
    round(s_adapt,   2)  AS s_adapt,
    round((s_popular * 0.3) + (s_engage * 0.3) + (s_adapt * 0.4), 2) AS ghi,
    {hook_expr}          AS has_hook
FROM (
    SELECT
        id, title, summary, tags, views, likes, original_url,
        platform, lang, rank_type, created_at, s_adapt, top_keywords,
        least(log10(toFloat64(ifNull(views, 0)) + 1.0) * 10.0, 100.0) AS s_popular,
        if(
            ifNull(views, 0) = 0, 0.0,
            least(
                (toFloat64(ifNull(likes, 0)) / toFloat64(ifNull(views, 0))) * 100.0
                * multiIf(lang = 'ko', 1.2, lang = 'en', 0.8, 1.0),
                100.0
            )
        ) AS s_engage
    FROM novels
    WHERE toString(id) = {{novel_id:String}}
) AS raw
LIMIT 1
""".format(hook_expr=_build_hook_expr())


@router.get("/{novel_id}", response_model=NovelOut)
def get_novel(novel_id: str):
    """获取单本小说详情，包含 top_keywords 关键词云数据。"""
    client = get_client()
    try:
        result = client.query(
            _DETAIL_SQL,
            parameters={"novel_id": novel_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse 查询失败: {exc}")

    rows = list(result.named_results())
    if not rows:
        raise HTTPException(status_code=404, detail="小说不存在")

    return _row_to_novel(rows[0])
