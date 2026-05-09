import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, BookOpen, Clapperboard, Loader2, Play, RefreshCw, RotateCcw } from "lucide-react";
import {
  fetchDramaScrapeStatus,
  fetchScrapeOverview,
  fetchScrapeStatus,
  triggerDramaScrape,
  triggerScrape,
} from "../api/client";

const POLL_MS = 2000;
const NOVEL_DEFAULT_LIMIT = 50;
const DRAMA_DEFAULT_LIMIT = 80;

// 平台展示名（与 DramaTable / NovelCard 命名口径保持一致）
const PLATFORM_LABEL = {
  // 小说
  wattpad: "Wattpad",
  royal_road: "Royal Road",
  syosetu_daily: "Syosetu 日榜",
  syosetu_weekly: "Syosetu 周榜",
  syosetu_monthly: "Syosetu 月榜",
  // 短剧
  shortdrama_top5: "ShortDrama 聚合",
  netshort: "NetShort",
  reelshort: "ReelShort",
  dramabox: "DramaBox",
  dramareels: "DramaReels",
  dramawave: "DramaWave",
  goodshort: "GoodShort",
  moboreels: "MoboReels",
  shortmax: "ShortMax",
};

const SCHEDULE_META = {
  daily:   { text: "每日",    cls: "text-emerald-700 bg-emerald-50 border-emerald-200", jobId: "daily_scrape"     },
  weekly:  { text: "每周一",  cls: "text-sky-700     bg-sky-50     border-sky-200",     jobId: "weekly_syosetu"   },
  monthly: { text: "每月 1 号", cls: "text-violet-700  bg-violet-50  border-violet-200",  jobId: "monthly_syosetu"  },
  manual:  { text: "手动",    cls: "text-slate-600   bg-slate-100  border-slate-200",   jobId: null                },
};

const CATEGORY_LABEL = {
  novel: "小说",
  drama: "短剧",
};

// 小说 rank_type 是英文 ID，dramas 已经是中文段位标签，本表只翻译小说侧
const RANK_TYPE_LABEL = {
  daily: "日榜",
  weekly: "周榜",
  monthly: "月榜",
};

function formatTime(isoStr) {
  if (!isoStr) return "—";
  const d = new Date(isoStr);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function relativeFromNow(isoStr) {
  if (!isoStr) return "";
  const diffMs = Date.now() - new Date(isoStr).getTime();
  if (Number.isNaN(diffMs)) return "";
  const futurePrefix = diffMs < 0 ? "" : "";
  const abs = Math.abs(diffMs);
  const diffMin = Math.floor(abs / 60000);
  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin} 分钟${diffMs >= 0 ? "前" : "后"}`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr} 小时${diffMs >= 0 ? "前" : "后"}`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay} 天${diffMs >= 0 ? "前" : "后"}`;
}

function CategoryBadge({ category }) {
  const isNovel = category === "novel";
  const Icon = isNovel ? BookOpen : Clapperboard;
  const cls = isNovel
    ? "text-brand bg-brand-light border-brand/30"
    : "text-amber-700 bg-amber-50 border-amber-200";
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] ${cls}`}>
      <Icon size={10} strokeWidth={1.8} />
      {CATEGORY_LABEL[category]}
    </span>
  );
}

function ScheduleBadge({ schedule }) {
  const meta = SCHEDULE_META[schedule] || SCHEDULE_META.manual;
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] ${meta.cls}`}>
      {meta.text}
    </span>
  );
}

/**
 * 榜单类型芯片：每个 rank_type 一个标签 + 数量徽章；最多展示 4 个，多余在 +N
 * 上 hover 显示完整列表（与 DramaTable 的 Tags 同款交互）。
 */
function RankTypeChips({ items }) {
  if (!items || items.length === 0) {
    return <span className="text-slate-400">—</span>;
  }
  const max = 4;
  const visible = items.slice(0, max);
  const rest = items.slice(max);

  return (
    <div className="flex flex-wrap gap-1">
      {visible.map((it) => {
        const label = it.rank_type
          ? (RANK_TYPE_LABEL[it.rank_type] || it.rank_type)
          : "未分类";
        return (
          <span
            key={`${label}-${it.count}`}
            className="inline-flex items-center gap-1 rounded border border-[#dcdfe6] bg-white px-1.5 py-0.5 text-[11px] text-black"
            title={`${label}: ${it.count} 条`}
          >
            <span className="max-w-[80px] truncate">{label}</span>
            <span className="text-slate-400 tabular-nums">{it.count}</span>
          </span>
        );
      })}
      {rest.length > 0 && (
        <span className="group relative inline-flex items-center rounded border border-[#dcdfe6] bg-white px-1.5 py-0.5 text-[11px] text-slate-500">
          +{rest.length}
          <span className="invisible absolute left-1/2 -translate-x-1/2 bottom-[calc(100%+8px)] z-30 min-w-44 max-w-72 rounded-lg border border-[#dcdfe6] bg-white p-2 text-left text-[11px] leading-5 text-black opacity-0 shadow-[0_8px_24px_rgba(15,23,42,0.12)] transition-opacity group-hover:visible group-hover:opacity-100">
            {rest
              .map((r) => `${r.rank_type ? (RANK_TYPE_LABEL[r.rank_type] || r.rank_type) : "未分类"}（${r.count}）`)
              .join("、")}
            <span aria-hidden className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full h-0 w-0 border-l-[7px] border-r-[7px] border-t-[7px] border-l-transparent border-r-transparent border-t-[#dcdfe6]" />
            <span aria-hidden className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full -mt-px h-0 w-0 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-white" />
          </span>
        </span>
      )}
    </div>
  );
}

/**
 * 单行触发按钮：根据 task 状态自动切态。
 * row.trigger_kind 为 null 时表示该平台不可独立触发，按钮置灰。
 */
function TriggerButton({ row, task, onClick, anyOtherRunning }) {
  if (!row.trigger_kind) {
    return (
      <span className="text-slate-400" title="该平台暂不可独立触发">—</span>
    );
  }

  const status = task?.status;
  const running = status === "pending" || status === "running";
  const aggregateHint = row.trigger_via_aggregate
    ? `本平台数据来自聚合任务 ${row.trigger_key}，触发会抓取所有 8 个短剧平台`
    : `触发本平台抓取（${row.trigger_kind === "novel" ? NOVEL_DEFAULT_LIMIT : DRAMA_DEFAULT_LIMIT} 条上限）`;

  // 抓取中
  if (running) {
    const progress = task?.scraped > 0
      ? `${task.scraped}${task.inserted ? ` / 入库 ${task.inserted}` : ""}`
      : "抓取中";
    return (
      <span
        className="inline-flex items-center gap-1 rounded border border-brand bg-brand-light px-2 py-1 text-[11px] text-brand"
        title={`task_id: ${task.task_id || "-"}`}
      >
        <Loader2 size={11} strokeWidth={2} className="animate-spin" />
        {progress}
      </span>
    );
  }

  // 失败 → 重试
  if (status === "failed") {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={anyOtherRunning}
        title={`失败：${(task?.error || "").slice(0, 200)}\n点击重试`}
        className="inline-flex items-center gap-1 rounded border border-red-300 bg-red-50 px-2 py-1 text-[11px] text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <RotateCcw size={11} strokeWidth={1.8} />
        重试
      </button>
    );
  }

  // 已完成 → 可再次触发
  if (status === "done") {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={anyOtherRunning}
        title={aggregateHint}
        className="inline-flex items-center gap-1 rounded border border-emerald-300 bg-emerald-50 px-2 py-1 text-[11px] text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Play size={11} strokeWidth={1.8} />
        再抓一次
      </button>
    );
  }

  // 默认状态
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={anyOtherRunning}
      title={aggregateHint}
      className="inline-flex items-center gap-1 rounded border border-brand bg-brand-light px-2 py-1 text-[11px] text-brand hover:bg-brand hover:text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
    >
      <Play size={11} strokeWidth={1.8} />
      触发抓取
    </button>
  );
}

function StatCard({ label, value, hint }) {
  return (
    <div className="rounded-sm border border-[#ebeef5] bg-white px-4 py-3">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-2">
        <span className="text-lg font-semibold text-black tabular-nums">{value}</span>
        {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
      </div>
    </div>
  );
}

function SkeletonRows({ count = 6 }) {
  return Array.from({ length: count }).map((_, idx) => (
    <tr key={idx} className="h-12 border-b border-[#ebeef5]">
      {Array.from({ length: 7 }).map((__, c) => (
        <td key={c} className="px-3 py-2">
          <div className="h-3 w-full animate-pulse rounded bg-slate-100" />
        </td>
      ))}
    </tr>
  ));
}

export default function ScrapeOverviewPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 每行独立的任务状态：rowKey -> { task_id, status, scraped, inserted, error }
  const [tasks, setTasks] = useState({});
  const pollersRef = useRef({});

  const load = () => {
    setLoading(true);
    setError(null);
    fetchScrapeOverview()
      .then((d) => setData(d))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  // 卸载时清掉所有轮询定时器
  useEffect(() => () => {
    Object.values(pollersRef.current).forEach((id) => clearInterval(id));
    pollersRef.current = {};
  }, []);

  const handleTrigger = async (row) => {
    if (!row.trigger_kind || !row.trigger_key) return;
    const rowKey = `${row.category}:${row.key}`;

    // 如果该行已有轮询，先清掉（防止重复触发产生竞态）
    if (pollersRef.current[rowKey]) {
      clearInterval(pollersRef.current[rowKey]);
      delete pollersRef.current[rowKey];
    }

    const limit = row.trigger_kind === "novel" ? NOVEL_DEFAULT_LIMIT : DRAMA_DEFAULT_LIMIT;
    const triggerFn = row.trigger_kind === "novel" ? triggerScrape : triggerDramaScrape;
    const statusFn = row.trigger_kind === "novel" ? fetchScrapeStatus : fetchDramaScrapeStatus;

    try {
      const task = await triggerFn({ platform: row.trigger_key, genre: "", limit });
      setTasks((prev) => ({ ...prev, [rowKey]: task }));

      pollersRef.current[rowKey] = setInterval(async () => {
        const status = await statusFn(task.task_id).catch(() => null);
        if (!status) return;
        setTasks((prev) => ({ ...prev, [rowKey]: status }));
        if (status.status === "done" || status.status === "failed") {
          clearInterval(pollersRef.current[rowKey]);
          delete pollersRef.current[rowKey];
          if (status.status === "done") {
            // 完成后刷新概览，让最近抓取/总记录数等同步
            load();
          }
        }
      }, POLL_MS);
    } catch (err) {
      setTasks((prev) => ({
        ...prev,
        [rowKey]: { status: "failed", error: err.message },
      }));
    }
  };

  const anyRunning = useMemo(
    () => Object.values(tasks).some(
      (t) => t?.status === "pending" || t?.status === "running"
    ),
    [tasks]
  );

  // 把 schedule.jobs 列表拍平成 jobId → next_run 的映射，每行查一次即可
  const jobNextRun = useMemo(() => {
    const map = {};
    (data?.schedule?.jobs ?? []).forEach((j) => {
      map[j.id] = j.next_run;
    });
    return map;
  }, [data?.schedule?.jobs]);

  // 平台行：novel 在前、drama 在后；同类内按总记录数降序
  const rows = useMemo(() => {
    const list = (data?.platforms ?? []).slice();
    const order = { novel: 0, drama: 1 };
    list.sort((a, b) => {
      const ca = order[a.category] ?? 9;
      const cb = order[b.category] ?? 9;
      if (ca !== cb) return ca - cb;
      return (b.total || 0) - (a.total || 0);
    });
    return list;
  }, [data?.platforms]);

  const totals = useMemo(() => {
    const t = {
      total: rows.length,
      scheduled: rows.filter((r) => r.schedule !== "manual").length,
      novelTotal: 0,
      novelRecent: 0,
      dramaTotal: 0,
      dramaRecent: 0,
    };
    rows.forEach((r) => {
      if (r.category === "novel") {
        t.novelTotal += r.total || 0;
        t.novelRecent += r.recent_7d || 0;
      } else {
        t.dramaTotal += r.total || 0;
        t.dramaRecent += r.recent_7d || 0;
      }
    });
    return t;
  }, [rows]);

  const schedule = data?.schedule;
  const cronTime = schedule
    ? `${String(schedule.hour).padStart(2, "0")}:${String(schedule.minute).padStart(2, "0")} (${schedule.timezone})`
    : "—";

  return (
    <section className="space-y-4">
      {/* 顶部标题 + 刷新 */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-[#ebeef5] bg-white px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Activity size={16} strokeWidth={1.7} className="text-brand" />
            <h1 className="text-xs font-semibold text-black">数据抓取概览</h1>
          </div>
          <span className="hidden text-xs text-slate-500 sm:inline">
            执行时间 <span className="text-black">{cronTime}</span>
          </span>
          {schedule?.enabled ? (
            <span className="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> 调度已启用
            </span>
          ) : (
            <span className="inline-flex items-center rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600">
              调度已禁用
            </span>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded border border-slate-200 bg-white px-3 py-1.5 text-xs text-black hover:border-brand hover:text-brand disabled:opacity-50"
        >
          <RefreshCw size={12} strokeWidth={1.7} className={loading ? "animate-spin" : ""} />
          刷新
        </button>
      </div>

      {/* 统计带 */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="小说总记录数" value={totals.novelTotal.toLocaleString()} hint={`近 7 天 +${totals.novelRecent.toLocaleString()}`} />
        <StatCard label="短剧总记录数" value={totals.dramaTotal.toLocaleString()} hint={`近 7 天 +${totals.dramaRecent.toLocaleString()}`} />
        <StatCard label="平台总数" value={totals.total} />
        <StatCard label="已纳入定时" value={totals.scheduled} hint={`占 ${totals.total ? Math.round((totals.scheduled / totals.total) * 100) : 0}%`} />
      </div>

      {/* 错误态 */}
      {error && (
        <div className="rounded-sm border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
          加载失败：{error}
          <button onClick={load} className="ml-3 rounded border border-red-200 bg-white px-2 py-0.5 text-xs hover:bg-red-50">
            重试
          </button>
        </div>
      )}

      {/* 主表 —— 每行一个平台，参考 DramaTable 的紧凑列布局
          ⚠️ 不要在 thead 与 <main> 之间塞任何 overflow 容器（包括 overflow-x-auto），
          否则 sticky thead 会被困住。横向溢出由 main 自行处理。 */}
      <div className="rounded-sm border border-[#ebeef5] bg-white">
        <table className="min-w-[1200px] w-full table-fixed text-left text-xs text-black">
          {/* sticky thead：滚动时表头始终留在浏览器视口顶端 */}
          <thead className="sticky top-0 z-20 bg-[#f2f3f5] text-black shadow-[0_1px_0_#ebeef5]">
              <tr className="h-14">
                <th className="w-[220px] px-3 font-semibold">平台</th>
                <th className="w-[70px]  px-3 font-semibold">类型</th>
                <th className="w-[80px]  px-3 font-semibold">抓取频率</th>
                <th className="w-[230px] px-3 font-semibold">榜单类型</th>
                <th className="w-[150px] px-3 font-semibold">下次执行</th>
                <th className="w-[150px] px-3 font-semibold">最近抓取</th>
                <th className="w-[90px]  px-3 text-right font-semibold">总记录数</th>
                <th className="w-[80px]  px-3 text-right font-semibold">近 7 天</th>
                <th className="w-[120px] px-3 text-center font-semibold">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && !data ? (
                <SkeletonRows />
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-xs text-slate-500">
                    暂无平台数据
                  </td>
                </tr>
              ) : (
                rows.map((r) => {
                  const meta = SCHEDULE_META[r.schedule] || SCHEDULE_META.manual;
                  const nextRun = meta.jobId ? jobNextRun[meta.jobId] : null;
                  const rowKey = `${r.category}:${r.key}`;
                  const task = tasks[rowKey];
                  const isThisRowRunning = task?.status === "pending" || task?.status === "running";
                  return (
                    <tr
                      key={rowKey}
                      className="border-b border-[#ebeef5] bg-white hover:bg-[#f7f8fa]"
                    >
                      <td className="px-3 py-2.5">
                        <div className="font-medium text-black">{PLATFORM_LABEL[r.key] || r.key}</div>
                        <div className="text-[11px] text-slate-500">{r.key}</div>
                      </td>
                      <td className="px-3 align-middle"><CategoryBadge category={r.category} /></td>
                      <td className="px-3 align-middle"><ScheduleBadge schedule={r.schedule} /></td>
                      <td className="px-3 py-2.5 align-middle">
                        <RankTypeChips items={r.rank_types} />
                      </td>
                      <td className="px-3 align-middle">
                        {nextRun ? (
                          <div>
                            <div className="text-black">{formatTime(nextRun)}</div>
                            <div className="text-[11px] text-slate-500">{relativeFromNow(nextRun)}</div>
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-3 align-middle">
                        {r.last_crawled ? (
                          <div>
                            <div className="text-black">{formatTime(r.last_crawled)}</div>
                            <div className="text-[11px] text-slate-500">{relativeFromNow(r.last_crawled)}</div>
                          </div>
                        ) : (
                          <span className="text-slate-400">尚未抓取</span>
                        )}
                      </td>
                      <td className="px-3 text-right align-middle tabular-nums">{(r.total || 0).toLocaleString()}</td>
                      <td className="px-3 text-right align-middle tabular-nums">
                        {r.recent_7d > 0 ? (
                          <span className="text-emerald-600">+{r.recent_7d.toLocaleString()}</span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>
                      <td className="px-3 text-center align-middle">
                        <TriggerButton
                          row={r}
                          task={task}
                          onClick={() => handleTrigger(r)}
                          anyOtherRunning={anyRunning && !isThisRowRunning}
                        />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
      </div>
    </section>
  );
}
