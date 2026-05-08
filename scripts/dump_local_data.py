"""
本地 ClickHouse → seed dump 文件（跨平台，Windows 直接 python 跑）。

从 backend/.env 读连接信息（CLICKHOUSE_HOST / PORT / DATABASE / USERNAME / PASSWORD），
通过 HTTP 接口把每张表全量导出为 ClickHouse Native 二进制 + gzip 压缩。

Native 格式跨实例传输 0 丢失（Map / Array / Nullable / LowCardinality 全保留），
比 CSV / JSONEachRow 更小更快，是 ClickHouse 自家推荐的迁移格式。

用法（项目根目录）：
    python scripts/dump_local_data.py
    python scripts/dump_local_data.py --tables novels
    python scripts/dump_local_data.py --output ./seed --tables novels dramas

输出：
    seed/novels.native.gz
    seed/dramas.native.gz
    seed/manifest.json   # 表名 / 行数 / 压缩字节 / 时间戳，便于服务器端核对
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")

CH_HOST = os.environ.get("CLICKHOUSE_HOST", "localhost")
CH_PORT = os.environ.get("CLICKHOUSE_PORT", "8123")
CH_DB = os.environ.get("CLICKHOUSE_DATABASE", "analysis")
CH_USER = os.environ.get("CLICKHOUSE_USERNAME", "default")
CH_PASS = os.environ.get("CLICKHOUSE_PASSWORD", "")

# 把 ClickHouse 主机加进 NO_PROXY，避免 HTTP_PROXY/HTTPS_PROXY 把内网请求吞掉
# （与 backend/database.py 同样的处理）
_existing_np = os.environ.get("NO_PROXY", "") + "," + os.environ.get("no_proxy", "")
_ch_hosts = ",".join(filter(None, [CH_HOST, "localhost", "127.0.0.1"]))
_merged_np = ",".join(p for p in (_ch_hosts + "," + _existing_np).split(",") if p)
os.environ["NO_PROXY"] = _merged_np
os.environ["no_proxy"] = _merged_np

# requests 也通过显式 proxies={} 二次保险，跳过任何会话级代理设置
_NO_PROXIES = {"http": None, "https": None}

DEFAULT_TABLES = ["novels", "dramas"]
HTTP_URL = f"http://{CH_HOST}:{CH_PORT}/"
CHUNK = 1 << 20  # 1 MiB


def _post_sql(sql: str, *, stream: bool = False, timeout: int = 600) -> requests.Response:
    r = requests.post(
        HTTP_URL,
        auth=(CH_USER, CH_PASS),
        data=sql.encode("utf-8"),
        stream=stream,
        timeout=timeout,
        proxies=_NO_PROXIES,
    )
    if not r.ok:
        sys.stderr.write(f"\nClickHouse error ({r.status_code}):\n{r.text}\n")
        r.raise_for_status()
    return r


def _row_count(table: str) -> int:
    r = _post_sql(f"SELECT count() FROM {CH_DB}.{table}", timeout=30)
    return int(r.text.strip())


def dump_table(table: str, out_dir: Path) -> dict:
    sql = f"SELECT * FROM {CH_DB}.{table} FORMAT Native"
    out_path = out_dir / f"{table}.native.gz"
    written = 0
    with _post_sql(sql, stream=True) as r, gzip.open(out_path, "wb", compresslevel=6) as f:
        for chunk in r.iter_content(chunk_size=CHUNK):
            if chunk:
                f.write(chunk)
                written += len(chunk)
    rows = _row_count(table)
    return {
        "table": table,
        "rows": rows,
        "bytes_compressed": out_path.stat().st_size,
        "file": out_path.name,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Dump local ClickHouse tables to seed/ directory.")
    ap.add_argument("--tables", nargs="+", default=DEFAULT_TABLES,
                    help=f"tables to dump (default: {' '.join(DEFAULT_TABLES)})")
    ap.add_argument("--output", default=str(ROOT / "seed"),
                    help="output directory (default: ./seed)")
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Source : http://{CH_HOST}:{CH_PORT}  db={CH_DB}  user={CH_USER}")
    print(f"Output : {out_dir}")
    print(f"Tables : {', '.join(args.tables)}\n")

    manifest = {
        "dumped_at": datetime.now(timezone.utc).isoformat(),
        "source": {"host": CH_HOST, "port": CH_PORT, "database": CH_DB},
        "format": "Native+gzip",
        "tables": [],
    }
    for t in args.tables:
        print(f"  dumping {t} ...", end=" ", flush=True)
        info = dump_table(t, out_dir)
        manifest["tables"].append(info)
        print(f"{info['rows']:>8,} rows -> {info['bytes_compressed']:>12,} bytes  ({info['file']})")

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nDone. Manifest: {out_dir / 'manifest.json'}")
    print("Next steps:")
    print(f"  scp -r {out_dir.name} user@server:/path/to/project/")
    print( "  ssh user@server 'cd /path/to/project && ./scripts/load_seed_data.sh --reset'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
