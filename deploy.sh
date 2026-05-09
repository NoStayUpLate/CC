#!/usr/bin/env bash
# 服务器一键运维脚本（Linux / macOS）
#
# 子命令:
#   ./deploy.sh up         首次启动 / 平滑更新（默认）
#   ./deploy.sh down       停止全部容器
#   ./deploy.sh restart    down + up
#   ./deploy.sh status     展示运行状态 + 健康检查
#   ./deploy.sh logs [svc] 跟随日志（默认全部，可指定 backend / frontend）
#   ./deploy.sh update     git pull → 重建镜像 → 启动 → 清理悬挂镜像
#   ./deploy.sh secret     生成一个 JWT_SECRET 并打印
#   ./deploy.sh help       使用说明
#
# 使用前置条件:
#   - 已安装 docker + docker compose v2（apt/yum 装 docker-ce 自带）
#   - 项目根目录有 .env.production（可从 .env.production.example 复制后填）
#
# 当前部署形态：HTTP-only（直接 http://<服务器公网IP>）；DuckDB 嵌入式不需要外部 DB。

set -euo pipefail

# ─────────────────────────────────────────────────────────────
# 颜色 & 日志辅助
# ─────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_BLUE=$'\033[34m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
    C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_DIM=""; C_RESET=""
fi

log()    { printf '%s[deploy]%s %s\n' "$C_BLUE"   "$C_RESET" "$*"; }
ok()     { printf '%s[ ✓ ]%s %s\n'    "$C_GREEN"  "$C_RESET" "$*"; }
warn()   { printf '%s[ ! ]%s %s\n'    "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()    { printf '%s[ ✗ ]%s %s\n'    "$C_RED"    "$C_RESET" "$*" >&2; exit 1; }

# 切到脚本所在目录，保证相对路径稳定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE=".env.production"
ENV_EXAMPLE=".env.production.example"

# ─────────────────────────────────────────────────────────────
# 依赖检测：docker / docker compose
# 兼容 v2 (docker compose) 与 v1 (docker-compose)
# ─────────────────────────────────────────────────────────────
detect_compose() {
    if docker compose version >/dev/null 2>&1; then
        COMPOSE=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE=(docker-compose)
        warn "检测到 docker-compose v1，建议升级到 docker compose v2 plugin"
    else
        die "未找到 docker compose。安装方式：apt install docker-compose-plugin / yum install docker-compose-plugin"
    fi
}

check_docker() {
    command -v docker >/dev/null 2>&1 || die "未找到 docker。安装方式：curl -fsSL https://get.docker.com | sh"
    docker info >/dev/null 2>&1 || die "docker daemon 未运行 / 当前用户无权限。试试 sudo systemctl start docker，或把当前用户加入 docker 组：sudo usermod -aG docker \$USER 后重新登录"
    detect_compose
}

# ─────────────────────────────────────────────────────────────
# 环境变量校验
# 仅在 up / restart / update 时执行，logs/down/status 不需要
# ─────────────────────────────────────────────────────────────
check_env() {
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "$ENV_EXAMPLE" ]]; then
            warn "未找到 $ENV_FILE"
            warn "请先复制样例并填值："
            warn "  cp $ENV_EXAMPLE $ENV_FILE && vim $ENV_FILE"
            warn "  生成 JWT_SECRET：./deploy.sh secret"
        fi
        die "缺少 $ENV_FILE，无法启动"
    fi

    # 加载变量并校验关键项（注意：=右侧含 $/" 的不安全 source，所以用 grep + 自行解析）
    # 轻量化版本只剩 JWT_SECRET 必填；DuckDB 不需要密码 / host；HTTP-only 不需要 DOMAIN
    local missing=()
    for key in JWT_SECRET; do
        local val
        val="$(grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true)"
        # 去掉首尾引号与空格
        val="${val#\"}"; val="${val%\"}"; val="${val#\'}"; val="${val%\'}"; val="${val// /}"
        if [[ -z "$val" ]]; then
            missing+=("$key")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        die "$ENV_FILE 缺失关键变量：${missing[*]}"
    fi

    # 校验 JWT_SECRET 长度（HS256 推荐 ≥32 字节 = 64 hex 字符）
    local jwt_len
    jwt_len="$(grep -E '^JWT_SECRET=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '\r"\047 ' | wc -c)"
    if [[ "$jwt_len" -lt 32 ]]; then
        warn "JWT_SECRET 长度 $jwt_len 字符过短（推荐 64 hex），建议 ./deploy.sh secret 重新生成"
    fi

    # AUTH_BACKEND=sqlite 时 SQLite 库路径在容器内固定 /data/auth_users.db；
    # AUTH_BACKEND=file 时 AUTH_USERS 不能为空
    local backend users
    backend="$(grep -E '^AUTH_BACKEND=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '\r"\047 ')"
    backend="${backend:-file}"
    if [[ "$backend" == "file" ]]; then
        users="$(grep -E '^AUTH_USERS=' "$ENV_FILE" | tail -n1 | cut -d= -f2- || true)"
        if [[ -z "$users" || "$users" == *"REPLACE_WITH_REAL_BCRYPT_HASH"* ]]; then
            die "AUTH_BACKEND=file 但 AUTH_USERS 为空 / 仍是占位符。生成 hash：cd backend && python -m auth.cli hash <密码>"
        fi
    fi

    ok "$ENV_FILE 校验通过（backend=$backend）"
}

# ─────────────────────────────────────────────────────────────
# 子命令实现
# ─────────────────────────────────────────────────────────────
cmd_up() {
    check_docker
    check_env
    log "构建并启动容器（轻量化镜像，1-3 分钟；首次拉 base image 视网络而定）..."
    "${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --build --remove-orphans
    ok "容器已启动，等待健康检查..."
    sleep 3
    cmd_status
}

cmd_down() {
    check_docker
    log "停止所有容器（数据卷保留）..."
    "${COMPOSE[@]}" --env-file "$ENV_FILE" down
    ok "已停止"
}

cmd_restart() {
    cmd_down
    cmd_up
}

cmd_status() {
    check_docker
    log "容器状态："
    "${COMPOSE[@]}" --env-file "$ENV_FILE" ps
    echo ""
    log "健康检查："
    if "${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T backend curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
        ok "backend /health  → OK"
    else
        warn "backend /health  → 异常或未就绪（首次启动稍等 30 秒后重试）"
    fi
    if "${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T frontend wget -qO- http://127.0.0.1/ >/dev/null 2>&1; then
        ok "frontend nginx   → OK"
    else
        warn "frontend nginx   → 异常或未就绪"
    fi

    # HTTP-only 部署，没有 Caddy / 域名；提示用户用 服务器公网 IP 访问
    echo ""
    local public_ip
    public_ip="$(curl -s --max-time 3 ifconfig.me 2>/dev/null || true)"
    if [[ -n "$public_ip" ]]; then
        log "访问地址：${C_GREEN}http://${public_ip}${C_RESET}"
    else
        log "访问地址：${C_GREEN}http://<本机公网IP>${C_RESET}"
    fi
    printf '%s' "$C_DIM"
    echo "  HTTP-only 模式，请确认安全组 80 端口已放开。"
    echo "  需要 HTTPS / 自签证书时再加回 Caddy（参考 git 历史 docker-compose.yml）。"
    printf '%s' "$C_RESET"
}

cmd_logs() {
    check_docker
    local svc="${1:-}"
    if [[ -n "$svc" ]]; then
        log "跟随 $svc 日志（Ctrl+C 退出）..."
        "${COMPOSE[@]}" --env-file "$ENV_FILE" logs -f --tail=100 "$svc"
    else
        log "跟随所有服务日志（Ctrl+C 退出）..."
        "${COMPOSE[@]}" --env-file "$ENV_FILE" logs -f --tail=100
    fi
}

cmd_update() {
    check_docker
    check_env

    if [[ -d .git ]]; then
        log "拉取最新代码..."
        local before
        before="$(git rev-parse HEAD)"
        git pull --ff-only
        local after
        after="$(git rev-parse HEAD)"
        if [[ "$before" == "$after" ]]; then
            log "代码无更新（HEAD 仍为 ${before:0:8}）"
        else
            ok "已更新到 ${after:0:8}"
        fi
    else
        warn "未检测到 .git 目录，跳过 git pull（如需更新请手动 scp / rsync）"
    fi

    log "重建镜像并平滑重启..."
    "${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --build --remove-orphans

    log "清理悬挂镜像（保留命名镜像）..."
    docker image prune -f >/dev/null
    ok "更新完成"
    cmd_status
}

cmd_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    elif [[ -r /dev/urandom ]]; then
        head -c 32 /dev/urandom | xxd -p -c 64
    else
        die "未找到 openssl 或 /dev/urandom，无法生成"
    fi
}

cmd_help() {
    cat <<EOF
$(printf '%s' "$C_BLUE")海外内容监测看板 — 服务器运维脚本$(printf '%s' "$C_RESET")

用法:
  ./deploy.sh <command> [args]

命令:
  $(printf '%s' "$C_GREEN")up$(printf '%s' "$C_RESET")          首次启动 / 平滑更新（默认）
  $(printf '%s' "$C_GREEN")down$(printf '%s' "$C_RESET")        停止所有容器（保留数据卷）
  $(printf '%s' "$C_GREEN")restart$(printf '%s' "$C_RESET")     down + up
  $(printf '%s' "$C_GREEN")status$(printf '%s' "$C_RESET")      展示运行状态 + /health 健康检查
  $(printf '%s' "$C_GREEN")logs$(printf '%s' "$C_RESET") [svc]  跟随日志，svc ∈ {backend, frontend}
  $(printf '%s' "$C_GREEN")update$(printf '%s' "$C_RESET")      git pull → 重建镜像 → 平滑重启 → 清理
  $(printf '%s' "$C_GREEN")secret$(printf '%s' "$C_RESET")      生成 JWT_SECRET（粘到 .env.production）
  $(printf '%s' "$C_GREEN")help$(printf '%s' "$C_RESET")        显示本说明

首次部署流程:
  1) cp .env.production.example .env.production
  2) ./deploy.sh secret              # 复制输出粘到 JWT_SECRET=
  3) vim .env.production             # 填 JWT_SECRET / AUTH_BACKEND / REGISTRATION_CODE 等
  4) ./deploy.sh up

日常更新:
  ./deploy.sh update                 # 拉新代码 + 重建 + 重启 一气呵成

排查:
  ./deploy.sh status
  ./deploy.sh logs backend
EOF
}

# ─────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────
main() {
    local cmd="${1:-up}"
    shift || true

    case "$cmd" in
        up|start)            cmd_up           ;;
        down|stop)           cmd_down         ;;
        restart)             cmd_restart      ;;
        status|ps)           cmd_status       ;;
        logs|log)            cmd_logs "$@"    ;;
        update|upgrade)      cmd_update       ;;
        secret|gen-secret)   cmd_secret       ;;
        help|-h|--help)      cmd_help         ;;
        *)
            warn "未知命令: $cmd"
            echo ""
            cmd_help
            exit 2
            ;;
    esac
}

main "$@"
