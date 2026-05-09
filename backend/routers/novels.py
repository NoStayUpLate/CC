"""
小说列表 & 元数据 API。

GHI = (S_popular × 0.3) + (S_engage × 0.3) + (S_adapt × 0.4)
  S_popular  = log10(views + 1) × 10  （上限 100，SQL 计算）
  S_engage   = (likes / views) × 100 × 语种系数  （上限 100，SQL 计算）
  S_adapt    = 爬虫端预计算并存入 novels.s_adapt 列（SQL 直接读取）

实现：DuckDB（嵌入式）。SQL 内算分项 → 外层加权排序，与 CH 时代结构一致，
仅替换 CH 方言：if/multiIf → CASE WHEN，positionCaseInsensitive → lower(...) LIKE，
toFloat64 → ::DOUBLE，ifNull → coalesce，arrayJoin → unnest。
"""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database import query_dicts, query_scalar
from models import NovelsResponse, NovelOut

router = APIRouter(prefix="/api/novels", tags=["novels"])

# ─────────────────────────────────────────────────────────────
# 黄金三秒关键词（lower(summary) LIKE '%kw%' 逐一检测）
# ─────────────────────────────────────────────────────────────
_HOOK_KEYWORDS = [
    "reborn", "rebirth", "revenge", "betrayed", "transmigrat",
    "identity", "reincarnation", "regression", "villainess",
    "abandoned", "second chance",
]


def _build_hook_expr() -> str:
    """生成 DuckDB 的黄金三秒布尔表达式（关键词都是英文小写常量，无注入风险）。"""
    clauses = [
        f"lower(summary) LIKE '%{kw}%'"
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
        least(log10(coalesce(views, 0)::DOUBLE + 1.0) * 10.0, 100.0) AS s_popular,
        CASE
            WHEN coalesce(views, 0) = 0 THEN 0.0
            ELSE least(
                (coalesce(likes, 0)::DOUBLE / coalesce(views, 0)::DOUBLE) * 100.0
                * CASE lang WHEN 'ko' THEN 1.2 WHEN 'en' THEN 0.8 ELSE 1.0 END,
                100.0
            )
        END AS s_engage
    FROM novels
    {where_clause}
) AS raw
ORDER BY ghi DESC
LIMIT {limit} OFFSET {offset}
"""

_GHI_SQL_BASE = _GHI_SQL_TEMPLATE.replace("{hook_expr}", _build_hook_expr())

_COUNT_SQL_TEMPLATE = "SELECT count(*) FROM novels {where_clause}"


# ─────────────────────────────────────────────────────────────
# 工具函数：安全构建 WHERE 子句（参数化防注入，用 DuckDB 命名占位符 $name）
# ─────────────────────────────────────────────────────────────
def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


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
    multi-select 用 = ANY($x)；DuckDB 命名占位符语法：$name。
    """
    conditions: list[str] = []
    params: dict = {}

    platforms = _split_csv(platform)
    if platforms:
        conditions.append("platform = ANY($platforms)")
        params["platforms"] = platforms

    langs = _split_csv(lang)
    if langs:
        conditions.append("lang = ANY($langs)")
        params["langs"] = langs

    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        if tag_list:
            # list_has_any(arr_a, arr_b) → bool；先 lower 化原 tags 列再求交
            conditions.append(
                "list_has_any(list_transform(tags, x -> lower(x)), $tag_list)"
            )
            params["tag_list"] = tag_list

    if title:
        conditions.append("lower(title) LIKE $title_pat")
        params["title_pat"] = f"%{title.lower()}%"

    if date_range == "today":
        conditions.append("created_at::DATE = current_date")
    elif date_range == "week":
        conditions.append("created_at >= date_trunc('week', current_date)")
    elif date_range == "month":
        conditions.append("created_at >= date_trunc('month', current_date)")

    rank_types = _split_csv(rank_type)
    if rank_types:
        conditions.append("rank_type = ANY($rank_types)")
        params["rank_types"] = rank_types

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


def _row_to_novel(row: dict) -> NovelOut:
    """DuckDB 行字典 -> NovelOut Pydantic。top_keywords 落盘是 JSON 字符串，反序列化回 dict。"""
    raw_kw = row.get("top_keywords")
    if isinstance(raw_kw, str) and raw_kw.strip():
        try:
            kw = json.loads(raw_kw)
        except (ValueError, TypeError):
            kw = None
    else:
        kw = raw_kw if isinstance(raw_kw, dict) else None

    return NovelOut(
        id=str(row.get("id", "")),
        title=row.get("title") or "",
        summary=row.get("summary") or None,
        tags=row.get("tags") or [],
        views=int(row["views"]) if row.get("views") is not None else 0,
        likes=int(row["likes"]) if row.get("likes") is not None else 0,
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
    platform: Optional[str] = Query(None, description="平台名称，多选用逗号分隔"),
    lang: Optional[str] = Query(None, description="语种代码，多选用逗号分隔"),
    tags: Optional[str] = Query(None, description="逗号分隔标签，如 werewolf,romance"),
    title: Optional[str] = Query(None, description="书名关键词（模糊搜索）"),
    date_range: Optional[str] = Query(None, description="时间范围: today / week / month"),
    rank_type: Optional[str] = Query(None, description="榜单类型，多选用逗号分隔，如 daily,weekly"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询小说列表，GHI 算法在 DuckDB 内完成计算。"""
    where_clause, params = _build_where(platform, lang, tags, title, date_range, rank_type)

    offset = (page - 1) * page_size

    final_sql = (
        _GHI_SQL_BASE
        .replace("{where_clause}", where_clause)
        .replace("{limit}", str(page_size))
        .replace("{offset}", str(offset))
    )
    count_sql = _COUNT_SQL_TEMPLATE.replace("{where_clause}", where_clause)

    try:
        rows = query_dicts(final_sql, params)
        total = int(query_scalar(count_sql, params) or 0)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DuckDB 查询失败: {exc}")

    items = [_row_to_novel(r) for r in rows]
    return NovelsResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/meta/platforms")
def get_platforms():
    rows = query_dicts("SELECT DISTINCT platform FROM novels ORDER BY platform")
    return {"platforms": [r["platform"] for r in rows]}


@router.get("/meta/langs")
def get_langs():
    rows = query_dicts("SELECT DISTINCT lang FROM novels ORDER BY lang")
    return {"langs": [r["lang"] for r in rows]}


@router.get("/meta/tags")
def get_tags():
    """库中高频标签 Top 50（用于筛选器联想）。DuckDB 用 unnest 展开 list 列。"""
    rows = query_dicts("""
        SELECT tag, count(*) AS cnt
        FROM (SELECT unnest(tags) AS tag FROM novels)
        GROUP BY tag
        ORDER BY cnt DESC
        LIMIT 50
    """)
    return {"tags": [r["tag"] for r in rows]}


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
        least(log10(coalesce(views, 0)::DOUBLE + 1.0) * 10.0, 100.0) AS s_popular,
        CASE
            WHEN coalesce(views, 0) = 0 THEN 0.0
            ELSE least(
                (coalesce(likes, 0)::DOUBLE / coalesce(views, 0)::DOUBLE) * 100.0
                * CASE lang WHEN 'ko' THEN 1.2 WHEN 'en' THEN 0.8 ELSE 1.0 END,
                100.0
            )
        END AS s_engage
    FROM novels
    WHERE CAST(id AS VARCHAR) = $novel_id
) AS raw
LIMIT 1
""".replace("{hook_expr}", _build_hook_expr())


@router.get("/{novel_id}", response_model=NovelOut)
def get_novel(novel_id: str):
    """获取单本小说详情，包含 top_keywords 关键词云数据。"""
    try:
        rows = query_dicts(_DETAIL_SQL, {"novel_id": novel_id})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DuckDB 查询失败: {exc}")

    if not rows:
        raise HTTPException(status_code=404, detail="小说不存在")

    return _row_to_novel(rows[0])
