import { useCallback, useEffect, useRef, useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Clapperboard,
  FileText,
  Info,
  LayoutDashboard,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import FilterBar from "./components/FilterBar";
import DramaFilterBar from "./components/DramaFilterBar";
import NovelCard from "./components/NovelCard";
import NovelModal from "./components/NovelModal";
import DramaTable from "./components/DramaTable";
import DramaModal from "./components/DramaModal";
import DramaInsights from "./components/DramaInsights";
import SystemOverviewModal from "./components/SystemOverviewModal";
import ResultCounter from "./components/ResultCounter";
import LoginPage from "./components/LoginPage";
import { useAuth } from "./hooks/useAuth";
import {
  fetchDramaPlatforms,
  fetchDramaLangs,
  fetchDramaTags,
  fetchDramas,
  fetchDramaScrapeStatus,
  fetchLangs,
  fetchNovels,
  fetchPlatforms,
  fetchScrapeStatus,
  fetchTags,
  triggerDramaScrape,
  triggerScrape,
} from "./api/client";

const POLL_MS = 2000;
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
};

function Dashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState("dramas");
  const [displayTab, setDisplayTab] = useState("dramas");
  const [tabVisible, setTabVisible] = useState(true);
  const [siderOpen, setSiderOpen] = useState(false);
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
  const [novelScrapeTask, setNovelScrapeTask] = useState(null);
  const [novelScrapePanel, setNovelScrapePanel] = useState(false);
  const [novelScrapeForm, setNovelScrapeForm] = useState({
    platform: "wattpad",
    genre: "",
    limit: 50,
  });

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
  const [dramaScrapeTask, setDramaScrapeTask] = useState(null);
  const [dramaScrapePanel, setDramaScrapePanel] = useState(false);
  const [dramaScrapeForm, setDramaScrapeForm] = useState({
    platform: "shortdrama_top5",
    genre: "",
    limit: 80,
  });

  const novelPollRef = useRef(null);
  const dramaPollRef = useRef(null);

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
    // 后端（ClickHouse）已完成 GHI 分项计算，前端仅消费返回字段并渲染。
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

  useEffect(() => () => {
    clearInterval(novelPollRef.current);
    clearInterval(dramaPollRef.current);
  }, []);

  useEffect(() => {
    if (activeTab === displayTab) return undefined;
    setTabVisible(false);
    const timer = setTimeout(() => {
      setDisplayTab(activeTab);
      requestAnimationFrame(() => setTabVisible(true));
    }, TAB_SWITCH_MS);
    return () => clearTimeout(timer);
  }, [activeTab, displayTab]);

  const handleNovelScrape = async () => {
    try {
      const task = await triggerScrape(novelScrapeForm);
      setNovelScrapeTask(task);
      novelPollRef.current = setInterval(async () => {
        const status = await fetchScrapeStatus(task.task_id).catch(() => null);
        if (!status) return;
        setNovelScrapeTask(status);
        if (status.status === "done" || status.status === "failed") {
          clearInterval(novelPollRef.current);
          if (status.status === "done") loadNovels(1, novelFilters);
        }
      }, POLL_MS);
    } catch (err) {
      alert(`触发失败: ${err.message}`);
    }
  };

  const handleDramaScrape = async () => {
    try {
      const task = await triggerDramaScrape(dramaScrapeForm);
      setDramaScrapeTask(task);
      dramaPollRef.current = setInterval(async () => {
        const status = await fetchDramaScrapeStatus(task.task_id).catch(() => null);
        if (!status) return;
        setDramaScrapeTask(status);
        if (status.status === "done" || status.status === "failed") {
          clearInterval(dramaPollRef.current);
          if (status.status === "done") loadDramas(1, dramaFilters);
        }
      }, POLL_MS);
    } catch (err) {
      alert(`触发失败: ${err.message}`);
    }
  };

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
  const currentTotal = displayTab === "novels" ? novelTotal : dramaTotal;
  const currentLoading = displayTab === "novels" ? novelLoading : dramaLoading;
  const currentTask = displayTab === "novels" ? novelScrapeTask : dramaScrapeTask;

  return (
    <div className="min-h-screen bg-[#e5e7eb] text-black">
      <SiderContent activeTab={activeTab} onChange={handleTabChange} />
      <MobileSider open={siderOpen} onClose={() => setSiderOpen(false)}>
        <SiderContent activeTab={activeTab} onChange={handleTabChange} mobile />
      </MobileSider>

      <div className="min-h-screen md:pl-[120px]">
        <header className="sticky top-0 z-30 h-[50px] border-b border-[#ebeef5] bg-white">
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
                <div className="truncate text-sm font-semibold text-black">
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
              <span className="hidden sm:inline">当前数据 {currentTotal}</span>
              {currentLoading && <span className="text-brand">查询中</span>}
              {currentTask?.status && (
                <span className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1">
                  <StatusDot status={currentTask.status} />
                  {taskStatusText(currentTask.status)}
                </span>
              )}
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

        <main className="h-[calc(100vh-50px)] overflow-y-auto bg-[#e5e7eb]">
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

          <div
            className={`space-y-3 p-3 transition-all duration-200 ease-out
              ${tabVisible ? "translate-y-0 opacity-100" : "translate-y-1 opacity-0"}`}
          >
            {displayTab === "novels" ? (
              <section className="space-y-4">
                <ScrapePanel
                  open={novelScrapePanel}
                  onToggle={() => setNovelScrapePanel((v) => !v)}
                  title="小说爬取任务"
                  form={novelScrapeForm}
                  setForm={setNovelScrapeForm}
                  task={novelScrapeTask}
                  onSubmit={handleNovelScrape}
                  options={[
                    { value: "wattpad", label: "Wattpad" },
                    { value: "royal_road", label: "Royal Road" },
                    { value: "syosetu_weekly", label: "Syosetu 周榜" },
                  ]}
                />

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

                <div className="zw-card flex flex-wrap items-center justify-between gap-3">
                  <ResultCounter total={novelTotal} loading={novelLoading} error={novelError} />
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
                <ScrapePanel
                  open={dramaScrapePanel}
                  onToggle={() => setDramaScrapePanel((v) => !v)}
                  title="短剧爬取任务（TOP5 平台爆款）"
                  form={dramaScrapeForm}
                  setForm={setDramaScrapeForm}
                  task={dramaScrapeTask}
                  onSubmit={handleDramaScrape}
                  options={[{ value: "shortdrama_top5", label: "TOP5 平台聚合抓取" }]}
                />

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

                <div className="zw-card">
                  <ResultCounter total={dramaTotal} loading={dramaLoading} error={dramaError} />
                </div>

                <DramaInsights
                  filters={dramaFilters}
                  queryVersion={dramaQueryVersion}
                  onDramaClick={setActiveDrama}
                />

                <DramaTable
                  dramas={dramas}
                  loading={dramaLoading}
                  onTitleClick={setActiveDrama}
                />

                <Pagination page={dramaPage} total={dramaTotal} onChange={setDramaPage} />
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

      <div className="absolute right-0 top-full mt-2 w-[480px] z-50
                      invisible opacity-0 translate-y-1
                      group-hover:visible group-hover:opacity-100 group-hover:translate-y-0
                      transition-all duration-200
                      bg-white border border-zw-border rounded-lg p-4 space-y-3 shadow-[0_12px_36px_rgba(15,23,42,0.12)]">
        <div className="px-3 py-2 text-xs text-black border border-zw-border rounded bg-[#f7f8fa]">
          GHI = S_popular × 0.3 + S_engage × 0.3 + S_adapt × 0.4
        </div>
        <p className="text-xs text-black leading-relaxed">
          指标均由 ClickHouse 预计算后返回，前端只做字段映射展示，避免口径偏差。
        </p>
      </div>
    </div>
  );
}

/** 爬取状态指示点 */
function StatusDot({ status }) {
  const cls = {
    pending: "bg-slate-400",
    running: "bg-brand animate-pulse",
    done: "bg-emerald-500",
    failed: "bg-red-500",
  }[status] || "bg-slate-400";
  return <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${cls}`} />;
}

function taskStatusText(status) {
  return {
    pending: "等待启动",
    running: "爬取中",
    done: "已完成",
    failed: "失败",
  }[status] || status;
}

function SiderContent({ activeTab, onChange, mobile = false }) {
  return (
    <aside
      className={`${mobile ? "flex" : "fixed left-0 top-0 z-40 hidden md:flex"}
        h-screen w-[120px] flex-col border-r border-[#ebeef5] bg-white`}
    >
      <div className="flex h-[60px] items-center gap-2 px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-full border border-brand text-brand">
          <LayoutDashboard size={18} strokeWidth={1.8} />
        </div>
        <div className="min-w-0">
          <div className="truncate text-xl font-bold text-black">罗盘</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-1 py-3">
        <NavItem
          active={activeTab === "novels"}
          icon={<BookOpen size={17} strokeWidth={1.8} />}
          label="海外小说检测"
          onClick={() => onChange("novels")}
        />
        <NavItem
          active={activeTab === "dramas"}
          icon={<Clapperboard size={17} strokeWidth={1.8} />}
          label="海外短剧检测"
          onClick={() => onChange("dramas")}
        />
      </nav>

      <div className="border-t border-[#ebeef5] bg-white px-2 py-3 text-right text-[11px] text-black">
        数据监测工作台
      </div>
    </aside>
  );
}

function NavItem({ active, icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex h-10 w-full items-center gap-3 rounded px-3 text-sm transition-colors
        ${active
          ? "bg-brand-light font-medium text-brand"
          : "font-medium text-black hover:bg-[#f5f7fa] hover:text-brand"
        }`}
    >
      {icon}
      <span>{label}</span>
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
      <div className="relative h-full w-[120px] bg-white shadow-xl">
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

function ScrapePanel({
  open,
  onToggle,
  title,
  form,
  setForm,
  task,
  onSubmit,
  options,
}) {
  return (
    <>
      <button
        onClick={onToggle}
        className="zw-primary-btn inline-flex items-center gap-1.5"
      >
        {open ? "收起抓取面板" : "触发爬取"}
        {open ? <ChevronUp size={14} strokeWidth={1.5} /> : <ChevronDown size={14} strokeWidth={1.5} />}
      </button>
      {open && (
        <div className="zw-card space-y-4">
          <h2 className="text-sm font-semibold text-black">{title}</h2>
          <div className="grid gap-3 md:grid-cols-[minmax(180px,240px)_minmax(180px,1fr)_120px_auto] md:items-end">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-black">目标平台</label>
              <select
                value={form.platform}
                onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value }))}
                className="zw-field w-full"
              >
                {options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-black">关键词（可选）</label>
              <input
                type="text"
                value={form.genre}
                onChange={(e) => setForm((f) => ({ ...f, genre: e.target.value }))}
                className="zw-field"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-black">抓取条数</label>
              <input
                type="number"
                min={1}
                max={200}
                value={form.limit}
                onChange={(e) => setForm((f) => ({ ...f, limit: Number(e.target.value || 1) }))}
                className="zw-field"
              />
            </div>
            <button
              onClick={onSubmit}
              disabled={task?.status === "running" || task?.status === "pending"}
              className="zw-primary-btn disabled:cursor-not-allowed disabled:opacity-50"
            >
              开始爬取
            </button>
          </div>
          {task && (
            <div className="flex flex-wrap items-center gap-3 rounded bg-[#f7f8fa] px-3 py-2 text-sm">
              <StatusDot status={task.status} />
              <span className="font-medium text-black">
                {task.status === "running" && "爬取中..."}
                {task.status === "pending" && "等待启动..."}
                {task.status === "done" && "爬取完成"}
                {task.status === "failed" && `失败：${task.error}`}
              </span>
              {task.scraped > 0 && (
                <span className="text-black">
                  已抓取 {task.scraped} 条 / 已入库 {task.inserted} 条
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </>
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
        <p className="text-sm">{emptyText}</p>
      </div>
    );
  }
  return <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{children}</div>;
}

function Pagination({ page, total, onChange }) {
  const totalPages = Math.ceil(total / PAGE_SIZE);
  if (totalPages <= 1) return null;
  return (
    <div className="zw-card flex flex-col items-center gap-2">
      <div className="flex flex-wrap justify-center gap-2">
        <PageButton label="上一页" disabled={page <= 1} onClick={() => onChange(page - 1)} />
        {buildPageRange(page, totalPages).map((p, i) =>
          p === "..." ? (
            <span key={`ellipsis-${i}`} className="px-3 py-2 text-black">...</span>
          ) : (
            <PageButton key={p} label={p} active={p === page} onClick={() => onChange(p)} />
          )
        )}
        <PageButton
          label="下一页"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        />
      </div>
      <span className="text-xs text-black">
        第 {page} / {totalPages} 页
      </span>
    </div>
  );
}

/** 通用分页按钮 */
function PageButton({ label, active, disabled, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded px-3 py-2 text-sm transition-colors duration-200
        ${active
          ? "bg-brand font-bold text-black"
          : "border border-slate-200 bg-white text-black hover:border-brand hover:text-brand"
        }
        disabled:opacity-40 disabled:cursor-not-allowed`}
    >
      {label}
    </button>
  );
}

function buildPageRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = new Set([1, total, current, current - 1, current + 1].filter(
    (p) => p >= 1 && p <= total
  ));
  const sorted = [...pages].sort((a, b) => a - b);
  const result = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) result.push("...");
    result.push(p);
  });
  return result;
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
      <div className="min-h-screen flex items-center justify-center bg-page text-sm text-black">
        正在检查登录状态…
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLogin={login} onRegister={register} />;
  }

  return <Dashboard user={user} onLogout={logout} />;
}
