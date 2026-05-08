# 生产部署快照（阿里云 ECS）

> **AI 上下文文档** — 给后续会话快速建立"项目当前部署在哪、跑着什么、有哪些坑"的基本认知，不必反复问。
> 本文档**不含任何凭据**；真实凭据见 ECS 上 `/root/cc-secrets.txt` 与 `/opt/CC/.env.production`（均不在 git 中）。
> 内容仅描述当前部署状态，环境变化时请手工更新对应小节。

---

## 1. 服务器基础

| 项 | 值 |
|---|---|
| 云厂商 / 节点 | 阿里云 ECS（境内某节点） |
| 公网 IP | `223.4.250.171` |
| 系统 | Ubuntu (具体版本通过 `cat /etc/os-release` 查) |
| 主机名 | `iZbp1bwtkrvs37hx3ll5kuZ` |
| SSH 端口 | 22（默认） |
| HTTP 端口 | 80（已在阿里云安全组开放） |
| HTTPS 端口 | 443（开放但目前未启用，无证书） |
| 当前访问地址 | `http://223.4.250.171`（HTTP，无域名） |

> 登录方式：用户掌握，不在本文档记录。

---

## 2. 已安装基础环境

| 组件 | 安装方式 | 备注 |
|------|---------|------|
| Docker CE | `curl -fsSL https://get.docker.com \| sh -s -- --mirror Aliyun` | 走 Aliyun 镜像安装 |
| docker compose v2 | 随 docker-compose-plugin 安装 | |
| Docker registry mirrors | `/etc/docker/daemon.json` 配了 `docker.1ms.run` / `docker.m.daocloud.io` / `dockerproxy.com` / `docker.nju.edu.cn` | 拉镜像必备 |
| git | apt | 用于从 GitHub 拉项目 |

**关键约束**：国内节点必须走镜像加速器，否则 `docker pull` 必然超时。

---

## 3. 项目位置与版本

| 项 | 值 |
|---|---|
| 路径 | `/opt/CC` |
| GitHub | `https://github.com/NoStayUpLate/CC.git` |
| 主分支 | `main` |
| 部署方式 | Docker Compose（`docker-compose.yml` 同栈部署 backend + frontend + caddy + clickhouse） |

**更新流程**：本地改 → push → 服务器 `cd /opt/CC && ./deploy.sh update`

---

## 4. 运行中的容器（4 个）

| 容器名 | 镜像 | 容器内端口 | 宿主映射 | 角色 |
|--------|------|----------|---------|------|
| `novel_caddy` | `caddy:2-alpine` | 80 / 443 | `0.0.0.0:80→80` / `0.0.0.0:443→443` | 反向代理（**当前 HTTP-only 模式**） |
| `novel_frontend` | `cc-frontend`（本地构建） | 80 | 仅内网 | nginx + React build 静态托管 + `/api` 反代 |
| `novel_backend` | `cc-backend`（本地构建） | 8000 | 仅内网 | FastAPI + Playwright + APScheduler |
| `novel_clickhouse` | `clickhouse/clickhouse-server:24-alpine` | 8123 / 9000 | 仅内网 | 数据库（**同栈部署**，非外部） |

**Docker 卷（数据持久化）**：
- `backend_data` — 装 SQLite 用户库 `auth_users.db`
- `clickhouse_data` — ClickHouse 数据
- `clickhouse_logs` — ClickHouse 日志
- `caddy_data` / `caddy_config` — Caddy 自动签证书的状态（HTTP 模式下基本为空）

---

## 5. 关键文件位置（在 ECS 上）

| 文件 | 内容 | 是否在 git |
|------|------|----------|
| `/opt/CC/.env.production` | 所有真凭据（JWT_SECRET / CLICKHOUSE_PASSWORD / REGISTRATION_CODE / ...） | ❌ gitignore |
| `/opt/CC/Caddyfile` | Caddy 配置，**当前已临时改为 `:80 {`** 而非 `{$DOMAIN} {` | ✓ 在 git，但服务器上的修改未提交 |
| `/opt/CC/docker-compose.yml` | 主 compose | ✓ |
| `/opt/CC/deploy.sh` | 一键运维入口 | ✓ |
| `/root/cc-secrets.txt` | 部署时生成的凭据备份（仅 root 可读） | ❌ 仅服务器 |

> ⚠️ **Caddyfile 已被本地修改**：`sed -i 's|{$DOMAIN} {|:80 {|' Caddyfile`。下次 `git pull` 如果远端 Caddyfile 有改动会冲突，处理时优先保留本地的 `:80 {`，或者先决定要不要切回域名 + HTTPS 模式。

---

## 6. 鉴权与登录

| 项 | 值 |
|---|---|
| AUTH_BACKEND | `sqlite` |
| 自助注册 | **开启**（`REGISTRATION_CODE` 已配，具体值见 `.env.production`） |
| Cookie 配置 | `COOKIE_SECURE=false`（HTTP 模式必须）/ `COOKIE_SAMESITE=lax` |
| 已注册账号 | `admin`（密码用户自定，已可登录） |

**重要 bug 已修**：之前 `docker-compose.yml` 把 `COOKIE_SECURE` 写死成 `"true"`，HTTP 部署时浏览器拒种 cookie，登录后反复跳登录页。已改为 `${COOKIE_SECURE:-true}` 从 .env 读取（commit `f9590a9`）。

---

## 7. ⚠️ 当前已知限制

| 限制 | 影响 | 可选解决方向 |
|------|------|------------|
| **国内节点出口几乎不可达境外**（实测 Wattpad、Cloudflare 1.1.1.1 都 10s 超时） | 爬虫无法抓任何数据 | A) 换香港/新加坡 ECS（推荐长期）<br>B) 接 HTTP/SOCKS5 代理（短期，有合规风险）<br>C) 塞本地 dump 数据先验收 UI |
| 无域名 | 无 HTTPS / Caddy 走 :80 / 浏览器经常自动升级 https 导致访问失败 | 买域名后改回 `Caddyfile` 的 `{$DOMAIN} {` 模式 + `.env` 的 `COOKIE_SECURE=true` |
| 数据库为空 | 看板进了登录但无数据 | 同上，或塞 dump |

---

## 8. 常用运维命令（在 `/opt/CC` 下执行）

```bash
# 状态
./deploy.sh status                    # 容器状态 + /health 健康检查 + 访问地址
./deploy.sh logs backend              # 跟随后端日志（可换 frontend / caddy / clickhouse）

# 生命周期
./deploy.sh up                        # 启动（首次或更新后）
./deploy.sh restart                   # 重启全部
./deploy.sh down                      # 停止
./deploy.sh update                    # git pull + 重建 + 重启 + 清理悬挂镜像

# 杂项
./deploy.sh secret                    # 生成 JWT_SECRET（仅打印，不落盘）

# 查看后端容器实际拿到的环境变量（注意必须带 --env-file）
docker compose --env-file .env.production exec backend env | grep COOKIE

# 进 ClickHouse 客户端交互查询
docker compose --env-file .env.production exec clickhouse \
  clickhouse-client --user app --password "$(grep ^CLICKHOUSE_PASSWORD /opt/CC/.env.production | cut -d= -f2)"

# 查注册邀请码
grep REGISTRATION_CODE /opt/CC/.env.production

# CLI 管理 SQLite 用户
docker compose --env-file .env.production exec backend python -m auth.cli list
docker compose --env-file .env.production exec backend python -m auth.cli add-user xxx -p yyy
```

---

## 9. 部署过程中已踩过的坑（按时间）

避免后续 AI 重复掉坑里：

1. **Docker 安装脚本被 GFW 拦** → `--mirror Aliyun` 解决
2. **Docker 镜像 pull 超时** → `daemon.json` 配 registry-mirrors 解决
3. **Dockerfile apt 龟速** → 已 commit 全栈用 mirrors.aliyun.com / npmmirror（`backend/Dockerfile`）
4. **passlib 与 bcrypt 5.x 不兼容** → 改用 bcrypt 直接调用，已 commit
5. **COOKIE_SECURE 写死 "true"** → 改用 `${COOKIE_SECURE:-true}` + .env.production.example 补 `COOKIE_SECURE=true` 默认行
6. **`.env.production.example` 漏 COOKIE_SECURE 行** → sed 替换没匹配到，导致用户配置不生效，已修
7. **浏览器 HSTS 自动升级 HTTPS** → 教用户用无痕窗口或关 Edge 的"自动 HTTPS"
8. **跨境网络限制** → 当前未解决，是项目最大瓶颈

---

## 10. 待决策（用户尚未拍板）

- [ ] 是否塞本地 ClickHouse dump 作为初始数据（用户在写 `scripts/dump_local_data.py` + `load_seed_data.sh`，**进行中**）
- [ ] 是否换香港/新加坡 ECS 节点（彻底解决跨境）
- [ ] 是否买域名加 HTTPS（让看板正式可用）
- [ ] 团队其他成员是否需要邀请码自助注册（注册码就是入口控制）

---

## 11. 相关资源

| 资源 | 位置 |
|------|------|
| 项目顶层说明 | [README.md](../README.md) |
| AI 工作手册 | [CLAUDE.md](../CLAUDE.md) |
| 爬虫架构 skill | [.claude/skills/add-scraper/SKILL.md](../.claude/skills/add-scraper/SKILL.md) |
| 通用工程加固 skill | [.claude/skills/project-hardening/SKILL.md](../.claude/skills/project-hardening/SKILL.md) |
| GitHub 仓库 | <https://github.com/NoStayUpLate/CC> |
