"""
一次性迁移：本地 ClickHouse → 本地 DuckDB。

用途：把 CH 时代积累的 novels / dramas 数据原封不动塞进新的 DuckDB 文件。
保留原始 id (UUID) 和 created_at（DHI 的 S_recency 看 crawl_date，s_recency 不依赖 created_at；
但 overview 的 last_crawled / recent_7d 看 created_at，保留住才能让"最后抓取时间"正确）。

读取连接信息：
  - ClickHouse：从 backend/.env 读 CLICKHOUSE_HOST/PORT/DATABASE/USERNAME/PASSWORD
  - DuckDB：默认 backend/dashboard.duckdb；可用环境变量 DUCKDB_PATH 覆盖

运行（项目根目录）：
  pip install clickhouse-connect    # 一次性，requirements.txt 已经不含
  python scripts/migrate_ch_to_duckdb.py
  python scripts/migrate_ch_to_duckdb.py --reset   # 清空 DuckDB 后再迁

幂等性：
  - 默认走 ON CONFLICT DO UPDATE，DuckDB 里有同 (platform, lang, title) 的行会被 CH 的覆盖
  - --reset 模式会先 DELETE FROM novels / DELETE FROM dramas
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# 让 backend 里的 database.py / config.py 也能加载本地 .env
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "backend" / ".env")
except ImportError:
    pass  # python-dotenv 不在标准库，但 pydantic-settings 会自己加载


def main() -> int:
    ap = argparse.ArgumentParser(description="ClickHouse → DuckDB 一次性迁移")
    ap.add_argument("--reset", action="store_true",
                    help="迁移前先清空 DuckDB 的 novels / dramas（默认是增量上 upsert）")
    ap.add_argument("--ch-host", default=os.environ.get("CLICKHOUSE_HOST", ""))
    ap.add_argument("--ch-port", type=int, default=int(os.environ.get("CLICKHOUSE_PORT", 8123)))
    ap.add_argument("--ch-db",   default=os.environ.get("CLICKHOUSE_DATABASE", ""))
    ap.add_argument("--ch-user", default=os.environ.get("CLICKHOUSE_USERNAME", "default"))
    ap.add_argument("--ch-pass", default=os.environ.get("CLICKHOUSE_PASSWORD", ""))
    args = ap.parse_args()

    # ── 0. 依赖与凭据校验 ────────────────────────────────────
    try:
        import clickhouse_connect  # noqa: F401
    except ImportError:
        print("缺少 clickhouse-connect。请：pip install clickhouse-connect", file=sys.stderr)
        return 1

    if not args.ch_host or not args.ch_db or not args.ch_pass:
        print("缺少 CLICKHOUSE_HOST / DATABASE / PASSWORD。请：", file=sys.stderr)
        print("  - 把这些值写进 backend/.env，或", file=sys.stderr)
        print("  - 直接传 --ch-host xxx --ch-db xxx --ch-pass xxx", file=sys.stderr)
        return 1

    import clickhouse_connect

    from database import get_client as duck_client
    from database import init_db

    # ── 1. 连 ClickHouse + DuckDB ─────────────────────────────
    print(f"[CH]   {args.ch_user}@{args.ch_host}:{args.ch_port}/{args.ch_db}")
    ch = clickhouse_connect.get_client(
        host=args.ch_host, port=args.ch_port, database=args.ch_db,
        username=args.ch_user, password=args.ch_pass,
        autogenerate_session_id=False,
    )
    init_db()  # 确保 DuckDB 建表
    duck = duck_client()
    # database.py 内部已经 resolve 了 DUCKDB_PATH（默认相对 CWD）；这里直接复用其结果
    from database import _DB_PATH as _DUCK_DB_PATH
    print(f"[Duck] {_DUCK_DB_PATH}")

    # ── 2. 可选 reset ────────────────────────────────────────
    if args.reset:
        duck.execute("DELETE FROM novels")
        duck.execute("DELETE FROM dramas")
        print("[reset] 已清空 DuckDB 的 novels / dramas")

    # ── 3. novels 迁移 ──────────────────────────────────────
    ch_count_novels = ch.query("SELECT count() FROM novels").first_row[0]
    print(f"\n[novels] CH 行数 = {ch_count_novels}")
    if ch_count_novels:
        # ORDER BY created_at ASC 让新行最后 INSERT，
        # 这样 ON CONFLICT DO UPDATE 会让最终留下的是最新版本（避免 ReplacingMergeTree 旧副本盖掉新副本）
        rows = ch.query(
            """
            SELECT
                toString(id) AS id,
                title, summary, tags, views, likes, original_url,
                platform, lang, s_adapt, top_keywords, rank_type, created_at
            FROM novels
            ORDER BY created_at ASC
            """
        ).named_results()

        batch = []
        for r in rows:
            kw = r.get("top_keywords") or {}
            # CH Map → Python dict（clickhouse-connect 自动）；统一存 JSON
            try:
                kw_json = json.dumps(dict(kw), ensure_ascii=False)
            except Exception:
                kw_json = "{}"
            batch.append((
                r["id"],
                r.get("title") or "",
                r.get("summary") or "",
                list(r.get("tags") or []),
                r.get("views"),
                r.get("likes"),
                r.get("original_url") or "",
                r.get("platform") or "",
                r.get("lang") or "en",
                float(r.get("s_adapt") or 50.0),
                kw_json,
                r.get("rank_type") or "",
                r.get("created_at"),
            ))

        duck.executemany(
            """
            INSERT INTO novels
                (id, title, summary, tags, views, likes, original_url,
                 platform, lang, s_adapt, top_keywords, rank_type, created_at)
            VALUES (CAST(? AS UUID), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (platform, lang, title) DO UPDATE SET
                summary      = EXCLUDED.summary,
                tags         = EXCLUDED.tags,
                views        = EXCLUDED.views,
                likes        = EXCLUDED.likes,
                original_url = EXCLUDED.original_url,
                s_adapt      = EXCLUDED.s_adapt,
                top_keywords = EXCLUDED.top_keywords,
                rank_type    = EXCLUDED.rank_type,
                created_at   = EXCLUDED.created_at
            """,
            batch,
        )
        duck_count_novels = duck.execute("SELECT count(*) FROM novels").fetchone()[0]
        print(f"[novels] DuckDB 行数 = {duck_count_novels}（写入/更新 {len(batch)} 行）")

    # ── 4. dramas 迁移 ──────────────────────────────────────
    ch_count_dramas = ch.query("SELECT count() FROM dramas").first_row[0]
    print(f"\n[dramas] CH 行数 = {ch_count_dramas}")
    if ch_count_dramas:
        rows = ch.query(
            """
            SELECT
                toString(id) AS id,
                title, summary, cover_url, tags, episodes, rank_in_platform,
                heat_score, platform, lang, rank_type, crawl_date, source_url, created_at
            FROM dramas
            ORDER BY created_at ASC
            """
        ).named_results()

        batch = []
        for r in rows:
            batch.append((
                r["id"],
                r.get("title") or "",
                r.get("summary") or "",
                r.get("cover_url") or "",
                list(r.get("tags") or []),
                r.get("episodes"),
                int(r.get("rank_in_platform") or 0),
                float(r.get("heat_score") or 0),
                r.get("platform") or "",
                r.get("lang") or "en",
                r.get("rank_type") or "",
                r.get("crawl_date"),
                r.get("source_url") or "",
                r.get("created_at"),
            ))

        duck.executemany(
            """
            INSERT INTO dramas
                (id, title, summary, cover_url, tags, episodes, rank_in_platform,
                 heat_score, platform, lang, rank_type, crawl_date, source_url, created_at)
            VALUES (CAST(? AS UUID), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                source_url       = EXCLUDED.source_url,
                created_at       = EXCLUDED.created_at
            """,
            batch,
        )
        duck_count_dramas = duck.execute("SELECT count(*) FROM dramas").fetchone()[0]
        print(f"[dramas] DuckDB 行数 = {duck_count_dramas}（写入/更新 {len(batch)} 行）")

    # ── 5. 抽样校验 ─────────────────────────────────────────
    print("\n抽样：DuckDB 里 novels 前 3 行（按 GHI 排序）")
    sample = duck.execute(
        """
        SELECT title, platform, lang, s_adapt, views, likes
        FROM novels
        ORDER BY coalesce(views, 0) DESC
        LIMIT 3
        """
    ).fetchall()
    for row in sample:
        print(f"   {row}")

    print("\n抽样：DuckDB 里 dramas 前 3 行（按 rank_in_platform 升序）")
    sample = duck.execute(
        """
        SELECT title, platform, rank_in_platform, crawl_date
        FROM dramas
        WHERE rank_in_platform > 0
        ORDER BY rank_in_platform
        LIMIT 3
        """
    ).fetchall()
    for row in sample:
        print(f"   {row}")

    print("\n[DONE] 迁移完成。后续 docker compose 部署或本地 npm run dev 直接读这个 .duckdb 文件即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
