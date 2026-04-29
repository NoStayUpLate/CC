---
name: add-scraper
description: |
  【爬虫 / Scraper / Crawler 专用】在 backend/scrapers 下新增"小说 novels"或"短剧 dramas"数据抓取爬虫的标准架构与落地流程。
  触发关键词（任一命中即激活）：
    中文 — 爬虫、抓取、采集、爬一下、扒数据、抓数据、写个爬虫、加爬虫、新增爬虫、接入平台、扩展数据源、补一个站点、加一个小说站、加一个短剧站、新数据源、爬 XX、抓 XX
    英文 — scraper, crawler, spider, scrape, crawl, fetch site, ingest source, add scraper, new platform, data source
    站点示例 — wattpad / royal_road / syosetu / kakuyomu / inkitt / webnovel / netshort / shortmax / reelshort / dramabox / dramawave / dramareels / goodshort / moboreels / 任意"小说/短剧"平台名
  作用：强制沿用 BaseHttpScraper / BasePlaywrightScraper / BaseShortDramaScraper 三段式架构，注册到 SCRAPER_REGISTRY 或 DRAMA_SCRAPER_REGISTRY，字段对齐 ClickHouse novels / dramas 表，避免私造结构、绕过基类直连 requests、或忘改 DDL/迁移。
---

# 新增数据爬虫的标准流程

本项目所有"数据抓取"统一遵循下述三段式架构。当用户要求新增/扩展爬虫时，必须按本流程执行；不得绕过基类、不得私自定义返回结构、不得直接写 ClickHouse。

---

## 0. 触发场景识别

只要请求满足以下任一条件，即按本 skill 执行：

- 新增"小说类"数据源 → 走 **novels 流水线**（写入 `novels` 表）
- 新增"短剧/视频类"数据源 → 走 **dramas 流水线**（写入 `dramas` 表）
- 改造已有 scraper 但新增字段或榜单类型 → 仍沿用本架构，但要走第 5 节的迁移检查
- 用户口头要求"补一个站点"、"再加一个平台"、"扩展数据源"

如果用户给的是非 novels/dramas 的全新数据域（例如评论、用户行为、广告库），**先停下确认**：是否需要新建一张 ClickHouse 表，再回到本 skill。

---

## 1. 架构概览（必须先读）

```
backend/scrapers/
├── base_scraper.py            # 抽象顶层：BaseScraper（platform/lang/_make_row/_calc_s_adapt）
├── base_http_scraper.py       # HTTP/REST API 系站点：_get_json / _get_html，重试 + 代理回退
├── base_playwright_scraper.py # JS 渲染系站点：浏览器生命周期 + _enrich_results 钩子
├── sites_config.py            # 平台总览（platform/lang/url/tech/status）
├── __init__.py                # 注册到 SCRAPER_REGISTRY 或 DRAMA_SCRAPER_REGISTRY
├── novels/                    # 小说类 scraper（每个平台一个文件）
│   ├── en_wattpad_scraper.py
│   ├── en_royal_road_scraper.py
│   └── ja_syosetu_scraper.py
└── dramas/                    # 短剧类 scraper
    ├── shortdrama_base.py            # 短剧专属基类，封装栏位解析/标签清洗/详情补全
    ├── en_netshort_scraper.py        # 子平台 scraper
    ├── en_dramabox_scraper.py
    └── en_shortdrama_top5_scraper.py # 聚合调度器，写入 dramas 表
```

服务层：

- `services/scraper_service.py`     → novels 后台任务 + 分批写入 `batch_insert_async`
- `services/drama_scraper_service.py` → dramas 后台任务 + `batch_insert_dramas_async` + `OPTIMIZE FINAL`
- `services/scheduler.py`           → APScheduler 定时调度（按 daily/weekly/monthly 注册）
- `services/keyword_extractor.py`   → 仅英语 `extract_keywords(text, lang='en')`，其他语种返回 `None`

存储层：

- `database.py` → `batch_insert` / `batch_insert_dramas` / DDL + 迁移
- 字段顺序由 `_INSERT_COLUMNS` / `_DRAMA_INSERT_COLUMNS` 决定，**改动字段必须同时改 DDL、迁移 SQL、INSERT 列表与 models.py**

---

## 2. 决策树：选哪个基类？

```
能否拿到公开 REST/JSON 接口（无需 JS 渲染）？
├── 是 → 继承 BaseHttpScraper
│        - 异步 _get_json / _get_html
│        - 自动重试 3 次，代理握手失败自动回退直连
│        - User-Agent 自动随机
│        - 适用：Wattpad、所有短剧平台（HTML SSR）
│
└── 否（页面靠 JS 异步注入数据）
         → 继承 BasePlaywrightScraper
         - 自动管理 chromium 生命周期、注入反检测脚本、屏蔽图片
         - 必须实现 build_url(genre, page) + _scrape_page(page, genre, limit)
         - 列表抓完后可覆盖 _enrich_results(context, results) 做章节正文抓取
         - 适用：Royal Road、Syosetu

短剧站点是 HTML SSR，但需要"栏位/标签清洗/详情补全"
         → 继承 BaseShortDramaScraper（底层仍是 BaseHttpScraper）
         - 复用 _parse_section_by_headings / _enrich_items_from_detail_pages
         - 公共标签清洗规则集中在 SECTION_BLACKLIST / SECTION_LABEL_MAP
```

不要新建第四种基类。**如果新站点形态实在无法套用，先在对话里和用户对齐再扩 base**。

---

## 3. 文件命名与位置

| 类型 | 目录 | 文件名格式 | 示例 |
|------|------|------------|------|
| 小说 | `backend/scrapers/novels/` | `{lang}_{platform}_scraper.py` | `en_wattpad_scraper.py` / `ja_syosetu_scraper.py` |
| 短剧 | `backend/scrapers/dramas/` | `{lang}_{platform}_scraper.py` | `en_netshort_scraper.py` |
| 类名 | — | `{Platform}Scraper`（驼峰） | `WattpadScraper` / `NetShortScraper` |

`platform` 字段必须与 `sites_config.py` 中登记的字符串一致，且全小写下划线（如 `royal_road`、`naver_series`）。

---

## 4. 五步落地清单（每次新增爬虫都必须做齐）

### Step 1 — 在 `sites_config.py` 注册站点

新增一项：

```python
{
    "platform": "platform_xx",
    "lang": "en",                 # ISO 639-1
    "name": "Display Name",
    "url": "https://xxx/",
    "tech": "http_api",          # 或 "playwright"
    "status": "pending",         # 实现完成后改为 "done"
},
```

### Step 2 — 写 scraper 文件

最小骨架（HTTP 系，小说类）：

```python
"""
{Platform} 爬虫（{lang} 市场）。

接入方式 / 关键页面 / robots.txt 备注 / 反爬注意点写在 docstring 顶部，
后人维护时第一眼就能看到。
"""
import logging
from ..base_http_scraper import BaseHttpScraper
from services.keyword_extractor import extract_keywords

logger = logging.getLogger(__name__)


class XxxScraper(BaseHttpScraper):
    platform = "platform_xx"
    lang = "en"

    def build_url(self, genre: str = "", page: int = 1) -> str:
        ...

    async def scrape(self, genre: str = "", limit: int = 50) -> list[dict]:
        results: list[dict] = []
        page = 1
        while len(results) < limit and page <= 5:
            data = await self._get_json(self.build_url(genre, page))
            ...
            results.append(self._make_row(
                title=..., summary=..., tags=[...],
                views=int_or_none, likes=int_or_none,
                original_url=..., rank_type="weekly",
            ))
            page += 1

        # 关键词扩充（英语才有效）
        for row in results:
            try:
                row["top_keywords"] = await self._fetch_chapter_keywords(...)
            except Exception:
                pass  # 保持 None，禁止造数

        return results[:limit]
```

Playwright 系（小说类）只实现 `build_url()` + `_scrape_page()` 两个抽象方法即可；翻页与浏览器生命周期由基类完成。如需抓章节正文做关键词提取，覆盖 `_enrich_results(context, results)`，复用已打开的 `BrowserContext`。

短剧系继承 `BaseShortDramaScraper`，参考 `en_netshort_scraper.py` 的 `_parse_homepage` + `_enrich_items_from_detail_pages` 双段式；记得设置类属性：

```python
platform = "platform_xx"
lang = "en"
list_url = "https://xxx.com/"
section_limit = 10
section_order = ["轮播推荐", "推荐栏位", "最近上新"]
```

### Step 3 — 注册到 REGISTRY

编辑 `backend/scrapers/__init__.py`：

- 小说类 → 加入 `SCRAPER_REGISTRY`，key 即 `platform`；如果同一个类要按榜单类型分多个 key，用 `partial(Cls, rank_type=...)`（参考 `syosetu_daily/weekly/monthly`）
- 短剧类 → 加入 `DRAMA_SCRAPER_REGISTRY`，并把新平台加到 `dramas/en_shortdrama_top5_scraper.py` 的 `_PLATFORM_SCRAPERS` 列表里

同时更新 `__all__`。

### Step 4 — 字段对齐 + 数据契约

**小说行**（`_make_row` 已自动注入 `platform/lang/s_adapt/top_keywords`）必须包含：

| 字段 | 类型 | 规则 |
|------|------|------|
| `title` | `str` | 原文不翻译 |
| `summary` | `str` | 原文，缺失填空串 `""` |
| `tags` | `list[str]` | 统一小写；`s_adapt` 由 `_calc_s_adapt(tags)` 计算 |
| `views` | `int \| None` | **抓不到必须 None**，禁止 0 填充 |
| `likes` | `int \| None` | 同上 |
| `original_url` | `str` | 必填，用于跳转/去重 |
| `rank_type` | `str` | `daily/weekly/monthly` 或空串 |
| `top_keywords` | `dict[str,int] \| None` | 仅英语，其他语种保持 None |

**短剧行**必须包含：`title / summary / cover_url / tags / episodes / rank_in_platform / heat_score / platform / lang / rank_type / crawl_date / source_url`，参考 `en_shortdrama_top5_scraper.py` 的最终装配段。

**禁止**:
- 自造新字段而不同步更新 `database.py` 的 INSERT 列表与 `models.py`
- 用 `0` 替代缺失数值（`_safe_int_or_none` 会返回 None）
- 把日语/韩语正文塞给 `extract_keywords`（会返回 None，反而省事）

### Step 5 — 调度与触发

- API 触发：`POST /api/scrape  body={"platform":"platform_xx","genre":"","limit":50}`，进度查 `GET /api/scrape/{task_id}`
- 定时触发：在 `services/scheduler.py` 的 `_DAILY_PLATFORMS` / `_weekly_job` / `_monthly_job` 中追加新 platform key
- 写入由 `services/scraper_service.run_scrape_task` 自动按 `settings.scraper_batch_size` 分批；短剧走 `drama_scraper_service.run_scrape_task` 并在收尾触发 `OPTIMIZE TABLE dramas FINAL`

---

## 5. 必须避免的典型错误

1. **绕过基类直接 `requests.get`** → 失去重试与代理回退；必须用 `self._get_html / self._get_json`。
2. **在 scraper 里直接连 ClickHouse** → 写入是服务层职责；scraper 只 return `list[dict]`。
3. **用 0 / 空字符串伪装缺失值** → 触发 GHI 算法误判；按"不造假原则"返回 None。
4. **新增 ClickHouse 字段忘了同步迁移** → 必须同时更新：DDL、`_MIGRATE_SQL`、`_INSERT_COLUMNS`、`models.py`、`router` 输出模型。
5. **Playwright 子类自己管浏览器** → 浏览器由 `BasePlaywrightScraper.scrape()` 统一打开/关闭；二次抓取必须走 `_enrich_results` 钩子，复用 `context`。
6. **修改 `_calc_s_adapt` 阈值** → 这是 GHI 的预计算字段，改动会影响排名；必须先和用户确认再动 `base_scraper.py` 的 `_S_TAGS / _A_TAGS`。
7. **短剧 scraper 漏挂详情页补全** → `tags`/`summary`/`cover_url` 会大面积为空；用 `_enrich_items_from_detail_pages` 兜底。
8. **`platform` 字符串两处不一致**（`sites_config.py` ↔ class attr ↔ REGISTRY key）→ 任务无法路由到正确的 scraper。

---

## 6. 提交前自检清单

每完成一个新爬虫，逐条核对：

- [ ] `sites_config.py` 已登记新平台，`status` 改为 `done`
- [ ] scraper 类继承自 `BaseHttpScraper` / `BasePlaywrightScraper` / `BaseShortDramaScraper` 三者之一
- [ ] `platform` / `lang` 类属性与配置一致，且 platform 全小写下划线
- [ ] 文件 docstring 写明：目标 URL、关键 selector、robots.txt 备注、反爬注意点
- [ ] 缺失数值返回 `None`，不用 0 占位
- [ ] 注册到 `SCRAPER_REGISTRY` 或 `DRAMA_SCRAPER_REGISTRY`，并加入 `__all__`
- [ ] 短剧场景：已加入 `_PLATFORM_SCRAPERS` 聚合列表
- [ ] 如新增字段：同步改 `database.py` DDL + `_MIGRATE_SQL` + INSERT 列表 + `models.py`
- [ ] 如需周期性抓取：在 `services/scheduler.py` 注册到对应 job
- [ ] 本地手动跑一次：`POST /api/scrape` 或 `python run_wattpad_keywords.py` 同款脚本，确认 `inserted > 0`、ClickHouse 内可查到新行
