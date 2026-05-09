import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  FileText,
  Info,
  LayoutDashboard,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";
import FilterBar from "./components/FilterBar";
import DramaFilterBar from "./components/DramaFilterBar";
import NovelCard from "./components/NovelCard";
import NovelModal from "./components/NovelModal";
import DramaTable from "./components/DramaTable";
import DramaModal from "./components/DramaModal";
import DramaInsights from "./components/DramaInsights";
import ScrapeOverviewPage from "./components/ScrapeOverviewPage";
import SystemOverviewModal from "./components/SystemOverviewModal";
import LoginPage from "./components/LoginPage";
import { useAuth } from "./hooks/useAuth";
import {
  fetchDramaPlatforms,
  fetchDramaLangs,
  fetchDramaTags,
  fetchDramas,
  fetchLangs,
  fetchNovels,
  fetchPlatforms,
  fetchTags,
} from "./api/client";

const PAGE_SIZE = 24;
const TAB_SWITCH_MS = 180;

const EMPTY_FILTERS = {
  platform: "",
  lang: "",
  tags: "",
  title: "",
  rank_type: "",
};

const MODULE_META = {
  novels: {
    title: "海外小说检测",
    subtitle: "Novel IP Insight",
    breadcrumb: ["海外内容监测", "小说检测"],
  },
  dramas: {
    title: "海外短剧检测",
    subtitle: "Short Drama Insight",
    breadcrumb: ["海外内容监测", "短剧检测"],
  },
  scrape: {
    title: "数据抓取概览",
    subtitle: "Scrape Overview",
    breadcrumb: ["海外内容监测", "数据抓取概览"],
  },
};

function Dashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState("dramas");
  const [displayTab, setDisplayTab] = useState("dramas");
  const [tabVisible, setTabVisible] = useState(true);
  const [siderOpen, setSiderOpen] = useState(false);
  const [siderCollapsed, setSiderCollapsed] = useState(false);
  const [systemOverviewOpen, setSystemOverviewOpen] = useState(false);

  // 小说状态
  const [novelDraftFilters, setNovelDraftFilters] = useState(EMPTY_FILTERS);
  const [novelFilters, setNovelFilters] = useState(EMPTY_FILTERS);
  const [novelQueryVersion, setNovelQueryVersion] = useState(0);
  const [novels, setNovels] = useState([]);
  const [novelTotal, setNovelTotal] = useState(0);
  const [novelPage, setNovelPage] = useState(1);
  const [novelLoading, setNovelLoading] = useState(false);
  const [novelError, setNovelError] = useState(null);
  const [activeNovel, setActiveNovel] = useState(null);
  const [platforms, setPlatforms] = useState([]);
  const [langs, setLangs] = useState([]);
  const [topTags, setTopTags] = useState([]);

  // 短剧状态
  const [dramaDraftFilters, setDramaDraftFilters] = useState(EMPTY_FILTERS);
  const [dramaFilters, setDramaFilters] = useState(EMPTY_FILTERS);
  const [dramaQueryVersion, setDramaQueryVersion] = useState(0);
  const [dramas, setDramas] = useState([]);
  const [dramaTotal, setDramaTotal] = useState(0);
  const [dramaPage, setDramaPage] = useState(1);
  const [dramaLoading, setDramaLoading] = useState(false);
  const [dramaError, setDramaError] = useState(null);
  const [activeDrama, setActiveDrama] = useState(null);
  const [dramaPlatforms, setDramaPlatforms] = useState([]);
  const [dramaLangs, setDramaLangs] = useState([]);
  const [dramaTopTags, setDramaTopTags] = useState([]);

  useEffect(() => {
    fetchPlatforms().then((d) => setPlatforms(d.platforms || [])).catch(() => {});
    fetchLangs().then((d) => setLangs(d.langs || [])).catch(() => {});
    fetchTags().then((d) => setTopTags(d.tags || [])).catch(() => {});
    fetchDramaPlatforms().then((d) => setDramaPlatforms(d.platforms || [])).catch(() => {});
    fetchDramaLangs().then((d) => setDramaLangs(d.langs || [])).catch(() => {});
    fetchDramaTags().then((d) => setDramaTopTags(d.tags || [])).catch(() => {});
  }, []);

  const loadNovels = useCallback((page, filters) => {
    setNovelLoading(true);
    setNovelError(null);
    // 后端（DuckDB）已完成 GHI 分项计算，前端仅消费返回字段并渲染。
    fetchNovels({ ...filters, page, page_size: PAGE_SIZE })
      .then((data) => {
        setNovels(data.items || []);
        setNovelTotal(data.total || 0);
      })
      .catch((err) => setNovelError(err.message))
      .finally(() => setNovelLoading(false));
  }, []);

  const loadDramas = useCallback((page, filters) => {
    setDramaLoading(true);
    setDramaError(null);
    // 短剧列表同样走后端预聚合查询，前端不做二次口径处理。
    fetchDramas({ ...filters, page, page_size: PAGE_SIZE })
      .then((data) => {
        setDramas(data.items || []);
        setDramaTotal(data.total || 0);
      })
      .catch((err) => setDramaError(err.message))
      .finally(() => setDramaLoading(false));
  }, []);

  useEffect(() => {
    loadNovels(novelPage, novelFilters);
  }, [novelFilters, novelPage, novelQueryVersion, loadNovels]);

  useEffect(() => {
    loadDramas(dramaPage, dramaFilters);
  }, [dramaFilters, dramaPage, dramaQueryVersion, loadDramas]);

  useEffect(() => {
    if (activeTab === displayTab) return undefined;
    setTabVisible(false);
    const timer = setTimeout(() => {
      setDisplayTab(activeTab);
      requestAnimationFrame(() => setTabVisible(true));
    }, TAB_SWITCH_MS);
    return () => clearTimeout(timer);
  }, [activeTab, displayTab]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setSiderOpen(false);
  };

  const handleNovelSearch = () => {
    setNovelFilters(novelDraftFilters);
    setNovelPage(1);
    setNovelQueryVersion((version) => version + 1);
  };

  const handleDramaSearch = () => {
    setDramaFilters(dramaDraftFilters);
    setDramaPage(1);
    setDramaQueryVersion((version) => version + 1);
  };

  const currentMeta = MODULE_META[displayTab];
  const currentTotal =
    displayTab === "novels" ? novelTotal : displayTab === "dramas" ? dramaTotal : null;
  const currentLoading =
    displayTab === "novels" ? novelLoading : displayTab === "dramas" ? dramaLoading : false;

  return (
    <div className="min-h-screen bg-[#e5e7eb] text-black">
      <SiderContent
        activeTab={activeTab}
        onChange={handleTabChange}
        collapsed={siderCollapsed}
        onToggleCollapsed={() => setSiderCollapsed((c) => !c)}
      />
      <MobileSider open={siderOpen} onClose={() => setSiderOpen(false)}>
        <SiderContent activeTab={activeTab} onChange={handleTabChange} mobile />
      </MobileSider>

      <div
        className={`min-h-screen transition-[padding] duration-200 ${
          siderCollapsed ? "md:pl-[64px]" : "md:pl-[224px]"
        }`}
      >
        {/*
          整页只有 <main> 一个滚动条；header 与面包屑都在 main 里，
          滚动时随内容一起上移消失，让位给 sticky thead 真正贴在浏览器顶端。
        */}
        <main className="h-screen overflow-y-auto bg-[#e5e7eb]">
          <header className="h-[50px] border-b border-[#ebeef5] bg-white">
            <div className="flex h-full items-center justify-between gap-3 px-4">
              <div className="flex min-w-0 items-center gap-3">
                <button
                  onClick={() => setSiderOpen(true)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 text-black md:hidden"
                  aria-label="打开导航"
                >
                  <Menu size={18} strokeWidth={1.7} />
                </button>
                <div className="min-w-0">
                  <div className="truncate text-xs font-semibold text-black">
                    {currentMeta.title}
                  </div>
                  <div className="hidden text-[11px] text-black sm:block">
                    {currentMeta.subtitle}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSystemOverviewOpen(true)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-brand-light bg-brand-light px-2.5 text-[11px] font-medium text-brand transition-colors hover:bg-brand hover:text-white"
                  title="查看系统说明（业务价值 / 创新度 / 开发难度）"
                >
                  <FileText size={12} strokeWidth={1.8} />
                  <span>系统说明</span>
                </button>
              </div>

              <div className="flex items-center gap-4 text-xs text-black">
                {currentTotal !== null && (
                  <span className="hidden sm:inline">当前数据 {currentTotal}</span>
                )}
                {currentLoading && <span className="text-brand">查询中</span>}
                {user && (
                  <span className="hidden text-slate-500 sm:inline">
                    {user.username}
                  </span>
                )}
                <button
                  type="button"
                  onClick={onLogout}
                  className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 hover:bg-slate-50"
                  title="登出"
                >
                  <LogOut size={12} strokeWidth={1.7} />
                  <span className="hidden sm:inline">登出</span>
                </button>
              </div>
            </div>
          </header>

          <div className="flex h-9 items-center bg-[#f0eef6] px-3 text-xs text-black">
            {currentMeta.breadcrumb.map((item, idx) => (
              <span key={item}>
                {idx > 0 && <span className="mx-2 text-black">/</span>}
                <span className="font-medium text-black">
                  {item}
                </span>
              </span>
            ))}
          </div>

          {/*
            ⚠️ 这里只能用 opacity 做切换动画，不要再加 translate-y-*。
            一旦加了 transform，里面 DramaTable 的 sticky thead 会失效——
            transform 会让浏览器把当前元素当作 sticky 的「containing block」，
            导致 thead 沿着这个块滚走而不是贴浏览器顶端。
          */}
          <div
            className={`space-y-3 p-3 transition-opacity duration-200 ease-out
              ${tabVisible ? "opacity-100" : "opacity-0"}`}
          >
            {displayTab === "scrape" ? (
              <ScrapeOverviewPage />
            ) : displayTab === "novels" ? (
              <section className="space-y-4">
                <FilterBar
                  filters={novelDraftFilters}
                  onChange={(k, v) => {
                    setNovelDraftFilters((p) => ({ ...p, [k]: v }));
                  }}
                  onSearch={handleNovelSearch}
                  platforms={platforms}
                  langs={langs}
                  topTags={topTags}
                />

                {novelError && (
                  <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-500">
                    查询失败：{novelError}
                  </div>
                )}

                <div className="flex justify-end">
                  <GhiInfoTooltip />
                </div>

                <GridState
                  loading={novelLoading}
                  empty={!novels.length}
                  emptyText="暂无匹配小说数据，请调整筛选条件或触发爬取任务。"
                >
                  {novels.map((novel) => (
                    <NovelCard key={novel.id} novel={novel} onClick={setActiveNovel} />
                  ))}
                </GridState>

                <Pagination page={novelPage} total={novelTotal} onChange={setNovelPage} />
              </section>
            ) : (
              <section className="space-y-4">
                <DramaFilterBar
                  filters={dramaDraftFilters}
                  platforms={dramaPlatforms}
                  langs={dramaLangs}
                  topTags={dramaTopTags}
                  onChange={(k, v) => {
                    setDramaDraftFilters((p) => ({ ...p, [k]: v }));
                  }}
                  onSearch={handleDramaSearch}
                />

                {dramaError && (
                  <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-500">
                    查询失败：{dramaError}
                  </div>
                )}

                <DramaInsights
                  filters={dramaFilters}
                  queryVersion={dramaQueryVersion}
                  onDramaClick={setActiveDrama}
                />

                <DramaTable
                  dramas={dramas}
                  loading={dramaLoading}
                  onTitleClick={setActiveDrama}
                  footer={
                    <Pagination
                      page={dramaPage}
                      total={dramaTotal}
                      onChange={setDramaPage}
                    />
                  }
                />
              </section>
            )}
          </div>
        </main>
      </div>

      <NovelModal novel={activeNovel} onClose={() => setActiveNovel(null)} />
      <DramaModal drama={activeDrama} onClose={() => setActiveDrama(null)} />
      <SystemOverviewModal
        open={systemOverviewOpen}
        onClose={() => setSystemOverviewOpen(false)}
      />
    </div>
  );
}

// ─── 辅助子组件 ──────────────────────────────────────────────

/** GHI 算法悬浮提示（鼠标悬停展开，向左弹出） */
function GhiInfoTooltip() {
  return (
    <div className="relative group">
      <span className="text-xs text-black cursor-default select-none group-hover:text-brand transition-colors duration-200 flex items-center gap-1">
        GHI 算法
        <Info size={12} strokeWidth={1.5} />
      </span>

      <div className="absolute right-0 bottom-full mb-2 w-[480px] z-50
                      invisible opacity-0 translate-y-1
                      group-hover:visible group-hover:opacity-100 group-hover:translate-y-0
                      transition-all duration-200
                      bg-white border border-zw-border rounded-lg p-4 space-y-3 shadow-[0_12px_36px_rgba(15,23,42,0.12)]">
        <div className="px-3 py-2 text-xs text-black border border-zw-border rounded bg-[#f7f8fa]">
          GHI = S_popular × 0.3 + S_engage × 0.3 + S_adapt × 0.4
        </div>
        <p className="text-xs text-black leading-relaxed">
          指标均由 DuckDB 在 SQL 内预计算后返回，前端只做字段映射展示，避免口径偏差。
        </p>
      </div>
    </div>
  );
}

function SiderContent({ activeTab, onChange, mobile = false, collapsed = false, onToggleCollapsed }) {
  // 移动端抽屉始终保持完全展开（窄屏没必要再收起）；只有桌面侧栏受 collapsed 影响
  const isCollapsed = !mobile && collapsed;
  return (
    <aside
      className={`${mobile ? "flex" : "fixed left-0 top-0 z-40 hidden md:flex"}
        h-screen ${isCollapsed ? "w-[64px]" : "w-[224px]"} flex-col border-r border-[#ebeef5] bg-white
        transition-[width] duration-200`}
    >
      <div className={`flex h-[60px] items-center gap-2 ${isCollapsed ? "justify-center px-2" : "px-4"}`}>
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-brand text-brand">
          <LayoutDashboard size={18} strokeWidth={1.8} />
        </div>
        {!isCollapsed && (
          <div className="min-w-0">
            <div className="truncate text-lg font-bold text-black">罗盘</div>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 px-1 py-3">
        <NavItem
          active={activeTab === "novels"}
          icon={<BookOpen size={17} strokeWidth={1.8} />}
          label="海外小说检测"
          collapsed={isCollapsed}
          onClick={() => onChange("novels")}
        />
        <NavItem
          active={activeTab === "dramas"}
          icon={<Clapperboard size={17} strokeWidth={1.8} />}
          label="海外短剧检测"
          collapsed={isCollapsed}
          onClick={() => onChange("dramas")}
        />
        <NavItem
          active={activeTab === "scrape"}
          icon={<Activity size={17} strokeWidth={1.8} />}
          label="数据抓取概览"
          collapsed={isCollapsed}
          onClick={() => onChange("scrape")}
        />
      </nav>

      {!mobile && (
        <div className="border-t border-[#ebeef5] bg-white px-2 py-2 flex items-center">
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label={isCollapsed ? "展开侧边栏" : "收起侧边栏"}
            title={isCollapsed ? "展开" : "收起"}
            className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 bg-white text-black hover:bg-[#f5f7fa] hover:text-brand"
          >
            {isCollapsed ? <PanelLeftOpen size={16} strokeWidth={1.8} /> : <PanelLeftClose size={16} strokeWidth={1.8} />}
          </button>
        </div>
      )}
    </aside>
  );
}

function NavItem({ active, icon, label, onClick, collapsed = false }) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? label : undefined}
      className={`flex h-10 w-full items-center gap-3 rounded text-xs transition-colors
        ${collapsed ? "justify-center px-0" : "px-3"}
        ${active
          ? "bg-brand-light font-medium text-brand"
          : "font-medium text-black hover:bg-[#f5f7fa] hover:text-brand"
        }`}
    >
      {icon}
      {!collapsed && <span>{label}</span>}
    </button>
  );
}

function MobileSider({ open, onClose, children }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <button
        className="absolute inset-0 bg-black/30"
        onClick={onClose}
        aria-label="关闭导航"
      />
      <div className="relative h-full w-[224px] bg-white shadow-xl">
        {children}
        <button
          onClick={onClose}
          className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded text-black hover:bg-[#f5f7fa]"
          aria-label="关闭导航"
        >
          <X size={18} strokeWidth={1.8} />
        </button>
      </div>
    </div>
  );
}

function GridState({ loading, empty, emptyText, children }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, idx) => (
          <div key={idx} className="zw-card space-y-4">
            <div className="h-4 w-24 animate-pulse rounded bg-slate-100" />
            <div className="h-7 w-3/4 animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-5/6 animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-slate-100" />
          </div>
        ))}
      </div>
    );
  }
  if (empty) {
    return (
      <div className="zw-card py-20 text-center text-black">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-light text-brand">
          <LayoutDashboard size={24} strokeWidth={1.7} />
        </div>
        <p className="text-xs">{emptyText}</p>
      </div>
    );
  }
  return <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{children}</div>;
}

/**
 * Pagination 组件本身**不带卡片外壳**（无 border / 无 bg），让它能直接
 * 嵌进 DramaTable 的同一个 bordered 容器里，作为表格的「页脚」存在；
 * 也能在没有 table 的页面（例如 NovelCard 网格）作为独立行使用。
 *
 * 全部内容居中单行：共 N 条 · < 1 2 3 4 5 6 ··· 42 >
 */
function Pagination({ page, total, onChange }) {
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const showPages = totalPages > 1;
  if (total === 0) return null;
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 px-3 py-3">
      <span className="text-xs text-black">
        共
        <span className="mx-1 font-semibold tabular-nums">
          {total.toLocaleString("zh-CN")}
        </span>
        条
      </span>
      {showPages && (
        <div className="flex items-center gap-1">
          <PageButton
            label={<ChevronLeft size={14} strokeWidth={1.7} />}
            ariaLabel="上一页"
            disabled={page <= 1}
            onClick={() => onChange(page - 1)}
          />
          {buildPageRange(page, totalPages).map((p, i) =>
            p === "..." ? (
              <span
                key={`ellipsis-${i}`}
                className="select-none px-1 text-xs text-slate-400"
              >
                ···
              </span>
            ) : (
              <PageButton
                key={p}
                label={p}
                active={p === page}
                onClick={() => onChange(p)}
              />
            )
          )}
          <PageButton
            label={<ChevronRight size={14} strokeWidth={1.7} />}
            ariaLabel="下一页"
            disabled={page >= totalPages}
            onClick={() => onChange(page + 1)}
          />
        </div>
      )}
    </div>
  );
}

/** 通用分页按钮：方形 28×28，active 用 brand-light 高亮 + brand 文本 */
function PageButton({ label, active, disabled, onClick, ariaLabel }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className={`flex h-7 min-w-[28px] items-center justify-center rounded px-2 text-xs tabular-nums transition-colors duration-200
        ${active
          ? "border border-brand bg-brand-light font-semibold text-brand"
          : "border border-[#dcdfe6] bg-white text-black hover:border-brand hover:text-brand"
        }
        disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-[#dcdfe6] disabled:hover:text-black`}
    >
      {label}
    </button>
  );
}

/**
 * 7 页内全部展示；超过则按当前位置选择三种窗口：
 *   - 头部窗口（current ≤ 4）：[1 2 3 4 5 6 ··· last]
 *   - 尾部窗口（current ≥ last-3）：[1 ··· last-5 last-4 last-3 last-2 last-1 last]
 *   - 中部窗口：[1 ··· current-1 current current+1 ··· last]
 * 与 ElementUI / AntDesign 的默认 pager-count=7 一致。
 */
function buildPageRange(current, total) {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  if (current <= 4) {
    return [1, 2, 3, 4, 5, 6, "...", total];
  }
  if (current >= total - 3) {
    return [1, "...", total - 5, total - 4, total - 3, total - 2, total - 1, total];
  }
  return [1, "...", current - 1, current, current + 1, "...", total];
}

// ─────────────────────────────────────────────────────────────
// 顶层 Auth Gate
// loading → 启动占位；未登录 → LoginPage；登录成功 → Dashboard
// 把 useAuth 抽到顶层是为了避免主看板内的大量 useEffect 在未登录时
// 先发请求拿一堆 401，再被守卫推回登录页。
// ─────────────────────────────────────────────────────────────
export default function App() {
  const { loading, user, login, register, logout } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-page text-xs text-black">
        正在检查登录状态…
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLogin={login} onRegister={register} />;
  }

  return <Dashboard user={user} onLogout={logout} />;
}
