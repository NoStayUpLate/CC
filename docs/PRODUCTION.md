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
| 部署方式 | Docker Compose（瘦身后：backend + frontend；DuckDB 走嵌入式无独立容器） |

**更新流程**：本地改 → push → 服务器 `cd /opt/CC && ./deploy.sh update`

---

## 4. 运行中的容器（2 个，瘦身后）

| 容器名 | 镜像 | 容器内端口 | 宿主映射 | 角色 |
|--------|------|----------|---------|------|
| `novel_frontend` | `cc-frontend`（本地构建） | 80 | `0.0.0.0:80→80` | nginx + React build 静态托管 + `/api` 反代 |
| `novel_backend` | `cc-backend`（本地构建） | 8000 | 仅 compose 内网 | FastAPI + DuckDB（嵌入式）+ APScheduler；默认不装 Chromium |

> 历史上还有 `novel_caddy`（反代）+ `novel_clickhouse`（数据库），1C2G 服务器上跑不动，已下线 —
> Caddy 在 HTTP-only 模式下属于空转；ClickHouse 24.x 默认要 600MB+ 内存，换成 DuckDB 嵌入式后省到 ~50MB。
> 需要 HTTPS 时再把 Caddy 加回 compose（`Caddyfile` 仍在仓库里）。

**Docker 卷（数据持久化）**：
- `backend_data` — SQLite 用户库 `auth_users.db` **+ DuckDB 数据库 `dashboard.duckdb`**（同卷下两个文件）

---

## 5. 关键文件位置（在 ECS 上）

| 文件 | 内容 | 是否在 git |
|------|------|----------|
| `/opt/CC/.env.production` | JWT_SECRET / REGISTRATION_CODE 等真凭据 | ❌ gitignore |
| `/opt/CC/docker-compose.yml` | 主 compose（瘦身后只剩 backend / frontend） | ✓ |
| `/opt/CC/deploy.sh` | 一键运维入口 | ✓ |
| `/opt/CC/Caddyfile` | Caddy 配置，**当前未启用**；将来要加 HTTPS 时把 Caddy 服务加回 compose 即可 | ✓ |
| `/opt/CC/.../dashboard.duckdb` | DuckDB 数据库文件，**容器内** `/data/dashboard.duckdb`，挂在 `backend_data` 卷 | ❌ 持久卷 |
| `/root/cc-secrets.txt` | 部署时生成的凭据备份（仅 root 可读） | ❌ 仅服务器 |

> ⚠️ 历史上服务器侧 Caddyfile 被 `sed` 改成过 `:80 {` 模式以便 HTTP-only 部署。瘦身后 Caddy 不再启用，
> 这个本地改动可以丢弃 / 还原；以后如果重新加 Caddy 上 HTTPS，记得把 Caddyfile 改回 `{$DOMAIN} {` 模板。

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
| 无域名 | 无 HTTPS，浏览器有时自动升级 https 导致访问失败 | 买域名后把 Caddy 加回 `docker-compose.yml`（参考 git 历史 `b73126f` 之前的版本） + `.env` 改 `COOKIE_SECURE=true` |
| 数据库为空 | 看板进了登录但无数据 | 同上，或本地 dump duckdb 文件 scp 到服务器卷里（卷路径：`docker volume inspect cc_backend_data`） |

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

# 进 DuckDB 交互查询（嵌入式，没独立容器，直接进 backend 容器跑 python 起 cli）
docker compose --env-file .env.production exec backend \
  python -c "import duckdb; con=duckdb.connect('/data/dashboard.duckdb'); print(con.execute('SELECT count(*) FROM novels').fetchone(), con.execute('SELECT count(*) FROM dramas').fetchone())"

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
8. **跨境网络限制** → 当前未解决，是项目最大瓶颈（生产 backend 默认不装 Chromium，因为爬虫跨境跑也是失败循环）
9. **ClickHouse 在阿里云 ECS 上 NUMA syscall 被 seccomp 拦** → 起初加 `cap_add: SYS_NICE / IPC_LOCK` + `seccomp=unconfined` 解决；后来直接换 DuckDB 嵌入式，问题不复存在
10. **1C2G 内存不够** → 整体瘦身：CH→DuckDB（省 600MB）+ 去掉 Caddy（省 30MB）+ 默认不装 Chromium（省 300MB 内存 + 700MB 镜像）

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
