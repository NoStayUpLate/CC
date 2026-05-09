import { useEffect, useRef, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchDramaRankHistory } from "../api/client";

const ENTER_LEAVE_MS = 500;

export default function DramaModal({ drama, onClose }) {
  const [isClosing, setIsClosing] = useState(false);
  const closeTimerRef = useRef(null);

  useEffect(() => {
    if (drama) {
      setIsClosing(false);
    }
    return undefined;
  }, [drama]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) {
        clearTimeout(closeTimerRef.current);
      }
    };
  }, []);

  if (!drama) return null;

  const closeWithAnimation = () => {
    setIsClosing(true);
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
    }
    closeTimerRef.current = setTimeout(() => {
      onClose();
    }, ENTER_LEAVE_MS);
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex justify-end
                  transition-opacity duration-500 ease-out
                  ${isClosing ? "bg-black/0 opacity-0" : "bg-black/35 opacity-100"}`}
      onClick={closeWithAnimation}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`h-full w-full md:w-[60vw] overflow-y-auto bg-white border-l border-zw-border shadow-[-12px_0_36px_rgba(15,23,42,0.18)]
                    transition-all duration-500 ease-out transform
                    ${isClosing ? "translate-x-full opacity-0" : "translate-x-0 opacity-100"}`}
      >
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[#ebeef5] bg-white px-8 py-6">
          <div>
            <h3 className="text-lg font-bold text-black">{drama.title}</h3>
            <p className="text-xs text-black mt-1">
              平台 {drama.platform} · {drama.rank_type || "未分类"} · 资源位位置 #{drama.rank_in_platform}
            </p>
          </div>
          <button
            onClick={closeWithAnimation}
            className="flex h-8 w-8 items-center justify-center rounded bg-slate-100 text-lg leading-none text-black hover:bg-brand-light hover:text-brand"
          >
            ×
          </button>
        </div>

        <div className="space-y-6 px-8 py-6">
          {drama.cover_url && (
            <div className="mx-auto aspect-[3/4] w-full max-w-[260px] overflow-hidden rounded border border-zw-border bg-slate-100">
              <img
                src={drama.cover_url}
                alt={`${drama.title || "短剧"}封面`}
                loading="lazy"
                className="h-full w-full object-cover"
              />
            </div>
          )}

          <Section title="短剧简介">
            <p className="text-xs leading-relaxed text-black">
              {drama.summary || "暂无简介"}
            </p>
          </Section>

          {drama.tags?.length > 0 && (
            <Section title="标签">
              <div className="flex flex-wrap gap-2">
                {drama.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs px-2.5 py-1 bg-slate-100 text-black rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </Section>
          )}

          <Section title="DHI 热度指数">
            <div className="rounded-lg border border-zw-border bg-[#f7f8fa] p-4 space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-black">综合 DHI</span>
                <span className="text-2xl font-bold text-brand tabular-nums">
                  {(drama.dhi || 0).toFixed(1)}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-black opacity-70">等级判定</span>
                <span className={`font-semibold ${dhiLevel(drama.dhi || 0).color}`}>
                  {dhiLevel(drama.dhi || 0).label}
                </span>
              </div>
              <div className="space-y-2.5 pt-2 border-t border-zw-border">
                <ScoreBar
                  label="题材匹配度（×45%）"
                  value={drama.s_tag || 0}
                  hint="命中 S/A 级关键标签得分。S 级 +25，A 级 +12，基线 50。"
                />
                <ScoreBar
                  label="资源位强度（×35%）"
                  value={drama.s_position || 0}
                  hint="平台内名次靠前程度，第 1 名 100，每后退一位 -8。"
                />
                <ScoreBar
                  label="数据新鲜度（×20%）"
                  value={drama.s_recency || 0}
                  hint="距今天数线性衰减，今天 100，每过一天 -10。"
                />
              </div>
              <p className="text-[11px] text-black opacity-60 pt-1">
                公式：DHI = 题材 × 45% + 资源位 × 35% + 新鲜度 × 20%
              </p>
            </div>
          </Section>

          <RankHistorySection platform={drama.platform} title={drama.title} />

          <Section title="基础信息">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <Info label="榜单类型" value={drama.rank_type || "未分类"} />
              <Info label="资源位位置" value={`#${drama.rank_in_platform || "-"}`} />
              <Info label="平台" value={drama.platform} />
              <Info label="集数" value={drama.episodes ?? "-"} />
              <Info label="抓取日期" value={drama.crawl_date || "-"} />
            </div>
          </Section>

          {drama.source_url && (
            <a
              href={drama.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex rounded bg-brand px-4 py-2 text-xs text-black hover:bg-brand-dark"
            >
              查看来源页面
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="space-y-2">
      <h4 className="text-xs font-semibold text-black">{title}</h4>
      <div>{children}</div>
    </section>
  );
}

function Info({ label, value }) {
  return (
    <div className="rounded-lg border border-zw-border bg-[#f7f8fa] px-3 py-2">
      <div className="text-xs text-black">{label}</div>
      <div className="text-black font-medium">{value}</div>
    </div>
  );
}

function dhiLevel(dhi) {
  if (dhi >= 80) return { label: "S 级爆款潜力", color: "text-brand" };
  if (dhi >= 65) return { label: "A 级高潜力", color: "text-blue-500" };
  if (dhi >= 45) return { label: "B 级待观察", color: "text-amber-500" };
  return { label: "C 级低潜力", color: "text-black" };
}

function ScoreBar({ label, value, hint }) {
  const pct = Math.min(Math.max(value, 0), 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-xs">
        <span className="text-black">{label}</span>
        <span className="font-bold text-black tabular-nums">{pct.toFixed(1)}</span>
      </div>
      <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-brand progress-bar-animated"
          style={{ "--target-width": `${pct}%`, width: `${pct}%` }}
        />
      </div>
      {hint && <p className="text-[10px] text-black opacity-60 leading-relaxed">{hint}</p>}
    </div>
  );
}

const RANK_HISTORY_DAYS = 30;

function formatMD(iso) {
  // "2026-05-09" → "05-09"；用纯字符串切片避免 new Date() 时区漂移
  if (typeof iso !== "string" || iso.length < 10) return iso;
  return iso.slice(5, 10);
}

function RankHistorySection({ platform, title }) {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setItems(null);
    setError(null);
    fetchDramaRankHistory(platform, title, RANK_HISTORY_DAYS)
      .then((data) => {
        if (cancelled) return;
        setItems(data?.items || []);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "加载失败");
      });
    return () => {
      cancelled = true;
    };
  }, [platform, title]);

  // recharts 需要的数据结构（保留 ISO 给 tooltip，单独字段给坐标轴）
  const chartData = (items || []).map((p) => ({
    date: formatMD(p.crawl_date),
    iso: p.crawl_date,
    rank: p.rank_in_platform,
  }));

  const ranks = chartData.map((d) => d.rank);
  const minRank = ranks.length ? Math.max(1, Math.min(...ranks) - 1) : 1;
  const maxRank = ranks.length ? Math.max(...ranks) + 1 : 10;

  return (
    <Section title="资源位变化趋势（近 30 天）">
      <div className="rounded-lg border border-zw-border bg-[#f7f8fa] p-4 space-y-3">
        <div className="flex items-baseline justify-between">
          <span className="text-xs text-black opacity-70">
            数值越小越靠前（rank=1 = 平台首位）
          </span>
          <span className="text-xs text-black opacity-60">
            {chartData.length > 0 ? `${chartData.length} 个数据点` : ""}
          </span>
        </div>

        {items === null && !error && (
          <div className="h-[160px] flex items-center justify-center text-xs text-black opacity-50">
            加载中…
          </div>
        )}

        {error && (
          <div className="h-[160px] flex items-center justify-center text-xs text-red-500">
            {error}
          </div>
        )}

        {items !== null && !error && chartData.length === 0 && (
          <div className="h-[160px] flex items-center justify-center text-xs text-black opacity-50 text-center px-4">
            尚无历史快照。下次定时爬取后会自动累积每日资源位变化。
          </div>
        )}

        {items !== null && !error && chartData.length === 1 && (
          <div className="h-[160px] flex items-center justify-center text-xs text-black opacity-60 text-center px-4">
            目前只有 1 个数据点（{chartData[0].iso}，第 {chartData[0].rank} 位）。
            <br />
            等次日爬取完成后趋势曲线会出现。
          </div>
        )}

        {items !== null && !error && chartData.length >= 2 && (
          <div className="h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  axisLine={{ stroke: "#cbd5e1" }}
                  tickLine={false}
                />
                <YAxis
                  reversed
                  allowDecimals={false}
                  domain={[minRank, maxRank]}
                  tick={{ fontSize: 11, fill: "#475569" }}
                  axisLine={{ stroke: "#cbd5e1" }}
                  tickLine={false}
                  width={30}
                  label={{
                    value: "名次",
                    angle: -90,
                    position: "insideLeft",
                    style: { fontSize: 10, fill: "#94a3b8" },
                  }}
                />
                <Tooltip content={<RankTooltip />} cursor={{ stroke: "#cbd5e1", strokeWidth: 1 }} />
                <Line
                  type="monotone"
                  dataKey="rank"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#10b981", strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </Section>
  );
}

function RankTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded border border-zw-border bg-white px-2.5 py-1.5 text-xs shadow-md">
      <div className="text-black opacity-70">{point.iso}</div>
      <div className="font-semibold text-black">第 {point.rank} 位</div>
    </div>
  );
}
