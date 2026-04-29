# CLAUDE.md

> AI agent 工作手册（不是 README）。人类向部署/使用文档见 [README.md](README.md)。
> 这里只写 **30 秒看懂骨架 + 高频踩坑** 的内容。

---

## 1. 项目一览

海外**小说 + 短剧**监测看板，FastAPI + ClickHouse + React/Vite。

数据流：
```
scraper(list[dict]) → service(batch_insert) → ClickHouse → SQL 内算 GHI → React 展示
```

GHI / S_popular / S_engage / S_adapt / has_hook **全部在 ClickHouse 查询层算**，前端只做展示。

---

## 2. 目录速查

| 路径 | 用途 |
|------|------|
| [backend/main.py](backend/main.py) | FastAPI 入口，注册 router + lifespan(init_db + scheduler) |
| [backend/database.py](backend/database.py) | DDL + 迁移 + 批量写入；**字段语义权威来源** |
| [backend/models.py](backend/models.py) | Pydantic 行结构（NovelRow / DramaRow / 输出模型） |
| [backend/config.py](backend/config.py) | 配置项；运行时通过 `backend/.env` 覆盖 |
| [backend/routers/](backend/routers/) | `auth.py`（开放）/ `novels.py` / `dramas.py` / `scraper.py`（后三者全部 require_user 守卫） |
| [backend/auth/](backend/auth/) | 鉴权子系统：`backends.py`（File/SQLite 可插拔）/ `dependencies.py`（require_user）/ `cli.py`（用户管理） |
| [backend/scrapers/](backend/scrapers/) | 三大基类 + `novels/` `dramas/` 子类，详见 add-scraper skill |
| [backend/scrapers/__init__.py](backend/scrapers/__init__.py) | `SCRAPER_REGISTRY` / `DRAMA_SCRAPER_REGISTRY` 注册位置 |
| [backend/services/scheduler.py](backend/services/scheduler.py) | APScheduler 定时任务的**唯一**注册位置 |
| [backend/services/keyword_extractor.py](backend/services/keyword_extractor.py) | 仅英语 `extract_keywords`，其他语种返回 None |
| [frontend/src/App.jsx](frontend/src/App.jsx) | 顶层 Auth Gate + Dashboard（React 18 + Vite + Tailwind） |
| [frontend/src/api/client.js](frontend/src/api/client.js) | 前端唯一 HTTP 客户端（`credentials: 'include'` + 401 拦截） |
| [frontend/src/hooks/useAuth.js](frontend/src/hooks/useAuth.js) / [components/LoginPage.jsx](frontend/src/components/LoginPage.jsx) | 全局鉴权 hook + 登录页 |
| [docker-compose.yml](docker-compose.yml) / [docker-compose.dev.yml](docker-compose.dev.yml) / [Caddyfile](Caddyfile) | 生产 compose（Caddy→nginx→backend→**clickhouse 同栈**）/ 本地 dev override / Caddy HTTPS 配置 |
| [.env.production.example](.env.production.example) | 上云所需环境变量样例（JWT_SECRET / AUTH_USERS / DOMAIN / CLICKHOUSE_PASSWORD 等） |
| [deploy.sh](deploy.sh) | 服务器一键运维脚本（up / down / restart / logs / status / update / secret） |
| **`zhangwan-ui/`** | ⚠️ **独立 Vue 3 设计系统资源，与本项目无关，禁止改动** |
| [run_wattpad_keywords.py](run_wattpad_keywords.py) | 一次性脚本（关键词回填），不是定时任务；连接信息走环境变量，缺失会 fail-fast |
| [启动.bat](启动.bat) | Windows 一键启动后端 + 前端（轮询端口 + 自动 npm install） |

---

## 3. 常用命令

```bash
# 一键启动（Windows）
./启动.bat

# 手动启动
cd backend && python -m uvicorn main:app --port 8000
cd frontend && npm run dev

# Playwright 首次需要装浏览器
python -m playwright install chromium

# 触发爬虫
curl -XPOST localhost:8000/api/scrape         -d '{"platform":"wattpad","limit":50}'
curl -XPOST localhost:8000/api/dramas/scrape  -d '{"platform":"shortdrama_top5","limit":25}'

# API 文档
open http://localhost:8000/docs
```

---

## 4. ⚠️ 必须遵守的硬约束

> 这里列的都是 README 没写、但代码里强制成立的契约。违反会污染 GHI、丢数据、或破坏并发。

1. **数据缺失统一返回 `None`**，禁止用 `0` / `""` 占位 — 会被 GHI 当真实值参与排名。`base_scraper._safe_int_or_none()` 已封装好。
2. **小说 → `novels` 表 / 短剧 → `dramas` 表，禁止混表**。
3. **GHI 在 ClickHouse SQL 内计算**，前端只做展示。不要在 React 里重算分数。
4. **新增 ClickHouse 字段必须四处同步**：[`database.py`](backend/database.py) 的 DDL + `_MIGRATE_SQL` + `_INSERT_COLUMNS`(或 `_DRAMA_INSERT_COLUMNS`) + [`models.py`](backend/models.py)。漏一处就会整批写入失败。
5. **scraper 必须继承三件套之一**：`BaseHttpScraper` / `BasePlaywrightScraper` / `BaseShortDramaScraper`。**禁止** scraper 里直接 `requests.get()` —— 会丢失重试和代理回退。
6. **scraper 只 `return list[dict]`**，不直接连 ClickHouse；写入由 `services/*scraper_service.py` 负责。
7. **ClickHouse 客户端必须 `autogenerate_session_id=False`**，并发请求每次用 `database.get_client()` 取独立 client，不要做模块级单例。
8. **Playwright 浏览器生命周期由 `BasePlaywrightScraper.scrape()` 管理**，子类如需二次抓取（章节正文等），必须覆盖 `_enrich_results(context, results)` 复用已打开的 `BrowserContext`。
9. **`_calc_s_adapt` 阈值 / `_S_TAGS` / `_A_TAGS`** 在 [`base_scraper.py`](backend/scrapers/base_scraper.py)，改动会直接影响 GHI 排名 — 先和用户确认再动。
10. **真实数据库密码 / `.env` 内容**禁止写进任何文档或提交到仓库。
11. **新业务 router 必须挂在 `Depends(require_user)` 下**（[`backend/main.py`](backend/main.py) 用 `_protected` 列表统一注入），裸出业务接口等同 P0 故障。
12. **JWT_SECRET 不能为空**：[`backend/main.py`](backend/main.py) 启动时 fail-fast；本地用 `openssl rand -hex 32` 生成写入 `backend/.env`。
13. **`COOKIE_SECURE` 必须与传输协议匹配**：HTTPS=true，HTTP=false。改一边记得改另一边的 `.env`，否则浏览器拒种 cookie，登录后立即被推回登录页。
14. **bcrypt 用 `auth.password.hash_password`**，不要直接调 `bcrypt.hashpw`（已封装 72 字节截断与失败兜底；passlib 与 bcrypt 5.x 不兼容，故未引入 passlib）。
15. **SQLite 用户库 `auth_users.db` 不进仓库**（`.gitignore` 已排除），生产容器挂在 `/data` 持久卷。
16. **自助注册仅在 `AUTH_BACKEND=sqlite` 且 `REGISTRATION_CODE` 非空时启用**。`POST /api/auth/register` 同时校验：邀请码精确匹配、用户名 `^[A-Za-z0-9_]{3,32}$`、密码 ≥6 位、用户名未被占用；成功后直接种 cookie 自动登录。前端通过 `GET /api/auth/config` 决定是否展示注册入口。
17. **`REGISTRATION_CODE` 视同生产秘密**，禁止写进文档 / 仓库 / 默认 example；改邀请码立即作废历史邀请。
18. **后端 Dockerfile 镜像源**（apt → mirrors.aliyun.com / pip → 阿里云 / Playwright → npmmirror）是**国内 ECS 构建必需**，删掉等于让构建从 10 分钟变 7 小时。海外服务器构建可临时还原，但 PR 不要合回主分支。
19. **Skill 索引**只列入口（详细流程在 SKILL.md 内）；新增项目级 skill 在 [.claude/skills/](.claude/skills/) 下建子目录，不要塞 `.claude/settings.local.json`（用户私有，已 gitignore）。
20. **任何配置/凭据相关文件改动后**走完[`project-hardening` skill](.claude/skills/project-hardening/SKILL.md) 的 Step 1 secrets 扫描再 push，避免泄密。

---

## 5. 数据契约速查

字段语义以 [`backend/database.py`](backend/database.py) 顶部 DDL 注释为准。下面只列爬虫端必须填齐的字段。

### NovelRow（`_make_row` 已自动注入 `platform/lang/s_adapt/top_keywords`）

| 字段 | 类型 | 缺失值规则 |
|------|------|------------|
| `title` | `str` | 原文不翻译，必填 |
| `summary` | `str` | 缺失填空串 `""` |
| `tags` | `list[str]` | 统一小写 |
| `views` | `int \| None` | **抓不到必须 None** |
| `likes` | `int \| None` | **抓不到必须 None** |
| `original_url` | `str` | 必填 |
| `rank_type` | `str` | `daily` / `weekly` / `monthly` / 空串 |
| `top_keywords` | `dict[str,int] \| None` | 仅英语，其他语种保持 None |

### DramaRow

| 字段 | 类型 | 缺失值规则 |
|------|------|------------|
| `title` / `platform` / `source_url` | `str` | 必填 |
| `summary` / `cover_url` | `str` | 缺失填 `""` |
| `tags` | `list[str]` | 详情页补全见 `_enrich_items_from_detail_pages` |
| `episodes` | `int \| None` | 解析不到 None |
| `rank_in_platform` | `int` | 1 起 |
| `heat_score` | `float` | 由名次换算（聚合层会算） |
| `rank_type` | `str` | `轮播推荐` / `推荐栏位` / `最近上新` |
| `crawl_date` | `date` | 当天 |

---

## 6. Skill 索引

- **新增爬虫 / 接入新平台** → 必读 [.claude/skills/add-scraper/SKILL.md](.claude/skills/add-scraper/SKILL.md)
- **架构审计 / 加固 / 防泄密**（**通用，可移植到任何项目**）→ [.claude/skills/project-hardening/SKILL.md](.claude/skills/project-hardening/SKILL.md)

后续如需新增"前端组件规范 / SQL 查询规范 / GHI 调整"等 skill，在此追加一行指针即可。

---

## 7. 协作约定

- 探索性问题（"怎么改 X 比较好"）先给 2–3 句建议，待用户确认再动手。
- 改动多文件时优先 Edit 已有文件，避免新建。
- 不主动写 README/文档，除非用户明说。
- 任何破坏性操作（删表、reset --hard、force push）先确认。
