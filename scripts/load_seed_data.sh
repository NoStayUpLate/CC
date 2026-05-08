#!/usr/bin/env bash
# 服务器侧灌入本地 dump 到同栈 ClickHouse 容器。
# 在项目根目录运行（与 docker-compose.yml 同级），ClickHouse 容器须已 healthy。
#
# 用法：
#   ./scripts/load_seed_data.sh                       # 默认追加 seed/ 下所有 *.native.gz
#   ./scripts/load_seed_data.sh --reset               # 推荐：先 TRUNCATE 再导入（避免重复行）
#   ./scripts/load_seed_data.sh --reset --optimize    # 导入后 OPTIMIZE FINAL（强制 ReplacingMergeTree 合并）
#   ./scripts/load_seed_data.sh --tables novels       # 只导一张表
#   ./scripts/load_seed_data.sh --seed-dir ./seed --env-file .env.production
#
# 退出码：0=成功；非 0=任一阶段失败（set -e）

set -euo pipefail

SEED_DIR="./seed"
ENV_FILE=".env.production"
TABLES=()
RESET=0
OPTIMIZE=0

usage() {
    grep -E '^#( |!|$)' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --reset)     RESET=1; shift ;;
        --optimize)  OPTIMIZE=1; shift ;;
        --tables)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do TABLES+=("$1"); shift; done
            ;;
        --seed-dir)  SEED_DIR="$2"; shift 2 ;;
        --env-file)  ENV_FILE="$2"; shift 2 ;;
        -h|--help)   usage 0 ;;
        *) echo "Unknown arg: $1" >&2; usage 1 ;;
    esac
done

# 加载环境变量拿 ClickHouse 凭据
if [[ -f "$ENV_FILE" ]]; then
    set -a; # shellcheck disable=SC1090
    source "$ENV_FILE"; set +a
else
    echo "WARN: $ENV_FILE not found, relying on shell env" >&2
fi

CH_USER="${CLICKHOUSE_USERNAME:-app}"
CH_DB="${CLICKHOUSE_DATABASE:-analysis}"
: "${CLICKHOUSE_PASSWORD:?CLICKHOUSE_PASSWORD missing (set in $ENV_FILE)}"
CH_PASS="$CLICKHOUSE_PASSWORD"

# 默认导入 seed_dir 下所有匹配文件
if [[ ${#TABLES[@]} -eq 0 ]]; then
    shopt -s nullglob
    for f in "$SEED_DIR"/*.native.gz; do
        TABLES+=("$(basename "$f" .native.gz)")
    done
    shopt -u nullglob
    if [[ ${#TABLES[@]} -eq 0 ]]; then
        echo "No *.native.gz files found in $SEED_DIR" >&2
        exit 1
    fi
fi

# clickhouse-client 在容器内执行（通过 docker compose exec）
ch_query() {
    docker compose exec -T clickhouse clickhouse-client \
        --user "$CH_USER" --password "$CH_PASS" \
        --database "$CH_DB" --query "$1"
}

ch_check() {
    if ! docker compose ps --status running clickhouse | grep -q clickhouse; then
        echo "ClickHouse container is not running. Start the stack first:" >&2
        echo "  docker compose --env-file $ENV_FILE up -d" >&2
        exit 1
    fi
}

ch_check

echo "Target  : docker compose service 'clickhouse'  db=$CH_DB  user=$CH_USER"
echo "Source  : $SEED_DIR  (${#TABLES[@]} table(s))"
[[ $RESET -eq 1 ]]    && echo "Mode    : RESET (TRUNCATE before insert)"
[[ $OPTIMIZE -eq 1 ]] && echo "Post-op : OPTIMIZE TABLE ... FINAL"
echo

for table in "${TABLES[@]}"; do
    file="$SEED_DIR/$table.native.gz"
    if [[ ! -f "$file" ]]; then
        echo "  [skip] $table: $file not found" >&2
        continue
    fi

    echo "=== $table ==="
    if [[ $RESET -eq 1 ]]; then
        echo "  TRUNCATE TABLE $CH_DB.$table"
        ch_query "TRUNCATE TABLE $CH_DB.$table"
    fi

    echo "  loading $file ..."
    # 宿主机 gunzip → docker stdin → clickhouse-client，避免把大文件拷进容器
    gunzip -c "$file" | docker compose exec -T clickhouse clickhouse-client \
        --user "$CH_USER" --password "$CH_PASS" \
        --database "$CH_DB" \
        --query "INSERT INTO $CH_DB.$table FORMAT Native"

    rows="$(ch_query "SELECT count() FROM $CH_DB.$table" | tr -d '[:space:]')"
    echo "  -> $rows rows now in $table"

    if [[ $OPTIMIZE -eq 1 ]]; then
        echo "  OPTIMIZE TABLE $CH_DB.$table FINAL"
        ch_query "OPTIMIZE TABLE $CH_DB.$table FINAL"
        rows_after="$(ch_query "SELECT count() FROM $CH_DB.$table" | tr -d '[:space:]')"
        echo "  -> $rows_after rows after OPTIMIZE FINAL"
    fi
done

echo
echo "Done."
