# 罗盘 · 海外内容监测看板 · 系统说明

> 给评审人员的速读材料 —— 5 分钟看懂这套系统**做什么、怎么实现、对业务价值多大**。
> 详细工程说明见 [README.md](../README.md) 与 [CLAUDE.md](../CLAUDE.md)。

---

## 1. 系统定位（一句话）

**面向 AI 短剧团队的"题材选品 + 平台对标"决策工具**：自动监测海外 8 大短剧平台 + 3 大小说平台的热门内容，用 GHI 算法量化"哪些题材最值得改编"，让团队从"凭感觉选题"变成"看数据选题"。

业务闭环：
```
海外原作（爬虫监测） → 题材打分（GHI 算法） → 短剧表现验证（栏位榜单） → 反向指导团队选品
```

---

## 2. GHI 算法（核心 IP）

GHI = **G**lobal **H**eat **I**ndex（全球热度指数），用于量化一部海外小说被改编为 AI 短剧的潜力。

### 2.1 公式

```
GHI = S_popular × 0.30  +  S_engage × 0.30  +  S_adapt × 0.40
```

| 分项 | 含义 | 计算逻辑 | 算的位置 |
|------|------|----------|----------|
| **S_popular** | 流量分（人气广度） | `log10(views + 1) × 10`，上限 100。对数避免头部碾压 | ClickHouse SQL |
| **S_engage** | 粘性分（点赞 / 阅读） | `likes/views × 100 × 语种系数`，上限 100。系数：韩语 ×1.2、英语 ×0.8（韩语点赞文化更克制） | ClickHouse SQL |
| **S_adapt** | 改编适配分（题材契合度） | 爬虫端按标签预计算：S 级标签（狼人 / 重生 / 复仇 / 恶役千金）→ 90+；A 级 → 70-89；无标签默认 50 | Python 爬虫 |

权重 30/30/40 倾向 **S_adapt**，因为改编公司更在意"能不能改"而不是"原作多火"。详细算法引用：[backend/routers/novels.py:42-69](../backend/routers/novels.py#L42-L69)。

### 2.2 黄金三秒钩子（has_hook）

并行的二元判定：标题或简介命中 `reborn / revenge / villainess / transmigrat / abandoned / ...` 等词就标记为「黄金三秒」。短剧首集开头三秒决定留存，钩子词命中率与转化率强相关。

### 2.3 短剧侧的 heat_score

短剧表 `dramas` 不算 GHI（无 views/likes 数据），用 **heat_score** 替代：按平台榜单名次线性换算 `100 - (rank - 1) × 8`。配合栏位类型（轮播 / 推荐 / 上新）二维定位「哪个平台的哪个栏位最容易出爆款」。

---

## 3. 监测的平台与内容

### 3.1 海外短剧（8 平台聚合，1 个调度入口）

| 平台 | 标识符 | 抓取栏位 |
|------|--------|----------|
| NetShort | `netshort` | 轮播推荐 / 推荐栏位 / 最近上新 |
| ShortMax | `shortmax` | 推荐栏位 / 最近上新 / 近期热门 |
| ReelShort | `reelshort` | 最近上新 |
| DramaBox | `dramabox` | 顶部推荐 / 推荐栏位 / 近期热门 |
| DramaReels | `dramareels` | 轮播推荐 / 推荐栏位 / 最近上新 |
| DramaWave | `dramawave` | 轮播推荐 / 推荐栏位 / 最近上新 |
| GoodShort | `goodshort` | 近期热门 / 推荐栏位 / 热门榜单 / 当前热门 |
| MoboReels | `moboreels` | 近期热门 / 推荐栏位 / 最近上新 |

调度统一走 [`ShortDramaTop5Scraper`](../backend/scrapers/dramas/en_shortdrama_top5_scraper.py)：一次调用同时抓 8 个平台、按平台名次线性赋予 heat_score。

**抓取字段**：标题 / 简介 / 封面 / 题材标签 / 集数 / 平台内名次 / 热度分 / 栏位类型 / 抓取日期 / 来源 URL。

### 3.2 海外小说（3 平台）

| 平台 | 抓取方式 | 频率 |
|------|---------|------|
| **Wattpad**（英语） | 公开 REST API | 触发式 + APScheduler 周榜 |
| **Royal Road**（英语） | SSR HTML 解析 | 周榜 |
| **Syosetu**（日语） | 日榜 / 周榜 / 月榜 | 三档定时 |

**抓取字段**：标题 / 简介 / 题材标签 / 阅读量 / 点赞 / 原作 URL / 平台 / 语种 / 榜单类型 / **前三章高频关键词词频（仅英语）** —— 后者用于做关键词云。

### 3.3 数据缺失契约

凡是平台未公开或抓取失败的数值字段，**统一返回 `None`**，禁止用 0 占位 —— 否则会污染 GHI 排名。这是工程纪律，也是数据可信度的根基。

---

## 4. 代码架构（4 层）

```
┌─────────────────────────────────────────────────────────────┐
│  React + Vite + Tailwind                  ← 前端展示层      │
│  · Auth Gate / 双 Tab 切换 / 可视化罗盘   · ~12 个组件      │
├─────────────────────────────────────────────────────────────┤
│  FastAPI + APScheduler + Pydantic         ← 后端 API 层    │
│  · /api/novels  /api/dramas  /api/scrape  · JWT + bcrypt    │
├─────────────────────────────────────────────────────────────┤
│  ClickHouse (novels / dramas 双表)        ← 存储 + 计算层  │
│  · GHI 在 SQL 内算，前端零计算            · 列式存储压缩高 │
├─────────────────────────────────────────────────────────────┤
│  BaseHttpScraper / BasePlaywrightScraper  ← 爬虫抽象层      │
│  · 三件套基类 + 子类实现                  · 注册表自动发现 │
└─────────────────────────────────────────────────────────────┘
```

### 4.1 关键设计

- **GHI 算 SQL 不算 JS**：算法在 [`backend/routers/novels.py:42-69`](../backend/routers/novels.py#L42-L69)，前端只做字段映射展示。算法迭代不需要重发前端。
- **爬虫三件套**：HTTP 系 / Playwright 系 / 短剧专用基类（[backend/scrapers/](../backend/scrapers/)）—— 子类只关心「URL 怎么拼」「HTML 怎么解析」，重试 / 代理回退 / 浏览器生命周期都在基类。**新增一个平台只需 ~50 行子类代码**。
- **批量写入幂等**：ClickHouse `ReplacingMergeTree` 引擎 + `(platform, title)` 去重键，重复抓取自动合并。
- **鉴权可插拔**：File 后端（环境变量直读）/ SQLite 后端（动态注册），代码同一份接口（[backend/auth/backends.py](../backend/auth/backends.py)）。
- **可视化罗盘前端纯算**：当前筛选条件下的 KPI / 平台分布 / 标签热度散点 / TOP 榜单全部在浏览器算，零额外后端聚合查询，分页拉满后 useMemo 派生（[frontend/src/components/DramaInsights.jsx](../frontend/src/components/DramaInsights.jsx)）。

### 4.2 关键路径速查

| 关注点 | 入口文件 |
|--------|---------|
| FastAPI 启动 + 路由注册 | [backend/main.py](../backend/main.py) |
| GHI 算法 SQL | [backend/routers/novels.py](../backend/routers/novels.py) |
| 短剧 8 平台调度 | [backend/scrapers/dramas/en_shortdrama_top5_scraper.py](../backend/scrapers/dramas/en_shortdrama_top5_scraper.py) |
| 表结构 + 迁移 + 批量写入 | [backend/database.py](../backend/database.py) |
| 定时任务（日 / 周 / 月榜） | [backend/services/scheduler.py](../backend/services/scheduler.py) |
| 前端主入口 + 鉴权门 | [frontend/src/App.jsx](../frontend/src/App.jsx) |
| 短剧选品罗盘可视化 | [frontend/src/components/DramaInsights.jsx](../frontend/src/components/DramaInsights.jsx) |

### 4.3 部署

Docker Compose 同栈部署 4 个容器：Caddy（反代 + LE 证书） / nginx + React 静态文件 / FastAPI 后端 / ClickHouse 数据库。一键运维入口 [`./deploy.sh`](../deploy.sh) 子命令：`up / down / restart / status / logs / update / secret`。

`./deploy.sh update` = 拉新代码 + 重建镜像 + 平滑重启 + 清理悬挂镜像，整个流程一气呵成。

---

## 5. 业务价值（评估视角）

### 5.1 解决了什么问题

| 痛点 | 看板带来的改变 |
|------|---------------|
| 选题靠拍脑袋 / 抄爆款，撞车率高 | GHI 量化打分 + 标签热度散点把「蓝海机会 / 热门赛道 / 红海拥挤」可视化分区 |
| 跨 8 个平台手工逛榜，每天耗 1-2 小时 | 一键聚合抓取，10 分钟覆盖全平台 TOP 榜单 |
| 拍完不知该投哪个平台的哪个栏位 | 「平台 × 栏位 热力图」直接告诉你哪个组合最容易出爆款 |
| 海外小说改编选 IP 无依据 | S_adapt 标签匹配 + has_hook 钩子词检测，先筛后看 |

### 5.2 量化对比

- **选品效率**：1-2 小时手工调研 → **10 分钟看罗盘**
- **数据覆盖**：单平台肉眼浏览 → **8 个海外短剧平台 + 3 个海外小说平台同栈聚合**
- **决策依据**：经验直觉 → **GHI 三维加权 + 标签四象限定位**

---

## 6. 易用性（操作流程）

### 6.1 看板使用（业务侧）

1. 登录（邀请码注册 / 管理员开账号）
2. 进「海外短剧检测」 / 「海外小说检测」 双 Tab
3. **筛选** 平台 / 语种 / 栏位 / 标签 / 关键词
4. 看 **可视化罗盘**：数据概览（KPI + 分布）/ 趋势洞察（标签散点 + 平台栏位热力）/ 表现榜单（TOP20 横向条形）
5. 点条目进详情页 —— 看简介、标签、原站链接

### 6.2 运维使用（技术侧）

```bash
# 服务器
./deploy.sh status          # 看状态
./deploy.sh logs backend    # 跟日志
./deploy.sh update          # 拉新代码 + 一键升级

# 本地
./启动.bat                  # Windows 一键起后端 + 前端
```

### 6.3 扩展使用（开发侧）

新增一个短剧平台抓取：
1. `backend/scrapers/dramas/` 下新建 `en_xxx_scraper.py`，继承 `BaseShortDramaScraper`
2. 实现 `scrape()` 方法（约 50 行）
3. 在 `__init__.py` 的 `DRAMA_SCRAPER_REGISTRY` 注册
4. 走 [.claude/skills/add-scraper](../.claude/skills/add-scraper/SKILL.md) skill 的 6 步检查表确认数据契约
5. 重启即生效

---

## 7. 工程亮点（评审参考）

| 维度 | 体现 |
|------|------|
| 架构清晰度 | 4 层分明、爬虫三件套基类、注册表自动发现 |
| 数据严谨性 | 缺失统一 `None`、ClickHouse 强类型 + 字段注释、新字段四处同步契约 |
| 算法可解释性 | GHI 三分项分别可见，能解释「为什么这部排第一」 |
| 安全性 | JWT + bcrypt + HTTP-only cookie + fail-fast 启动校验，无明文凭据落库 |
| 可运维性 | 一键脚本 / 健康检查 / 镜像加速 / 国内 ECS 友好的构建优化 |
| 可观测性 | 前端 KPI 面板 / 日志按服务隔离 / 任务进度轮询 |
| 文档完备 | README.md（人类）+ CLAUDE.md（AI 工作手册）+ PRODUCTION.md（部署快照）+ 本说明 |

---

## 8. 当前状态与限制（透明披露）

- **已部署**：阿里云 ECS（境内节点），Docker Compose 同栈，HTTP 模式访问
- **已知限制**：境内节点出口受限，部分海外平台爬虫无法直连，目前用本地 dump 数据演示效果
- **后续路线**：换境外节点 → HTTPS + 域名 → 关键词抓取扩展（多语种）

完整状态见 [docs/PRODUCTION.md](PRODUCTION.md)。
