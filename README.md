# 海外内容监测看板（小说 + 短剧）

一个用于监测海外小说 IP 与海外短剧平台内容热度的全栈看板项目。后端 FastAPI + ClickHouse，前端 React/Vite + Tailwind，爬虫覆盖海外小说与海外短剧两类数据源。

## 功能概览

- **海外小说监测**：Wattpad（API）、Royal Road（周榜）、Syosetu（日/周/月榜）。
- **海外短剧监测**：聚合抓取 NetShort、ShortMax、ReelShort、DramaBox、DramaReels、DramaWave、GoodShort、MoboReels 共 8 个平台。
- **独立分表存储**：小说写入 `novels`，短剧写入 `dramas`，互不混合。
- **GHI 适配度分析**：小说列表在 ClickHouse 查询层计算 `S_popular`、`S_engage`、`S_adapt` 与综合 `GHI`，并标记"黄金三秒钩子"。
- **短剧栏位识别**：按平台首页栏位写入 `rank_type`（如"轮播推荐 / 推荐栏位 / 最近上新 / 顶部推荐 / 近期热门"，具体名称由各平台决定）。
- **后台爬取任务**：API/前端触发，立即返回 `task_id`，前端轮询进度。
- **APScheduler 定时任务**：日榜、周榜、月榜按 cron 自动跑。

## 技术栈

| 层 | 选型 |
|----|------|
| 后端 | Python · FastAPI · Uvicorn · clickhouse-connect · Playwright · BeautifulSoup · APScheduler |
| 前端 | React 18 · Vite · Tailwind CSS · lucide-react |
| 数据库 | ClickHouse（`novels` / `dramas` 两张主表） |
| 部署 | Docker Compose / Windows 启动脚本 |

## 目录结构

```text
.
├── backend/
│   ├── main.py                          # FastAPI 入口，注册 router + lifespan
│   ├── config.py                        # 配置项（pydantic-settings + .env）
│   ├── database.py                      # ClickHouse DDL、迁移、批量写入
│   ├── models.py                        # Pydantic 数据模型
│   ├── requirements.txt
│   ├── routers/
│   │   ├── novels.py                    # 小说列表/详情/元数据
│   │   ├── dramas.py                    # 短剧列表/详情/元数据/爬取
│   │   └── scraper.py                   # 小说爬虫任务触发
│   ├── scrapers/
│   │   ├── __init__.py                  # SCRAPER_REGISTRY / DRAMA_SCRAPER_REGISTRY
│   │   ├── base_scraper.py              # 抽象基类 + S_adapt 预计算工具
│   │   ├── base_http_scraper.py         # HTTP/REST 系基类（重试 + 代理回退）
│   │   ├── base_playwright_scraper.py   # Playwright 系基类（浏览器生命周期）
│   │   ├── sites_config.py              # 站点登记表
│   │   ├── novels/
│   │   │   ├── en_wattpad_scraper.py
│   │   │   ├── en_royal_road_scraper.py
│   │   │   └── ja_syosetu_scraper.py
│   │   └── dramas/
│   │       ├── shortdrama_base.py       # 短剧公共基类（栏位/标签清洗）
│   │       ├── en_shortdrama_top5_scraper.py   # 8 平台聚合调度器
│   │       └── en_{netshort,shortmax,reelshort,dramabox,
│   │            dramareels,dramawave,goodshort,moboreels}_scraper.py
│   └── services/
│       ├── scraper_service.py           # 小说后台任务 + 批量写入
│       ├── drama_scraper_service.py     # 短剧后台任务 + OPTIMIZE FINAL
│       ├── scheduler.py                 # APScheduler 定时调度
│       └── keyword_extractor.py         # 英语关键词提取（仅 en）
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.jsx                      # 看板主入口（小说 + 短剧两个 Tab）
│       ├── api/client.js                # 统一 HTTP 客户端
│       └── components/                  # NovelCard / DramaCard / FilterBar / WordCloud …
├── docker-compose.yml                   # backend + frontend 容器化
├── 启动.bat                             # Windows 一键启动
├── run_wattpad_keywords.py              # 一次性脚本：回填 Wattpad 章节关键词
├── CLAUDE.md                            # AI agent 工作手册（硬约束 / 数据契约）
├── .claude/skills/add-scraper/          # 新增爬虫的标准流程 skill
└── README.md
```

## 爬虫架构

所有爬虫遵循"基类 + 子类 + 注册表"的三段式：

| 基类 | 适用 | 子类需实现 |
|------|------|------------|
| `BaseHttpScraper` | 公开 REST/JSON 或 SSR HTML | `scrape(genre, limit)` |
| `BasePlaywrightScraper` | 需 JS 渲染的站点 | `build_url()` + `_scrape_page()`，可选 `_enrich_results()` 复用浏览器 |
| `BaseShortDramaScraper` | 短剧聚合站点 | `scrape()`，复用栏位解析与详情补全 |

子类注册到 `backend/scrapers/__init__.py` 的 `SCRAPER_REGISTRY`（小说）或 `DRAMA_SCRAPER_REGISTRY`（短剧），即可被 `POST /api/scrape` / `POST /api/dramas/scrape` 调度。

> 新增爬虫请遵循 [.claude/skills/add-scraper/SKILL.md](.claude/skills/add-scraper/SKILL.md) 的五步落地清单。

## 环境准备

### 1. 后端依赖

```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium     # 首次运行 Playwright 系爬虫前
```

### 2. 前端依赖

```bash
cd frontend
npm install
```

### 3. 环境变量

后端读取 `backend/.env`，参考 [`backend/.env.example`](backend/.env.example)：

```env
# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=default
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=

# 爬虫
SCRAPER_HEADLESS=true
SCRAPER_BATCH_SIZE=50
SCRAPER_DELAY_MIN=1.0
SCRAPER_DELAY_MAX=3.5
HTTP_PROXY=

# 定时任务
SCHEDULE_ENABLED=true
SCHEDULE_HOUR=2
SCHEDULE_MINUTE=0
SCHEDULE_LIMIT=100

# 鉴权（必填）
JWT_SECRET=                # openssl rand -hex 32 生成
JWT_EXPIRE_HOURS=8
COOKIE_SECURE=false        # 本地 HTTP=false，生产 HTTPS=true
COOKIE_SAMESITE=lax
AUTH_BACKEND=file          # file 或 sqlite
AUTH_USERS=admin:$2b$12$...   # file 模式 CSV: "user1:hash;user2:hash"
AUTH_SQLITE_PATH=./auth_users.db
REGISTRATION_CODE=         # 空串 = 关闭注册；非空 + sqlite 模式 = 启用自助注册
```

> ⚠️ 真实数据库密码、`JWT_SECRET`、`AUTH_USERS` 不要提交到仓库。`JWT_SECRET` 缺失时后端启动会直接 fail-fast 退出。

## 鉴权与用户管理

所有业务接口（`/api/novels`、`/api/dramas`、`/api/scrape` 等）默认要求登录。前端首次访问会自动渲染登录页，登录成功后种 HTTP-only Cookie（`access_token`），后续请求由浏览器自动携带。

### 两种 user backend 切换

| 模式 | 适用 | 配置 |
|------|------|------|
| `file` | 单个/少量固定账号；运维不愿管 SQLite | `AUTH_BACKEND=file` + `AUTH_USERS="user1:bcrypt_hash;user2:bcrypt_hash"` |
| `sqlite` | 多人团队，账号会增删 | `AUTH_BACKEND=sqlite` + `AUTH_SQLITE_PATH=./auth_users.db`，用 CLI 管理 |

### 生成 bcrypt 密码哈希（file 模式必备）

```bash
cd backend
python -m auth.cli hash 你的密码
# 输出 $2b$12$xxx... 把它和用户名拼成 AUTH_USERS：
#   AUTH_USERS=admin:$2b$12$xxx
# 多个用户用 ; 分隔
```

### CLI 管理用户（sqlite 模式）

```bash
cd backend

# 添加用户（不带 -p 会交互式输入，更安全）
python -m auth.cli add-user alice -p secret123

# 列出所有用户
python -m auth.cli list

# 修改密码
python -m auth.cli passwd alice -p newpass

# 禁用用户（软删除）
python -m auth.cli delete alice
```

### 生成 JWT_SECRET

```bash
openssl rand -hex 32
# 把输出粘贴到 backend/.env 的 JWT_SECRET=
```

> ⚠️ 切换 backend 模式或修改 `AUTH_USERS` 后必须**重启后端**才生效。已签发的 JWT 会在 `JWT_EXPIRE_HOURS` 之后过期，删除/禁用用户会立即让其下一次请求被推回登录页。

### 用户自助注册（可选）

把 `REGISTRATION_CODE` 设为非空字符串、且 `AUTH_BACKEND=sqlite` 时，登录页会出现「立即注册」入口。前端表单要求填邀请码，与服务端 `REGISTRATION_CODE` 完全一致才能提交。

```env
AUTH_BACKEND=sqlite
REGISTRATION_CODE=team-2026-spring   # 任意字符串，线下分发给团队成员
```

校验规则（同时全过才能创建）：
- 邀请码精确匹配
- 用户名 3-32 位，仅允许字母 / 数字 / 下划线
- 密码至少 6 位
- 用户名未被占用

注册成功后端会自动种 cookie，相当于已经登录，直接进入主看板。

> ⚠️ 邀请码视同密码——不要写进任何文档、聊天记录或仓库。修改后历史邀请立即作废，已注册用户不受影响。如要彻底关闭注册，把 `REGISTRATION_CODE` 设为空串重启即可。

## 启动项目

### 方式一：Windows 一键启动

```bat
启动.bat
```

会同时拉起后端、前端，并自动打开浏览器。

### 方式二：手动启动

```bash
# 终端 A — 后端
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 终端 B — 前端
cd frontend
npm run dev
```

### 方式三：Docker Compose（本地）

`docker-compose.yml` 是**生产形态**（nginx + Caddy + 同源），本地开发请叠加 `docker-compose.dev.yml` override：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

dev 模式下：
- 后端暴露 `localhost:8000`，前端跑 vite dev `localhost:5173`
- 不启动 Caddy，`COOKIE_SECURE=false`
- 代码文件挂载进容器，支持热重载

> ClickHouse 不在 compose 内，需独立部署或指向已有实例。

## 上云部署（阿里云 ECS）

部署目标：阿里云 ECS（单 VPS Linux 主机）。架构：

```
浏览器 → Caddy(443/80, 自动 LE 证书) → frontend(nginx, /api 反代) → backend(FastAPI, 8000) → ClickHouse(外部)
```

### 一键运维脚本 `deploy.sh`

项目根目录的 [`deploy.sh`](deploy.sh) 封装了所有 docker compose 操作（带预检查 + 健康检查），所有运维动作都通过子命令调用：

```bash
./deploy.sh up          # 首次启动 / 平滑更新（默认）
./deploy.sh down        # 停止所有容器（数据卷保留）
./deploy.sh restart     # down + up
./deploy.sh status      # 容器状态 + /health 健康检查 + 访问地址
./deploy.sh logs [svc]  # 跟随日志，svc ∈ {backend, frontend, caddy}
./deploy.sh update      # git pull + 重建镜像 + 平滑重启 + 清理悬挂镜像
./deploy.sh secret      # 生成一个 JWT_SECRET（粘进 .env.production）
./deploy.sh help        # 完整说明
```

预检查内容：docker / docker compose 是否可用、`.env.production` 是否存在、`DOMAIN` / `JWT_SECRET` / `CLICKHOUSE_*` 是否填齐、`AUTH_BACKEND=file` 时 `AUTH_USERS` 是否仍是占位符。任何缺失会带可执行的修复命令直接退出。

### 首次部署（5 步）

```bash
# 1. ECS 装 docker（以 Ubuntu 为例）
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# 2. 上传项目（scp / rsync / git clone 都可）
scp -r drama_overseas_novel_project/ user@ecs-ip:/opt/
cd /opt/drama_overseas_novel_project

# 3. 准备 .env.production
cp .env.production.example .env.production
./deploy.sh secret              # 把输出粘到 .env.production 的 JWT_SECRET=
vim .env.production             # 填 DOMAIN / CLICKHOUSE_* / AUTH_USERS（或 AUTH_BACKEND=sqlite）

# 4. 一键启动
./deploy.sh up

# 5. 看 Caddy 签证书的过程
./deploy.sh logs caddy
```

### 必备前置条件

- **域名**：A 记录指向 ECS 公网 IP（Caddy 才能签 Let's Encrypt 证书）
- **安全组**：放开 80 / 443 入站
- **`.env.production`** 至少填齐：`DOMAIN` / `JWT_SECRET` / `AUTH_USERS`（或 `AUTH_BACKEND=sqlite` 然后用 CLI 加用户）/ `CLICKHOUSE_*`

### 日常更新

```bash
./deploy.sh update      # 一条命令搞定 git pull + 重建 + 重启 + 清理
```

### 进阶运维

```bash
# SQLite 模式下进容器加用户
docker compose exec backend python -m auth.cli add-user alice -p xxx

# 备份 SQLite 用户库
docker run --rm -v drama_overseas_novel_project_backend_data:/data \
  -v $(pwd):/backup alpine cp /data/auth_users.db /backup/
```

### 没有公网域名时的临时方案

把 `Caddyfile` 里的 `{$DOMAIN}` 改成 `:80`（明文 HTTP），同时把 `.env.production` 的 `COOKIE_SECURE` 改成 `false`，否则浏览器会拒绝种 cookie 导致登录后立即被踢回登录页。

## 前端命令

```bash
cd frontend
npm run dev        # 开发模式
npm run build      # 生产构建
npm run preview    # 预览构建产物
```

## 后端 API

完整文档：`http://localhost:8000/docs`

### 健康检查

```http
GET /health
```

### 鉴权（开放，无需登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/config` | 返回 `{registration_enabled}`，前端用以决定是否展示注册入口 |
| POST | `/api/auth/login` | body: `{username, password}` → 成功种 cookie |
| POST | `/api/auth/register` | body: `{username, password, invite_code}` → 成功种 cookie；仅 sqlite + `REGISTRATION_CODE` 非空时可用 |
| POST | `/api/auth/logout` | 清除 cookie |
| GET | `/api/auth/me` | 返回当前登录用户（已登录才能调通，否则 401） |

### 小说

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/novels` | 列表（GHI 排序），支持 `platform / lang / tags / title / date_range / rank_type / page / page_size` |
| GET | `/api/novels/{novel_id}` | 详情（含 `top_keywords` 关键词云） |
| GET | `/api/novels/meta/platforms` | 库内所有平台 |
| GET | `/api/novels/meta/langs` | 库内所有语种 |
| GET | `/api/novels/meta/tags` | 高频标签 Top 50 |
| POST | `/api/scrape` | 触发小说爬取，body: `{platform, genre, limit}` |
| GET | `/api/scrape/{task_id}` | 查询任务状态 |

### 短剧

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dramas` | 列表，支持 `platform / title / date_range / rank_type / page / page_size` |
| GET | `/api/dramas/{drama_id}` | 详情 |
| GET | `/api/dramas/meta/platforms` | 库内所有平台 |
| GET | `/api/dramas/meta/langs` | 库内所有语种 |
| GET | `/api/dramas/meta/tags` | 高频标签 Top 50 |
| POST | `/api/dramas/scrape` | 触发短剧爬取，body: `{platform, genre, limit}` |
| GET | `/api/dramas/scrape/{task_id}` | 查询任务状态 |

## 爬虫说明

### 小说爬虫

`SCRAPER_REGISTRY` 注册的 platform key：

| key | 平台 | 抓取方式 |
|-----|------|----------|
| `wattpad` | Wattpad | 公开 REST API + 阅读页 SSR HTML（前三章关键词提取） |
| `royal_road` | Royal Road | Playwright 周榜 + 章节正文关键词提取 |
| `syosetu_daily` / `syosetu_weekly` / `syosetu_monthly` | 小説家になろう | Playwright，按榜单类型分别注册 |

> 仅英语会触发关键词提取（`services/keyword_extractor.py`），日语/韩语等返回 `None`。

### 短剧爬虫

`DRAMA_SCRAPER_REGISTRY` 当前注册：

| key | 说明 |
|-----|------|
| `shortdrama_top5` | **聚合调度器**，依次抓取下表 8 个子平台并写入 `dramas` 表 |

子平台（位于 `backend/scrapers/dramas/`）：

- NetShort
- ShortMax
- ReelShort
- DramaBox
- DramaReels
- DramaWave
- GoodShort
- MoboReels

短剧首页栏位会写入 `rank_type`，常见值：`轮播推荐` / `推荐栏位` / `最近上新` / `顶部推荐` / `近期热门`（具体由各平台决定）。如平台公开页面没有可识别栏位，本轮跳过。

## 数据库设计

### `novels`

- 引擎：`ReplacingMergeTree`，`ORDER BY (platform, lang, title)`，按 `toYYYYMM(created_at)` 分区。
- 核心字段：`title / summary / tags / views / likes / original_url / platform / lang / s_adapt / top_keywords / rank_type / created_at`。
- `views` / `likes` 为 `Nullable(UInt64)`：抓不到时保持 `NULL`，**禁止用 0 占位**。
- `s_adapt` 由爬虫端按标签预计算（`base_scraper._calc_s_adapt`），存入 `Float32`。
- `top_keywords` 为 `Map(String, UInt32)`，仅英语小说写入。

### `dramas`

- 引擎：`ReplacingMergeTree(created_at)`，`ORDER BY (platform, title)`，分区同上。
- 核心字段：`title / summary / cover_url / tags / episodes / rank_in_platform / heat_score / platform / lang / rank_type / crawl_date / source_url / created_at`。
- 抓取完成后自动执行 `OPTIMIZE TABLE dramas FINAL` 触发去重合并。

### GHI 算法（在 ClickHouse SQL 内计算）

```text
GHI = S_popular × 0.3 + S_engage × 0.3 + S_adapt × 0.4

S_popular = min(log10(views + 1) × 10, 100)
S_engage  = min((likes / views) × 100 × 语种系数, 100)   # 韩语 ×1.2 · 英语 ×0.8 · 其他 ×1.0
S_adapt   = 爬虫端预计算（标签命中 S/A 级映射）
has_hook  = summary 包含 reborn/rebirth/revenge/betrayed/transmigrat/identity/
            reincarnation/regression/villainess/abandoned/second chance 任一关键词
```

## 定时任务

`backend/services/scheduler.py` 注册三个 cron job（默认 Asia/Shanghai 凌晨 02:00）：

| 频率 | 平台 |
|------|------|
| 每天 | `wattpad`、`syosetu_daily` |
| 每周一 | `royal_road`、`syosetu_weekly` |
| 每月 1 号 | `syosetu_monthly` |

通过环境变量调整：

```env
SCHEDULE_ENABLED=true     # false 关闭所有定时任务
SCHEDULE_HOUR=2
SCHEDULE_MINUTE=0
SCHEDULE_LIMIT=100        # 每平台每次爬取条数上限
```

> 短剧定时任务尚未挂载，目前通过 `POST /api/dramas/scrape` 手动触发或自行扩展 scheduler。

## 常见问题

### 前端端口不是 5173

如 `5173` 被占用，Vite 会自动顺延（5174、5175…），请以终端输出为准。

### Playwright 报 Chromium 不存在

```bash
python -m playwright install chromium
```

### ClickHouse 并发 session 报错

项目中 ClickHouse client 已设置 `autogenerate_session_id=False`，并在每次查询时通过 `database.get_client()` 取独立 client。如果在新代码里看到模块级 client 单例，请改为按需创建。

### 短剧数据重复

短剧抓取完成后会自动执行 `OPTIMIZE TABLE dramas FINAL`。手动调试后如仍残留重复行：

```sql
OPTIMIZE TABLE dramas FINAL;
```

### 内网 ClickHouse 走代理失败

`database.py` 启动时会自动把 ClickHouse 主机加入 `NO_PROXY`。如自定义了主机，记得同步更新该列表。

### 后端启动报 `JWT_SECRET 未配置`

在 `backend/.env` 设置 `JWT_SECRET=$(openssl rand -hex 32)` 后再启动。空 secret 会被启动期 fail-fast 拒绝，避免裸出业务接口。

### 登录后立刻被踢回登录页

99% 是 `COOKIE_SECURE` 与传输协议不匹配：本地 HTTP 必须 `COOKIE_SECURE=false`，生产 HTTPS 必须 `true`。改完重启后端即可。

### 忘记密码

- file 模式：用 `python -m auth.cli hash <新密码>` 重新生成 hash，替换 `.env` 里 `AUTH_USERS` 对应行，重启后端。
- sqlite 模式：`python -m auth.cli passwd <username> -p <新密码>`。

### Vite dev 模式 cookie 不生效

vite.config.js 的 proxy 已默认透传 cookie，无需特殊配置。如自定义 `proxy.cookieDomainRewrite` 需保留默认值。

## 开发约定

- 前端尽量使用 Tailwind CSS，不新增自定义 CSS。
- 后端 SQL 必须使用 ClickHouse 参数化写法（`{name:Type}`），禁止字符串拼接用户输入。
- 小说与短剧数据**必须分表**存储。
- GHI 口径由 ClickHouse 统一计算，**前端只做展示**，不要重算。
- 爬虫缺失数值返回 `None`，禁止 0/空串占位（会污染 GHI）。
- 新增爬虫请走 [.claude/skills/add-scraper/SKILL.md](.claude/skills/add-scraper/SKILL.md) 的标准流程；AI 协作约定见 [CLAUDE.md](CLAUDE.md)。
- **新增业务 router 必须挂在 `Depends(require_user)` 守卫下**，参考 [`backend/main.py`](backend/main.py) 的 `_protected` 注入方式，禁止裸出。
- bcrypt 密码哈希统一走 [`backend/auth/password.py`](backend/auth/password.py) 的 `hash_password()`，不要直接调底层。
- 真实环境变量、数据库密码、`JWT_SECRET`、`AUTH_USERS`、`auth_users.db` 都不要写入 README 或提交到仓库（`.gitignore` 已排除）。
