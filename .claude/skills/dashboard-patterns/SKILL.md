---
name: dashboard-patterns
description: |
  【React + Tailwind 看板设计模式】把一套筛选器 / 悬浮提示 / 折叠可视化 / 右侧抽屉 / 表格-分页-状态按钮 / 布局骨架的口径统一抽出，便于在本项目沿用、也便于复制到其他 React + Tailwind 项目。
  触发关键词（任一命中即激活）：
    中文 — 看板、仪表盘、Dashboard 改造、新增筛选器、做一个抽屉、侧拉框、悬浮提示、可视化折叠、新增数据看板、相似页面、筛选器样式、表格分页、状态按钮、设计 token
    英文 — dashboard pattern, build filters, multiselect filter, tooltip popover, side drawer, collapse visualization, data table pagination, status button, design tokens
  作用：在已有看板上扩展新页面 / 新筛选维度 / 新指标卡时，强制沿用同一套 className、动效时长、状态分层规则，避免每个新页面口径漂移。
---

# Dashboard 设计模式 — 一份 SKILL 复用 6+ 张看板的视觉与交互

> **设计目标**：让任何 React + Tailwind 项目都能照本 SKILL 一次性把筛选器 / Tooltip / 折叠可视化 / 抽屉 / 表格 / 状态按钮 / 布局骨架的口径对齐。
> **使用方式**：把整个 `dashboard-patterns/` 目录拷到目标项目的 `.claude/skills/` 下，跟着 §1 选模式即可。

---

## 0. 何时触发

满足以下任一情况就启动本 SKILL：

- 用户要求"加 / 改 / 抄一张看板页面"、"加一个筛选维度"、"加一个抽屉 / 侧拉框"
- 用户要求"统一一下样式"、"这两个页面看起来不一致"
- 用户在已有看板上"加 tooltip"、"加可视化折叠"、"加状态按钮"
- 新搭一个 React + Tailwind 数据看板项目，想要直接套现成模式

不要触发的场景：
- 用户问「写个组件」但与看板无关（一个孤立的表单 / 卡片秀）
- 用户改的是后端 / 爬虫 / 数据库（那是 `add-scraper` 的领域）

---

## 1. 适用范围（项目内 vs 可移植）

### 模式 A — 本项目内部使用

直接读 §3-§8 的「📁 本仓库参考」，**优先 import 现成组件**：

- 筛选器 → import `MultiSelectFilter` from `frontend/src/components/DropdownFilter.jsx`
- Tooltip 三角骨架 → 复制 `DhiInfoTooltip` 内的双层三角片段
- Modal 三件套 → 拷 `NovelModal` / `DramaModal` / `MobileSider` 改 props 即可
- Pagination / TriggerButton → 直接 import `App.jsx` 与 `ScrapeOverviewPage.jsx` 已导出的实现

避免重复造组件，本项目沿用现有 className 与 token。

### 模式 B — 可移植（其他 React + Tailwind 项目）

第一步：合并两份 snippet：

```
.claude/skills/dashboard-patterns/reference/tailwind.config.snippet.js
  → 合并到目标项目 tailwind.config.js → theme.extend.colors

.claude/skills/dashboard-patterns/reference/index.css.snippet.css
  → 合并到目标项目 src/index.css （已含 @layer base + components 段）
```

第二步：照 §3-§8 的「🧱 骨架」与「⚙️ 关键参数」自己实现组件（不会有现成 .jsx 给你拷，因为目标项目没有这些组件）。

第三步：跑 §10 的验证清单逐项打勾。

---

## 2. 起步 — Design Tokens（必备）

下面这些 token 是 §3-§8 所有 className 的底层依赖，**任何模式开工前先确认它们已就位**。

### 颜色 token

| Token | 值 | 角色 | 定义在 |
|------|----|----|------|
| `brand` | `#00BF8A` | 主绿（选中 / 强调 / 主按钮） | tailwind.config.js |
| `brand-light` | `#E6F9F3` | 浅绿（选中底 / 标签底） | tailwind.config.js |
| `brand-dark` | `#00A877` | 深绿（按钮 hover） | tailwind.config.js |
| `zw.border` | `rgb(242, 243, 245)` | 卡片 / 字段边 | tailwind.config.js |
| `#dcdfe6` | 硬编 | 下拉 / Tooltip 边 | inline className |
| `#f7f8fa` | 硬编 | 浅卡背景（公式框 / 空状态） | inline className |
| `#f2f3f5` | 硬编 | 表头条背景 | inline className |
| `#ebeef5` | 硬编 | 行分割 / 卡片描边 | inline className |

### CSS components

| Class | 用途 | 关键参数 |
|------|------|---------|
| `.zw-card` | 容器外壳 | `border-radius:2px; border:1px solid #ebeef5; padding:12px` |
| `.zw-field` | input / select / 多选触发器 | `height:28px; font-size:15px; border:1px solid #dcdfe6` |
| `.zw-primary-btn` | 主操作按钮 | brand 底，hover brand-dark，`font-size:15px` |
| `.zw-default-btn` | 次操作按钮 | 白底 + 描边，hover 变绿，`font-size:15px` |
| `.zw-chip` / `.zw-chip-active` | 小型快选标签 | 选中时 brand-light bg |

### 字号档位（已上调到 +4px 阅读舒适档）

| 工具类 | Tailwind 默认 | 本项目值 | 用途 |
|------|------|------|------|
| `text-xs` | 12px / 16px | **16px / 24px** | 表格 / 卡片正文（最常用） |
| `text-sm` | 14px / 20px | **18px / 26px** | 标题、过滤器 label、ResultCounter 总数文案 |
| `text-base / lg / xl / 2xl` | 16 / 18 / 20 / 24 | 不变 | 卡片标题、KPI 主值、Modal 标题 |
| `text-[11px]` | — | 11px（**保持不变**） | 芯片副字、徽章、灰色二级文本（刻意维持小一档形成层次） |
| body 基础 | 16px | **15px**（含 `line-height: 1.5`） | 任何无显式 text-* 的元素继承 |

⚠️ 注意：`text-xs` 现在等于 `text-base` 默认值（16px），`text-sm` 等于 `text-lg` 默认值（18px）。若需要明显的尺寸层级请直接用 `text-base / text-lg / text-xl`，不要依赖 sm/base 之间的视觉差异。

### Lucide 图标使用规约

```jsx
// 全站统一 size + strokeWidth，避免每个组件都不一致
<Icon size={12} strokeWidth={1.5} />   // 在 tooltip / chip / table 内
<Icon size={14} strokeWidth={1.7} />   // 在按钮 / tab / 折叠按钮
<Icon size={17} strokeWidth={1.8} />   // 在侧栏 NavItem
<Icon size={18} strokeWidth={1.7} />   // 在状态空态图标（TabEmpty）
```

📁 token 源：[frontend/tailwind.config.js](frontend/tailwind.config.js)、[frontend/src/index.css](frontend/src/index.css)

---

## 3. 布局骨架（侧栏 + 顶部 + 面包屑）

### 🎯 设计意图
固定左侧栏 + 顶部固定头 + 面包屑 + 主体可滚动的「工作台」式三段布局。移动端左侧栏退化为浮层。

### 🧱 骨架

```jsx
<div className="min-h-screen bg-[#e5e7eb] text-black">
  {/* 桌面侧栏：fixed + 仅在 md 以上展示 */}
  <aside className="fixed left-0 top-0 z-40 hidden md:flex
                    h-screen w-[160px] flex-col border-r border-[#ebeef5] bg-white">
    {/* logo + nav + footer */}
  </aside>

  {/* 主体：md 上 padding-left 让位给侧栏 */}
  <div className="min-h-screen md:pl-[160px]">
    {/* ⭐ 整页只有 <main> 一个滚动条；header / 面包屑都放在 main 内部，
       滚动时随内容上移消失，让位给表格的 sticky thead 真正贴在浏览器顶端。 */}
    <main className="h-screen overflow-y-auto bg-[#e5e7eb]">
      <header className="h-[50px] border-b border-[#ebeef5] bg-white">
        {/* 左：title + 标识；右：状态、用户 */}
      </header>
      <div className="flex h-9 items-center bg-[#f0eef6] px-3 text-xs text-black">
        {/* 面包屑 */}
      </div>
      <div className="space-y-3 p-3">
        {/* 主体内容 —— 表格/卡片网格等 */}
      </div>
    </main>
  </div>
</div>
```

### ⚙️ 关键参数

| 项 | 值 |
|---|---|
| 侧栏宽 | `w-[160px]`（中文 5 字标题不换行的最小宽度） |
| 顶部 header 高 | `h-[50px]`（**不 sticky**，跟内容一起滚走） |
| 面包屑条高 | `h-9`（**不 sticky**） |
| 主体可滚高 | `h-screen overflow-y-auto`（main 是唯一滚动条） |
| 移动端侧栏 | `MobileSider` 浮层 + `bg-black/30` 遮罩 |

### ⚠️ 禁令
- 侧栏宽不要小于 `w-[160px]`，否则 5 字中文标题（如「数据抓取概览」）会换行
- ⛔ **不要给 header 加 `sticky` 或 `fixed`** —— 长表格滚动时会挡住 sticky thead，违背"列名贴顶"的预期
- 不要把 header 放在 `<main>` **外部**，那样 header 和 main 是两个独立滚动上下文，header 永远不会跟着滚走
- main 必须是页面唯一的滚动容器（`overflow-y-auto h-screen`），sticky 子元素才能正确锚定到浏览器视口

### 📁 本仓库参考
[frontend/src/App.jsx](frontend/src/App.jsx) — `Dashboard` / `SiderContent` / `MobileSider` / `NavItem`

---

## 4. 筛选系统（FieldShell + MultiSelectFilter + 后端 CSV）

### 🎯 设计意图
所有筛选条件统一一行：左边 5em 灰色 label，右边可输入 / 选择控件。多选用 CSV 字符串穿透到后端，后端解析回 list 做参数化 IN 查询。

### 🧱 骨架

```jsx
// 1. FieldShell：所有筛选行的统一外壳
function FieldShell({ label, children }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <span className="w-[5em] flex-shrink-0 text-xs font-semibold text-black">{label}</span>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

// 2. MultiSelectFilter 触发器（核心）：
<button className="zw-field flex w-full items-center justify-between gap-2 pr-8 text-left">
  <span className="truncate text-black">
    {selected.length ? selectedLabels.join("、") : "全部"}
  </span>
</button>

// 右侧 hover-only 清空按钮（绝对定位）
<span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 ...">
  {showClear ? null : "∨"}
</span>
{showClear && (
  <button className="absolute right-2 top-1/2 -translate-y-1/2
                     flex h-4 w-4 items-center justify-center rounded-full
                     bg-slate-300 text-white hover:bg-slate-500 ...">
    <X size={10} strokeWidth={2.5} />
  </button>
)}

// 3. 下拉面板：选中项用 brand-light + brand 背景，附 ✓
<div className="absolute left-0 right-0 top-[calc(100%+4px)] z-30 max-h-64
                overflow-y-auto rounded-sm border border-[#dcdfe6] bg-white
                p-1 shadow-[0_8px_24px_rgba(15,23,42,0.10)]">
  <button className={selectedSet.has(val)
    ? "bg-brand-light text-brand"
    : "text-black hover:bg-slate-50"}>
    <span className="truncate">{label}</span>
    {selectedSet.has(val) && <span className="text-xs">✓</span>}
  </button>
</div>
```

### ⚙️ 关键参数

| 项 | 值 |
|---|---|
| value 格式 | 逗号 CSV 字符串 `"a,b,c"`（不是数组，便于序列化进 URL） |
| 选中分隔符 | 中文 `、` （join 时用，不是英文逗号） |
| 清空按钮触发 | `showClear = selected.length > 0 && hovering` |
| 触发器右侧 padding | `pr-8`（给 ∨ / ✕ 留 32px 空间） |
| 下拉 z-index | `z-30` |
| 选中态 | `bg-brand-light text-brand` |
| `allLabel` 默认 | `"全部"` |

### 级联清理（可选）

切换某个筛选维度后，把已选但已不再属于新合法集的「幽灵选中」静默剔除：

```jsx
// 例：平台变化后，rank_type 中不属于新平台并集的选项要被去掉
const handlePlatformChange = (value) => {
  onChange("platform", value);
  if (filters.rank_type) {
    const newAllowed = new Set(/* 新平台的并集 */);
    const cleaned = filters.rank_type
      .split(",").map((s) => s.trim()).filter((v) => newAllowed.has(v))
      .join(",");
    if (cleaned !== filters.rank_type) onChange("rank_type", cleaned);
  }
};
```

### 4.5 后端配套（**仅本仓库适用，便携模式忽略**）

```python
# backend 收到 ?platform=a,b&lang=en,ja → 拆 CSV → IN Array(String) 参数化查询
def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]

# WHERE platform IN {platforms:Array(String)} AND lang IN {langs:Array(String)}
# params = {"platforms": [...], "langs": [...]}
```

### ⚠️ 禁令
- 多选 join 用中文 `、` 不要用 `,`（避免和 CSV value 混淆）
- 清空按钮**不要**默认显示，必须 hover + 有选中两个条件同时满足才出现
- 后端 SQL 不要用字符串拼接 `IN (...)` —— 必须参数化 `Array(String)` 防注入

### 📁 本仓库参考
- [frontend/src/components/DropdownFilter.jsx](frontend/src/components/DropdownFilter.jsx) — `MultiSelectFilter` / `FieldShell`
- [frontend/src/components/DramaFilterBar.jsx](frontend/src/components/DramaFilterBar.jsx) — 级联示例
- [backend/routers/dramas.py](backend/routers/dramas.py) — `_split_csv` / `_build_where`

---

## 5. 悬浮提示（向上 + 双层三角）

### 🎯 设计意图
所有 hover 提示**统一向上展开**，弹窗底部带向下小三角指向触发器。透过 group-hover + 入场偏移营造软落感。

### 🧱 骨架

```jsx
<span className="relative inline-flex group">
  {/* 触发器（图标 / 标签 / +N 芯片） */}
  <span className="cursor-default group-hover:text-brand transition-colors">
    <Info size={12} strokeWidth={1.5} />
  </span>

  {/* 弹窗 —— 永远向上 */}
  <span className="invisible absolute left-1/2 -translate-x-1/2
                   bottom-[calc(100%+8px)] z-50
                   opacity-0 translate-y-1
                   group-hover:visible group-hover:opacity-100
                   group-hover:translate-y-0
                   transition-all duration-200
                   rounded-lg border border-[#dcdfe6] bg-white p-4
                   shadow-[0_12px_36px_rgba(15,23,42,0.12)]">
    {/* content */}

    {/* 向下双层三角（外灰边 + 内白填，-mt-px 错位 1px） */}
    <span aria-hidden className="pointer-events-none absolute left-1/2 -translate-x-1/2
                                  top-full h-0 w-0
                                  border-l-[7px] border-r-[7px] border-t-[7px]
                                  border-l-transparent border-r-transparent
                                  border-t-[#dcdfe6]" />
    <span aria-hidden className="pointer-events-none absolute left-1/2 -translate-x-1/2
                                  top-full -mt-px h-0 w-0
                                  border-l-[6px] border-r-[6px] border-t-[6px]
                                  border-l-transparent border-r-transparent
                                  border-t-white" />
  </span>
</span>
```

### ⚙️ 关键参数

| 项 | 值 |
|---|---|
| 入场动效 | `invisible opacity-0 translate-y-1` → `group-hover:visible group-hover:opacity-100 group-hover:translate-y-0` |
| 时长 | `transition-all duration-200`（与 tab 切换同节奏） |
| 与触发器距离 | `bottom-[calc(100%+8px)]` 或 `bottom-full mb-2` |
| 横向定位 | 窄弹窗 `left-1/2 -translate-x-1/2`；宽弹窗（>300px）用 `right-0` 防溢出右边界 |
| 三角外层 | 7px `border-t-[#dcdfe6]` |
| 三角内层 | 6px `border-t-white` + `-mt-px` 覆盖 |
| 阴影 | `shadow-[0_12px_36px_rgba(15,23,42,0.12)]`（弹窗）或 `shadow-[0_8px_24px_rgba(15,23,42,0.12)]`（小弹窗） |

### ⚠️ 禁令
- **不要向下展开**（`top-full mb-2` 是禁忌）—— 全站方向必须一致
- 不要省三角的内层（外层单层会有 1px gap，视觉「三角与卡片不连」）
- `pointer-events-none` 必须打在两层三角上，否则 hover 进入三角时会触发离场
- 触发器外层必须 `relative` + `group`，否则 group-hover 无效

### 🚨 特例：触发器位于 `overflow-hidden` 容器内（如表格 th）

如果触发器的祖先里有 `overflow-hidden` 或 `overflow-x-auto`（CSS 规范会让 Y 轴也变 auto-clip），CSS 默认的 `absolute bottom-full` 弹窗会被裁掉；如果再上层还有 `transform`/`translate-*`/`filter` 等创建 containing block 的属性，连 `position: fixed` 都会被收编。**典型场景：表格 thead 内的 ⓘ 提示**。

唯一干净解：用 **React Portal + state 驱动 hover**：

```jsx
import { createPortal } from "react-dom";
import { useLayoutEffect, useRef, useState } from "react";

function PortalTooltip() {
  const triggerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!open || !triggerRef.current) return;
    const r = triggerRef.current.getBoundingClientRect();
    setPos({ top: r.top, left: r.left + r.width / 2 });
  }, [open]);

  return (
    <>
      <span ref={triggerRef}
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={() => setOpen(false)}>
        <Info size={12} />
      </span>
      {open && createPortal(
        <div style={{
          position: "fixed",
          top: pos.top - 8,
          left: pos.left,
          transform: "translate(-50%, -100%)",
          zIndex: 100,
        }} className="w-[460px] ...">
          {/* tooltip 内容 + 双层三角 */}
        </div>,
        document.body
      )}
    </>
  );
}
```

判断要不要走 portal：
- 触发器在 `<table>` / `<thead>` / 任何 `overflow-hidden` 容器内 → **必须 portal**
- 触发器在普通 `zw-card` 或 `relative` 容器里 → 用上面 §5 主骨架 group-hover 即可

### 📁 本仓库参考
- [frontend/src/components/DramaTable.jsx](frontend/src/components/DramaTable.jsx) — `DhiInfoTooltip`（**portal 范本**：th 嵌入触发器 + 弹窗投到 body）
- [frontend/src/App.jsx](frontend/src/App.jsx) — `GhiInfoTooltip`（普通 group-hover）
- [frontend/src/components/ScrapeOverviewPage.jsx](frontend/src/components/ScrapeOverviewPage.jsx) — `RankTypeChips +N`（普通 group-hover）

---

## 6. 中部可视化（Tabs + 折叠 + Helper 组件）

### 🎯 设计意图
中部一块「Tab + 多图表」的复合展示区，支持整段折叠节省空间。点折叠时图表区塌；点 tab 时若处于折叠态自动展开。

### 🧱 骨架

```jsx
const TAB_DEFS = [
  { key: "overview", label: "数据概览", icon: LayoutDashboard },
  { key: "trend",    label: "趋势洞察", icon: Sparkles },
  { key: "ranking",  label: "表现榜单", icon: Trophy },
];

<div className="zw-card space-y-4">
  {/* 头部：tabs + 折叠按钮 */}
  <div className={`flex flex-wrap items-center gap-1
                   ${collapsed ? "" : "border-b border-[#ebeef5] pb-2"}`}>
    {TAB_DEFS.map((tab) => (
      <button onClick={() => { setActiveTab(tab.key); if (collapsed) setCollapsed(false); }}
              className={`inline-flex h-8 items-center gap-1.5 rounded px-3 text-xs transition-colors
                ${active
                  ? "bg-brand-light font-semibold text-brand"
                  : "text-black hover:bg-[#f5f7fa] hover:text-brand"}`}>
        <tab.icon size={14} strokeWidth={1.7} />
        {tab.label}
      </button>
    ))}
    <button onClick={() => setCollapsed((v) => !v)}
            className="ml-auto inline-flex h-8 items-center gap-1.5 rounded px-3
                       text-[11px] text-black hover:bg-[#f5f7fa] hover:text-brand">
      <span>{collapsed ? "展开" : "收起"}</span>
      {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
    </button>
  </div>

  {/* 内容：分层渲染 error → loading → empty → content */}
  {!collapsed && (
    <>
      {error && <TabError message={error} />}
      {!error && loading && rows.length === 0 && <TabSkeleton kind={activeTab} />}
      {!error && !loading && rows.length === 0 && <TabEmpty text="..." />}
      {!error && rows.length > 0 && activeTab === "overview" && <OverviewTab />}
      {/* ... */}
    </>
  )}
</div>
```

### Helper 组件（必备）

| 组件 | 签名 | 关键 className |
|------|------|---------------|
| `ChartBlock` | `({ title, hint, children })` | `rounded border border-[#ebeef5] bg-white p-3`；title `text-xs font-semibold`；hint `text-[11px] opacity-70` |
| `Kpi` | `({ label, value, suffix, tone })` | `rounded border border-[#ebeef5] bg-[#f7f8fa] px-4 py-3`；value `text-xl font-bold tabular-nums`；tone='primary' → `text-brand` |
| `ChartEmpty` | `()` | `flex h-40 items-center justify-center text-xs opacity-60` |
| `TabEmpty` | `({ text })` | `flex h-40 flex-col items-center justify-center bg-[#f7f8fa]` + 图标 |
| `TabError` | `({ message })` | `bg-red-50 border-red-200 text-red-700` |
| `TabSkeleton` | `({ kind })` | `h-16 / h-56 animate-pulse rounded bg-slate-100` 矩阵 |
| `KvTooltip` | Recharts content | `shadow-[0_8px_24px_rgba(15,23,42,0.12)]` |

### ⚙️ 关键参数

| 项 | 值 |
|---|---|
| Tab active | `bg-brand-light font-semibold text-brand` |
| Tab inactive hover | `hover:bg-[#f5f7fa] hover:text-brand` |
| 折叠时移除底边 | `${collapsed ? "" : "border-b border-[#ebeef5] pb-2"}` |
| 点 tab 自动展开 | `if (collapsed) setCollapsed(false)` |
| 状态优先级 | error > loading skeleton > empty > content |

### ⚠️ 禁令
- 折叠按钮文案是「收起 / 展开」，不要写「基于当前筛选下 N 条」之类的业务指标
- 状态分层不要漏 error 优先（loading 和 error 同时存在时，error 必须先显示）
- **Recharts Tooltip 必须关掉默认动画**（`isAnimationActive={false}` + `wrapperStyle={{ transition: "none" }}`），否则 hover 时 tooltip 会从图表左上角滑入到当前位置，体验极差。任何用了 `<Tooltip>` 的图表都要补上这两个 prop。

### 🚨 Recharts Tooltip「左上角飞入」问题

每个 `recharts/Tooltip` 默认会用 `transform` 动画从上一个位置过渡到当前 hover 点；首次渲染时上一个位置是 (0, 0)，所以视觉上是从图表左上角飞过来。修复 = 关掉动画 + 关掉 wrapper transition：

```jsx
<Tooltip
  isAnimationActive={false}
  wrapperStyle={{ transition: "none" }}
  cursor={{ fill: "rgba(0,191,138,0.08)" }}
  content={<KvTooltip ... />}
/>
```

只关 `isAnimationActive` 不够，因为 wrapperStyle 的 transition 是另外一层；只关 wrapperStyle 也不够，内部 Animate 组件还是会动。**两个都加**才彻底干净。

### 📁 本仓库参考
[frontend/src/components/DramaInsights.jsx](frontend/src/components/DramaInsights.jsx) — 完整三 tab + 折叠 + 7 个 helper 组件 + 4 处 Tooltip 都关掉了 fly-in 动画

---

## 7. 表格 + 分页 + 状态按钮

### 🎯 设计意图
紧凑型数据表（行高 12px ~ 60px）+ 永远显示总数的分页 + 4 态触发按钮（默认 / 抓取中 / 完成 / 失败）。

### 🧱 表格骨架

**核心原则**：thead 与 `<main>` 之间**不允许有任何 overflow 容器**（不管是 `overflow-hidden`、`overflow-x-auto` 还是 `overflow-y: clip`）。横向溢出由 `<main>` 自行处理（`<main>` 已经是 overflow-y-auto，规范会让 X 轴自动也变 auto，窄屏自然出现横滚）。

```jsx
{/* 外层 wrapper：只负责圆角 + 边 + 白底，无任何 overflow 属性 */}
<div className="rounded-sm border border-[#ebeef5] bg-white">
  {/* table 直接放在 wrapper 内，没有中间层 */}
  <table className="min-w-[1080px] w-full table-fixed text-left text-xs text-black">
    {/* ✅ sticky thead：滚动时表头始终粘在浏览器视口顶端
        z-20 < modal(50) / portal-tooltip(100) */}
    <thead className="sticky top-0 z-20 bg-[#f2f3f5] text-black shadow-[0_1px_0_#ebeef5]">
      <tr className="h-10">
        <th className="w-[220px] px-3 font-semibold">平台</th>
        {/* th 嵌入 Tooltip 示例 */}
        <th className="w-[90px] px-3 text-right font-semibold">
          <span className="inline-flex items-center justify-end gap-1">
            DHI
            <DhiInfoTooltip />
          </span>
        </th>
      </tr>
    </thead>
    <tbody>
      {rows.map((r) => (
        <tr className="border-b border-[#ebeef5] bg-white hover:bg-[#f7f8fa]">
          ...
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

### 🚨 sticky thead 的三大杀手（极其容易踩坑）

`position: sticky` 会沿着祖先链找最近的「滚动容器」作为粘附边界，并且任何祖先的 transform / overflow 都可能破坏这条链。下面三个陷阱**必须同时排查**，缺一会让 thead 滚不上去。

#### 杀手 ①：祖先的 `overflow-hidden` 截断 sticky

`overflow: hidden / auto / scroll` 都会**截断 sticky 的滚动上下文链**。如果表格外层卡片用了 `overflow-hidden`（很多人用它给 rounded 角兜底），thead 就被困在卡片内、无法贴浏览器顶端。

✅ 外层卡片只保留 `rounded-sm border bg-white`，**不要** `overflow-hidden`（`border-radius` 自己就能裁圆角）。

#### 杀手 ②：`overflow-x: auto` 隐式地把 Y 轴也变成 auto

最隐蔽：**单写 `overflow-x: auto` 时，CSS 规范会强行把 `overflow-y` 也设为 `auto`**（防止"X 滚 Y 不滚"的歧义）。所以一个普通的 `<div className="overflow-x-auto">` 会让 Y 轴也成为滚动上下文，把 sticky 困在里面。

理论上 `overflow-y: clip` 能解耦（`<div className="overflow-x-auto" style={{overflowY: "clip"}}>`），但实测在某些 Chromium 版本上 sticky 仍然失效 —— 一旦 thead 与 main 之间还有任何「会滚」的容器，行为就不可靠。

✅ **唯一稳妥的方案**：thead 与 `<main>` 之间**完全不要 overflow 容器**。横向溢出由 `<main>` 处理（`overflow-y-auto` 隐式让 X 也是 auto，窄屏自然出现整页横滚）。

❌ **常见错法**：
- `<div className="overflow-x-auto">` 想给表格加横滚 —— 会把 thead 困死
- `<div className="overflow-x-auto" style={{overflowY: "clip"}}>` —— Chromium 实测仍可能失效
- `<div className="overflow-x-auto overflow-y-visible">` —— 规范强制改成 overflow-y: auto

#### 杀手 ③：祖先有 `transform` 直接破坏 sticky 行为

任何祖先（哪怕中间隔了好几层）只要带 `transform`（包括 `translate-*`、`scale-*`、`rotate-*` 这些 Tailwind 类），都会让浏览器把那个祖先当作 sticky 的"containing block"。结果：sticky 元素只在那个祖先的盒子内部 sticky，根本贴不到浏览器顶端。

最容易翻车的场景：tab 切换动画用 `translate-y-1 → translate-y-0` 做"轻微滑入"。

❌ 错误：
```jsx
<div className={`transition-all duration-200
                 ${tabVisible ? "translate-y-0 opacity-100" : "translate-y-1 opacity-0"}`}>
  <Table />  {/* sticky thead 失效 */}
</div>
```

✅ 正确（只用 opacity，去掉 transform）：
```jsx
<div className={`transition-opacity duration-200
                 ${tabVisible ? "opacity-100" : "opacity-0"}`}>
  <Table />
</div>
```

`filter`、`will-change: transform`、`perspective` 也是同类杀手，一概不能在 sticky 元素的祖先上用。

### ⚠️ 其他次要禁令
- `top-0` 写成 `top-[50px]` 想让位给页面顶部 header —— 不需要，thead 的滚动祖先是 `<main>`，main 本就在 header 之下（参考 §3 布局，header 也在 main 内部），`top-0` 自然落在 header 下沿

### 🧱 Pagination 骨架

**核心原则**：分页器**不带 card 外壳**（无 border / 无 bg），全部内容**居中单行**，作为表格的页脚直接嵌进表格的同一个 bordered 容器，让数据 + 分页是同一个视觉单元。

```jsx
// Pagination 本体：card-less，居中单行，行内 padding
function Pagination({ page, total, onChange }) {
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const showPages = totalPages > 1;
  if (total === 0) return null;
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 px-3 py-3">
      <span className="text-sm text-black">
        共<span className="mx-1 font-semibold tabular-nums">
          {total.toLocaleString("zh-CN")}
        </span>条
      </span>
      {showPages && (
        <div className="flex items-center gap-1">
          <PageButton label={<ChevronLeft size={14} />} disabled={page <= 1} onClick={...} />
          {buildPageRange(page, totalPages).map((p) =>
            p === "..." ? <span className="px-1 text-slate-400">···</span>
                         : <PageButton label={p} active={p === page} onClick={...} />
          )}
          <PageButton label={<ChevronRight size={14} />} disabled={page >= totalPages} onClick={...} />
        </div>
      )}
    </div>
  );
}
```

**与表格的视觉融合**：表格组件接 `footer` prop，把 Pagination 渲染在同一个 bordered 容器底部，用 `border-t` 一根细线区隔：

```jsx
// DramaTable
export default function DramaTable({ dramas, loading, footer }) {
  return (
    <div className="overflow-hidden rounded-sm border border-[#ebeef5] bg-white">
      <div className="overflow-x-auto"><table>...</table></div>

      {footer && !isEmpty && (
        <div className="border-t border-[#ebeef5] bg-white">
          {footer}
        </div>
      )}
    </div>
  );
}

// 调用处：把 <Pagination /> 作为 footer 传进来，不再单独放
<DramaTable footer={<Pagination ... />} />
```

非表格场景（例如 NovelCard 网格）：Pagination 直接放在卡片网格下面即可，自身无 card 外壳即可与上方个体卡片视觉协调。

PageButton 方形 `h-7 min-w-[28px]`，active 用 brand-light bg + brand 边/文本：

```jsx
className={active
  ? "border border-brand bg-brand-light font-semibold text-brand"
  : "border border-[#dcdfe6] bg-white text-black hover:border-brand hover:text-brand"}
```

`buildPageRange` 用「头/尾/中」三窗口，pager-count=7（与 ElementUI / AntDesign 默认一致）：

```js
if (total <= 7) return [1..total];
if (current <= 4) return [1,2,3,4,5,6,"...",total];          // 头窗口
if (current >= total-3) return [1,"...",total-5,...,total];   // 尾窗口
return [1,"...",current-1,current,current+1,"...",total];     // 中窗口
```

### 🧱 TriggerButton 4 态骨架

```jsx
// 1. 默认
<button className="border-brand bg-brand-light text-brand hover:bg-brand hover:text-white">
  <Play size={11} /> 触发抓取
</button>

// 2. 抓取中
<span className="border-brand bg-brand-light text-brand">
  <Loader2 className="animate-spin" /> {scraped} / 入库 {inserted}
</span>

// 3. 已完成
<button className="border-emerald-300 bg-emerald-50 text-emerald-700">
  <Play size={11} /> 再抓一次
</button>

// 4. 失败
<button className="border-red-300 bg-red-50 text-red-700"
        title={`失败：${error.slice(0, 200)}`}>
  <RotateCcw size={11} /> 重试
</button>
```

### 🧱 状态点（Status Dot）

```jsx
const dotCls = {
  pending: "bg-slate-400",
  running: "bg-brand animate-pulse",
  done:    "bg-emerald-500",
  failed:  "bg-red-500",
}[status];
<span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${dotCls}`} />
```

### ⚙️ 关键参数

| 项 | 值 |
|---|---|
| 表壳 min-width | 按列总和算（800-1200px 常见） |
| 行 hover | `hover:bg-[#f7f8fa]` |
| thead 分割线 | `shadow-[0_1px_0_#ebeef5]`（不用 border 防止双线） |
| 数字列 | `text-right tabular-nums` |
| 总数文案 | 「共 **N** 条」（`font-semibold tabular-nums`，无强调色） |
| Pagination 布局 | `flex items-center justify-center gap-3 px-3 py-3` —— 总数 + 页码居中单行 |
| Pagination 容器 | **不带 zw-card** —— 由父表格的 footer 槽位承担 border + bg |
| 与表格融合 | 表格组件加 `footer` prop，footer 渲染在同一 bordered 容器底部，用 `border-t` 一线区隔 |
| 页码按钮尺寸 | `h-7 min-w-[28px]`，`gap-1` 间距 |
| Pager-count | 头/尾窗口各 6 个连续页 + ellipsis + 末页；中窗口 current ± 1 |
| Prev/Next | `<ChevronLeft/Right size={14} />`（不要写「上/下一页」文字） |
| 单页时分页 | 页码区段隐藏，只剩居中的「共 N 条」 |
| 零结果 | 整个 Pagination return null（连总数都不显示） |
| 全局并发锁 | `anyOtherRunning && !isThisRowRunning` 时禁用所有按钮 |

### ⚠️ 禁令
- thead 不要用 `border-b`（会跟 thead 自身边框叠加成 2px），用 `shadow-[0_1px_0_#ebeef5]` 替代
- 触发按钮 4 态切换时不要 unmount，否则进度数会闪
- 失败状态的 traceback **必须 slice(0, 200)**，避免 tooltip 被超长堆栈撑爆

### 📁 本仓库参考
- [frontend/src/components/DramaTable.jsx](frontend/src/components/DramaTable.jsx) — 表格 + th 嵌 Tooltip
- [frontend/src/App.jsx](frontend/src/App.jsx) — `Pagination`
- [frontend/src/components/ScrapeOverviewPage.jsx](frontend/src/components/ScrapeOverviewPage.jsx) — `TriggerButton` 4 态

---

## 8. Modal 全套（中间弹框 + 右侧抽屉 + 移动端左侧侧栏）

### 🎯 设计意图
三种 Modal 共享同一套退场 state，只在「方向 + 时长 + shadow 方向」上差异化：

| 类型 | 方向 | ENTER_LEAVE_MS | 出场动画 | shadow |
|------|------|---------------|---------|--------|
| 中间弹框（NovelModal） | 居中缩放 | 260 | scale 95→100 + translate-y 2→0 | `0_18px_60px_rgba(15,23,42,0.18)` |
| 右侧抽屉（DramaModal） | 从右滑入 | 500 | translate-x-full → 0 | `[-12px_0_36px_rgba(15,23,42,0.18)]` |
| 移动端左侧栏 | 浮层 | （建议加 300） | translate-x-[-160px] → 0 | `shadow-xl` |

### 🧱 共享 state pattern

```jsx
const ENTER_LEAVE_MS = 500; // 按方向调
const [isClosing, setIsClosing] = useState(false);
const closeTimerRef = useRef(null);

const closeWithAnimation = () => {
  setIsClosing(true);
  clearTimeout(closeTimerRef.current);
  closeTimerRef.current = setTimeout(onClose, ENTER_LEAVE_MS);
};

// ESC 关
useEffect(() => {
  if (!open) return;
  const h = (e) => e.key === "Escape" && closeWithAnimation();
  window.addEventListener("keydown", h);
  return () => window.removeEventListener("keydown", h);
}, [open]);

// 滚动锁
useEffect(() => {
  document.body.style.overflow = open ? "hidden" : "";
  return () => { document.body.style.overflow = ""; };
}, [open]);

// 切回 false 时清残留 isClosing
useEffect(() => {
  if (open) setIsClosing(false);
}, [open]);

// 卸载时清 timer
useEffect(() => () => clearTimeout(closeTimerRef.current), []);
```

### 🧱 右侧抽屉 骨架（用户重点关心）

```jsx
<div className={`fixed inset-0 z-50 flex justify-end
                 transition-opacity duration-500 ease-out
                 ${isClosing ? "bg-black/0 opacity-0" : "bg-black/35 opacity-100"}`}
     onClick={(e) => e.target === e.currentTarget && closeWithAnimation()}>
  <div className={`h-full w-full max-w-[720px] overflow-y-auto bg-white
                   shadow-[-12px_0_36px_rgba(15,23,42,0.18)]
                   transition-all duration-500 ease-out transform
                   ${isClosing ? "translate-x-full opacity-0" : "translate-x-0 opacity-100"}`}
       onClick={(e) => e.stopPropagation()}>
    {/* 内容 */}
  </div>
</div>
```

### 🧱 中间弹框 骨架

```jsx
<div className={`fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4
                 backdrop-blur-sm transition-all duration-300 ease-out
                 ${isClosing ? "bg-slate-900/0 opacity-0" : "bg-slate-900/35 opacity-100"}`}
     onClick={(e) => e.target === e.currentTarget && closeWithAnimation()}>
  <div className={`bg-white border border-[#ebeef5] rounded-lg
                   w-full max-w-2xl max-h-[calc(100dvh-48px)] overflow-y-auto
                   shadow-[0_18px_60px_rgba(15,23,42,0.18)]
                   transition-all duration-300 ease-out transform
                   ${isClosing
                     ? "opacity-0 scale-95 translate-y-2"
                     : "opacity-100 scale-100 translate-y-0"}`}
       onClick={(e) => e.stopPropagation()}>
    ...
  </div>
</div>
```

### ⚙️ 关键参数

| 项 | 值 |
|---|---|
| backdrop blur | `backdrop-blur-sm`（仅中间弹框，抽屉不要） |
| backdrop 色 | 中间用 `slate-900/35`，抽屉用 `black/35` |
| 抽屉 max-w | `max-w-[720px]`（再宽变成「半屏 modal」） |
| 抽屉 shadow | **负 X** `[-12px_0_36px_...]` 强化拉入感 |
| 抽屉 duration | 500ms 比中间 260ms 长，制造「侧拉」仪式感 |
| 内容 max-h | `max-h-[calc(100dvh-48px)]` + `overflow-y-auto` |

### ⚠️ 禁令
- 关闭流程必须**先动画再 onClose**（用 `isClosing` flag + setTimeout），React unmount 太快会截断动画
- 抽屉 `max-w` 不超 720（再宽就变成半屏 modal，失去「抽屉感」）
- backdrop 不要用 `bg-black`（纯黑过重），用 `bg-black/35` 或 `slate-900/35`
- ESC 监听必须在 `open` 时挂、关时摘，否则切到其他页面后还在监听

### 📁 本仓库参考
- [frontend/src/components/NovelModal.jsx](frontend/src/components/NovelModal.jsx) — 中间弹框
- [frontend/src/components/DramaModal.jsx](frontend/src/components/DramaModal.jsx) — **右侧抽屉范本**
- [frontend/src/components/SystemOverviewModal.jsx](frontend/src/components/SystemOverviewModal.jsx) — 中间弹框（300ms 时长变体）
- [frontend/src/App.jsx](frontend/src/App.jsx) — `MobileSider` 浮层（无动画版）

---

## 9. 一致性原则（横跨所有模式）

| 原则 | 规则 |
|------|------|
| **动画时长分档** | tooltip / tab 切换 = 200ms；中间弹框 = 260-300ms；右抽屉 = 500ms。三档不要互串。 |
| **关闭动画顺序** | 永远先 `setIsClosing(true)` → `setTimeout(onClose, MS)`，**先动画再 unmount** |
| **滚动锁** | 任何 modal 打开时 `body.style.overflow = "hidden"`；关闭 / 卸载时恢复 |
| **ESC 关闭** | 任何 modal 都监听 `keydown Escape` 并 `closeWithAnimation()` |
| **Tooltip 方向** | 永远向上（`bottom-full` / `bottom-[calc(100%+8px)]`）。**不向下展开** |
| **多选数据格式** | 前端 CSV 字符串 → 后端 `_split_csv` → ClickHouse `IN Array(String)` 参数化 |
| **状态分层渲染** | 永远 `error > loading > empty > content` 顺序判定 |
| **图标尺寸** | tooltip / chip = 12px；按钮 / tab = 14px；NavItem = 17px；空态 = 18px |
| **数字对齐** | 所有数字列加 `tabular-nums`，避免不等宽字体抖动 |
| **总数强调** | 用 `text-base font-semibold tabular-nums text-brand`（Pagination / KPI） |

---

## 10. 验证清单

套用本 SKILL 后逐项打勾：

### Token 就位
- [ ] tailwind.config.js → `theme.extend.colors` 含 `brand` / `brand-light` / `brand-dark` / `zw.border`
- [ ] index.css → `@layer components` 含 `.zw-field` / `.zw-card` / `.zw-primary-btn` / `.zw-default-btn`
- [ ] 全站字体 `Helvetica Neue, Helvetica, "PingFang SC", ...`，背景 `#e5e7eb`

### 模式自检
- [ ] **布局**：左侧栏 160px 不挤标题；header 和面包屑都在 `<main>` 内部、**不 sticky**、滚动时一起消失；只有 `<main>` 有滚动条
- [ ] **筛选**：选 2 个值后右侧出现灰圆 ✕；点 ✕ 一键清空；不选时只显示 ∨
- [ ] **筛选**：选中项用 `bg-brand-light text-brand` + ✓；展示时用中文 `、` 分隔
- [ ] **Tooltip**：hover 时向上展开；底部有向下双层三角；离开时无残留 1px gap
- [ ] **可视化**：点 tab 切内容；点收起整段塌；折叠时点 tab 自动展开
- [ ] **可视化**：error / loading / empty / content 四态层叠正确
- [ ] **可视化 Tooltip**：hover 时 tooltip 直接显示在指针位置，**不**从图表左上角滑入（确认所有 Recharts Tooltip 加了 `isAnimationActive={false}` + `wrapperStyle={{ transition: "none" }}`）
- [ ] **表格**：thead `bg-[#f2f3f5]` + 阴影下分割线（不用 border-b）
- [ ] **表格**：长表格滚动时 thead 应**始终粘在视口顶端**（确认外层卡片不用 `overflow-hidden`，thead 上有 `sticky top-0 z-20`）
- [ ] **分页**：「共 N 条 + 页码 + chevron」居中单行，**与表格共用同一 bordered 容器**（不是独立卡片）；单页时只剩居中的总数；零结果时整段隐藏；7 页以上自动用 ··· 折叠
- [ ] **触发按钮**：4 态都能复现（默认绿框 / 抓取中带进度 / 完成绿底「再抓一次」/ 失败红底「重试」）
- [ ] **中间弹框**：scale 95→100 + translate-y 2→0 入场，260-300ms，ESC + backdrop 关
- [ ] **右抽屉**：从右滑入 500ms，左缘负 X 阴影，max-w 720px

### 一致性
- [ ] 所有动画时长按 200 / 260-300 / 500 三档分配
- [ ] 所有 modal 都加 ESC + 滚动锁
- [ ] 所有 tooltip 都向上展开
- [ ] 所有数字列加 `tabular-nums`

跑完清单不通过的项，回 §3-§8 对应章节复核「关键参数」与「禁令」。
