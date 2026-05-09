import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import {
  BarChart3,
  ChevronDown,
  ChevronUp,
  LayoutDashboard,
  Network,
  Sparkles,
  Trophy,
} from "lucide-react";
import { fetchAllDramas } from "../api/client";

const PLATFORM_LABEL = {
  netshort: "NetShort",
  reelshort: "ReelShort",
  dramabox: "DramaBox",
  dramareels: "DramaReels",
  dramawave: "DramaWave",
  goodshort: "GoodShort",
  moboreels: "MoboReels",
  shortmax: "ShortMax",
};

const PLATFORM_COLORS = {
  shortmax: "#0ea5e9",
  moboreels: "#00BF8A",
  dramabox: "#f59e0b",
  reelshort: "#ef4444",
  netshort: "#2563eb",
  dramareels: "#8b5cf6",
  dramawave: "#14b8a6",
  goodshort: "#ec4899",
};
const FALLBACK_COLORS = ["#00BF8A", "#0ea5e9", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#ec4899", "#64748b"];
const RANK_TYPE_COLORS = ["#00BF8A", "#00A877", "#34D9A6", "#7AE5C4", "#B8F0DA", "#94a3b8", "#cbd5e1"];

// 这些是「资源位」名称，被错误写进了 tags 字段，需要从题材标签里剔除掉
const SECTION_TAGS = new Set([
  "轮播推荐",
  "顶部推荐",
  "推荐栏位",
  "近期热门",
  "热门榜单",
  "当前热门",
  "最近上新",
  "未分类",
]);

const TAB_DEFS = [
  { key: "overview", label: "数据概览", icon: LayoutDashboard },
  { key: "trend", label: "趋势洞察", icon: Sparkles },
  { key: "correlation", label: "标签搭配", icon: Network },
  { key: "ranking", label: "表现榜单", icon: Trophy },
];

// 主标签 → 同义词集合（中英混合数据里同一题材常见多种写法）。
// 只用于"标签搭配" Tab 的主标签匹配；副标签照原文展示。
const MAIN_TAG_GROUPS = [
  { key: "狼人",     label: "狼人",     aliases: ["狼人", "werewolf", "alpha", "werewolf/alpha"] },
  { key: "重生",     label: "重生",     aliases: ["重生", "rebirth", "reincarnation", "reborn", "regression"] },
  { key: "复仇",     label: "复仇",     aliases: ["复仇", "revenge", "karma payback", "comeback"] },
  { key: "恶役千金", label: "恶役千金", aliases: ["恶役千金", "villainess", "恶女"] },
];
const MAIN_ALIAS_LOOKUP = MAIN_TAG_GROUPS.map((g) => ({
  key: g.key,
  label: g.label,
  aliasSet: new Set(g.aliases.map((a) => a.toLowerCase())),
}));

function platformColor(platform, idx = 0) {
  return PLATFORM_COLORS[platform] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
}

function platformLabel(platform) {
  return PLATFORM_LABEL[platform] || platform || "—";
}

function heatColor(score) {
  if (score >= 90) return "#00A877";
  if (score >= 75) return "#00BF8A";
  if (score >= 60) return "#34D9A6";
  if (score >= 40) return "#7AE5C4";
  if (score >= 20) return "#B8F0DA";
  if (score > 0) return "#E6F9F3";
  return "#f1f5f9";
}

function median(nums) {
  if (!nums || nums.length === 0) return 0;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function truncate(s, n) {
  if (!s) return "";
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

// ─────────────────────────────────────────────────────────────
// 聚合：所有指标都从同一份 rows 里 useMemo 算
// ─────────────────────────────────────────────────────────────
function aggregate(rows) {
  if (!rows || rows.length === 0) {
    return {
      total: 0,
      avgDhi: 0,
      maxDhi: 0,
      byPlatform: [],
      byRankType: [],
      topTags: [],
      heatmap: [],
      top: [],
    };
  }

  // KPI
  let sum = 0;
  let max = 0;
  rows.forEach((r) => {
    const h = r.dhi || 0;
    sum += h;
    if (h > max) max = h;
  });
  const avgDhi = sum / rows.length;

  // 平台分布
  const platformMap = new Map();
  rows.forEach((r) => {
    const p = r.platform || "unknown";
    if (!platformMap.has(p)) platformMap.set(p, { platform: p, count: 0, sum: 0 });
    const o = platformMap.get(p);
    o.count += 1;
    o.sum += r.dhi || 0;
  });
  const byPlatform = Array.from(platformMap.values())
    .map((o) => ({ platform: o.platform, count: o.count, avg_heat: o.count ? o.sum / o.count : 0 }))
    .sort((a, b) => b.count - a.count);

  // 栏位分布
  const rankTypeMap = new Map();
  rows.forEach((r) => {
    const k = r.rank_type || "未分类";
    rankTypeMap.set(k, (rankTypeMap.get(k) || 0) + 1);
  });
  const byRankType = Array.from(rankTypeMap.entries())
    .map(([rank_type, count]) => ({ rank_type, count }))
    .sort((a, b) => b.count - a.count);

  // 题材标签：剔除栏位伪标签 + 空字符串
  const tagMap = new Map();
  rows.forEach((r) => {
    (r.tags || []).forEach((rawTag) => {
      if (!rawTag) return;
      const tag = rawTag.trim();
      if (!tag || SECTION_TAGS.has(tag)) return;
      if (!tagMap.has(tag)) tagMap.set(tag, { tag, count: 0, sum: 0 });
      const o = tagMap.get(tag);
      o.count += 1;
      o.sum += r.dhi || 0;
    });
  });
  const topTags = Array.from(tagMap.values())
    .map((o) => ({ tag: o.tag, count: o.count, avg_heat: o.count ? o.sum / o.count : 0 }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 30);

  // 平台 × 栏位 热力
  const heatmapMap = new Map();
  rows.forEach((r) => {
    const k = `${r.platform}|${r.rank_type || "未分类"}`;
    if (!heatmapMap.has(k)) {
      heatmapMap.set(k, { platform: r.platform, rank_type: r.rank_type || "未分类", count: 0, sum: 0 });
    }
    const o = heatmapMap.get(k);
    o.count += 1;
    o.sum += r.dhi || 0;
  });
  const heatmap = Array.from(heatmapMap.values()).map((o) => ({
    platform: o.platform,
    rank_type: o.rank_type,
    count: o.count,
    avg_heat: o.count ? o.sum / o.count : 0,
  }));

  // TOP 榜
  const top = [...rows]
    .filter((r) => (r.dhi || 0) > 0)
    .sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0) || (a.rank_in_platform || 0) - (b.rank_in_platform || 0))
    .slice(0, 20);

  // 标签搭配：4 个主标签各算一份
  const correlations = {};
  MAIN_ALIAS_LOOKUP.forEach((g) => {
    correlations[g.key] = computeTagCorrelation(rows, g);
  });

  return { total: rows.length, avgDhi, maxDhi: max, byPlatform, byRankType, topTags, heatmap, top, correlations };
}

// ─────────────────────────────────────────────────────────────
// 标签搭配聚合：找出含主标签的剧，按副标签分桶算 ΔDHI / Δ位置
// 主标签匹配走 alias 集合（大小写不敏感）；副标签去重时用原文，
// 但同主标签别名要剔除掉，避免"狼人"在自己身边出现 werewolf 节点。
// ─────────────────────────────────────────────────────────────
function computeTagCorrelation(rows, group) {
  const matched = rows.filter((r) =>
    (r.tags || []).some((t) => t && group.aliasSet.has(t.trim().toLowerCase()))
  );
  if (matched.length === 0) {
    return { mainKey: group.key, label: group.label, baseline: null, combos: [] };
  }

  let sumDhi = 0;
  let sumPos = 0;
  let posCount = 0;
  matched.forEach((r) => {
    sumDhi += r.dhi || 0;
    if (r.rank_in_platform && r.rank_in_platform > 0) {
      sumPos += r.rank_in_platform;
      posCount += 1;
    }
  });
  const baseline = {
    count: matched.length,
    avgDhi: sumDhi / matched.length,
    avgPos: posCount ? sumPos / posCount : null,
  };

  const comboMap = new Map();
  matched.forEach((r) => {
    (r.tags || []).forEach((rawTag) => {
      if (!rawTag) return;
      const tag = rawTag.trim();
      if (!tag || SECTION_TAGS.has(tag)) return;
      // 剔除主标签自身的所有别名，否则散点图里会出现"狼人 - werewolf"这种自指噪声
      if (group.aliasSet.has(tag.toLowerCase())) return;
      if (!comboMap.has(tag)) {
        comboMap.set(tag, { tag, count: 0, sumDhi: 0, sumPos: 0, posCount: 0 });
      }
      const o = comboMap.get(tag);
      o.count += 1;
      o.sumDhi += r.dhi || 0;
      if (r.rank_in_platform && r.rank_in_platform > 0) {
        o.sumPos += r.rank_in_platform;
        o.posCount += 1;
      }
    });
  });

  const combos = Array.from(comboMap.values())
    .map((o) => {
      const avgDhi = o.count ? o.sumDhi / o.count : 0;
      const avgPos = o.posCount ? o.sumPos / o.posCount : null;
      return {
        tag: o.tag,
        count: o.count,
        avgDhi,
        avgPos,
        dhiDelta: avgDhi - baseline.avgDhi,
        // 资源位数字越小越好；posDelta 用 baseline-combo，正值=组合让位置更靠前
        posDelta:
          baseline.avgPos !== null && avgPos !== null ? baseline.avgPos - avgPos : null,
      };
    })
    .sort((a, b) => b.count - a.count);

  return { mainKey: group.key, label: group.label, baseline, combos };
}

// ─────────────────────────────────────────────────────────────
// 容器：拉一次全量，三个 Tab 共享聚合结果
// ─────────────────────────────────────────────────────────────
export default function DramaInsights({ filters, queryVersion, onDramaClick }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [collapsed, setCollapsed] = useState(false);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchAllDramas(filters)
      .then((data) => {
        if (!cancelled) setRows(data.items || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, queryVersion]);

  const stats = useMemo(() => aggregate(rows), [rows]);

  return (
    <div className="zw-card space-y-4">
      <div
        className={`flex flex-wrap items-center gap-1 ${collapsed ? "" : "border-b border-[#ebeef5] pb-2"}`}
      >
        {TAB_DEFS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => {
                setActiveTab(tab.key);
                if (collapsed) setCollapsed(false);
              }}
              className={`inline-flex h-8 items-center gap-1.5 rounded px-3 text-xs transition-colors
                ${active
                  ? "bg-brand-light font-semibold text-brand"
                  : "text-black hover:bg-[#f5f7fa] hover:text-brand"
                }`}
            >
              <Icon size={14} strokeWidth={1.7} />
              {tab.label}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className="ml-auto inline-flex h-8 items-center gap-1.5 rounded px-3 text-[11px] text-black hover:bg-[#f5f7fa] hover:text-brand transition-colors"
          title={collapsed ? "展开可视化" : "收起可视化"}
        >
          <span>{collapsed ? "展开" : "收起"}</span>
          {collapsed ? (
            <ChevronDown size={14} strokeWidth={1.7} />
          ) : (
            <ChevronUp size={14} strokeWidth={1.7} />
          )}
        </button>
      </div>

      {!collapsed && (
        <>
          {error && <TabError message={error} />}
          {!error && loading && rows.length === 0 && <TabSkeleton kind={activeTab} />}
          {!error && !loading && rows.length === 0 && (
            <TabEmpty text="当前筛选条件下无数据，调整筛选或先触发抓取。" />
          )}

          {!error && rows.length > 0 && activeTab === "overview" && <OverviewTab stats={stats} />}
          {!error && rows.length > 0 && activeTab === "trend" && <TrendTab stats={stats} />}
          {!error && rows.length > 0 && activeTab === "correlation" && (
            <CorrelationTab correlations={stats.correlations} />
          )}
          {!error && rows.length > 0 && activeTab === "ranking" && (
            <RankingTab stats={stats} onDramaClick={onDramaClick} />
          )}
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Tab 1: 数据概览
// ─────────────────────────────────────────────────────────────
function OverviewTab({ stats }) {
  const platformData = stats.byPlatform.slice(0, 8).map((d, i) => ({
    ...d,
    label: platformLabel(d.platform),
    fill: platformColor(d.platform, i),
  }));
  const rankTypeData = stats.byRankType.map((d, i) => ({
    ...d,
    fill: RANK_TYPE_COLORS[i % RANK_TYPE_COLORS.length],
  }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="匹配剧数" value={stats.total} suffix="部" tone="primary" />
        <Kpi label="平均 DHI" value={stats.avgDhi.toFixed(1)} />
        <Kpi label="最高 DHI" value={stats.maxDhi.toFixed(1)} />
        <Kpi label="覆盖平台" value={stats.byPlatform.length} suffix="个" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartBlock title="平台剧数分布" hint="柱长 = 当前筛选下该平台的剧数；颜色按平台区分。Tooltip 中的「平均 DHI」可对比哪个平台整体潜力更高。">
          {platformData.length === 0 ? (
            <ChartEmpty />
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(220, platformData.length * 36)}>
              <BarChart
                layout="vertical"
                data={platformData}
                margin={{ top: 6, right: 36, bottom: 6, left: 8 }}
              >
                <XAxis type="number" tick={{ fontSize: 11, fill: "#000" }} stroke="#cbd5e1" />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={86}
                  tick={{ fontSize: 11, fill: "#000" }}
                  stroke="#cbd5e1"
                />
                <Tooltip
                  cursor={{ fill: "rgba(0,191,138,0.08)" }}
                  isAnimationActive={false}
                  wrapperStyle={{ transition: "none" }}
                  content={
                    <KvTooltip
                      titleKey="label"
                      rows={[
                        { key: "count", label: "剧数", suffix: " 部" },
                        { key: "avg_heat", label: "平均 DHI", format: (v) => v.toFixed(1) },
                      ]}
                    />
                  }
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={18}>
                  {platformData.map((d) => (
                    <Cell key={d.platform} fill={d.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartBlock>

        <ChartBlock title="栏位占比" hint="每条剧来自哪个推荐位（轮播 / 推荐栏 / 上新 等）。">
          {rankTypeData.length === 0 ? (
            <ChartEmpty />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Tooltip
                  isAnimationActive={false}
                  wrapperStyle={{ transition: "none" }}
                  content={
                    <KvTooltip
                      titleKey="rank_type"
                      rows={[{ key: "count", label: "剧数", suffix: " 部" }]}
                    />
                  }
                />
                <Pie
                  data={rankTypeData}
                  dataKey="count"
                  nameKey="rank_type"
                  cx="50%"
                  cy="50%"
                  innerRadius={48}
                  outerRadius={80}
                  paddingAngle={2}
                  label={({ rank_type, count }) => `${rank_type} ${count}`}
                  labelLine={false}
                  fontSize={11}
                >
                  {rankTypeData.map((d) => (
                    <Cell key={d.rank_type} fill={d.fill} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartBlock>
      </div>
    </div>
  );
}

function Kpi({ label, value, suffix, tone }) {
  return (
    <div className="rounded border border-[#ebeef5] bg-[#f7f8fa] px-4 py-3">
      <div className="text-xs text-black">{label}</div>
      <div className={`mt-1 text-xl font-bold tabular-nums ${tone === "primary" ? "text-brand" : "text-black"}`}>
        {value}
        {suffix && <span className="ml-1 text-xs font-normal text-black">{suffix}</span>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Tab 2: 趋势洞察
// ─────────────────────────────────────────────────────────────
function TrendTab({ stats }) {
  return (
    <div className="space-y-4">
      <ChartBlock
        title="标签热度散点（选品罗盘）"
        hint="X 轴 = 该标签当前剧数（市场供给），Y 轴 = 该标签平均 DHI（市场反馈）。中位虚线把图分成四个象限：左上=蓝海机会，右上=热门赛道，右下=红海拥挤，左下=冷门。气泡颜色越深表示 DHI 越高。"
      >
        {stats.topTags.length === 0 ? (
          <ChartEmpty />
        ) : (
          <TagScatter items={stats.topTags} />
        )}
      </ChartBlock>

      <ChartBlock
        title="平台 × 栏位 热力图"
        hint="单元格颜色越深表示该平台 × 栏位组合的平均 DHI 越高，主数字=平均 DHI，下方 ×N 为剧数。"
      >
        {stats.heatmap.length === 0 ? (
          <ChartEmpty />
        ) : (
          <PlatformRankHeatmap items={stats.heatmap} />
        )}
      </ChartBlock>
    </div>
  );
}

function TagScatter({ items }) {
  const counts = items.map((d) => d.count);
  const heats = items.map((d) => d.avg_heat);
  const medianCount = median(counts);
  const medianHeat = median(heats);
  const maxCount = Math.max(...counts, 1);

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={360}>
        <ScatterChart margin={{ top: 16, right: 24, bottom: 32, left: 24 }}>
          <XAxis
            type="number"
            dataKey="count"
            name="剧数"
            tick={{ fontSize: 11, fill: "#000" }}
            stroke="#cbd5e1"
            label={{
              value: "市场供给（剧数 →）",
              position: "insideBottom",
              offset: -8,
              fill: "#000",
              fontSize: 11,
            }}
            domain={[0, Math.ceil(maxCount * 1.1)]}
          />
          <YAxis
            type="number"
            dataKey="avg_heat"
            name="平均 DHI"
            tick={{ fontSize: 11, fill: "#000" }}
            stroke="#cbd5e1"
            label={{
              value: "市场反馈（平均 DHI ↑）",
              angle: -90,
              position: "insideLeft",
              fill: "#000",
              fontSize: 11,
            }}
            domain={[0, 100]}
          />
          <ZAxis range={[60, 60]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3", stroke: "#cbd5e1" }}
            isAnimationActive={false}
            wrapperStyle={{ transition: "none" }}
            content={
              <KvTooltip
                titleKey="tag"
                rows={[
                  { key: "count", label: "剧数", suffix: " 部" },
                  { key: "avg_heat", label: "平均 DHI", format: (v) => v.toFixed(1) },
                ]}
              />
            }
          />
          <ReferenceLine x={medianCount} stroke="#cbd5e1" strokeDasharray="4 4" />
          <ReferenceLine y={medianHeat} stroke="#cbd5e1" strokeDasharray="4 4" />
          <Scatter
            data={items}
            fill="#00BF8A"
            shape={(props) => {
              const { cx, cy, payload } = props;
              const color = heatColor(payload.avg_heat);
              return (
                <g>
                  <circle cx={cx} cy={cy} r={6} fill={color} stroke="#00A877" strokeWidth={1} opacity={0.85} />
                  <text x={cx + 8} y={cy + 4} fontSize={10} fill="#000">
                    {payload.tag}
                  </text>
                </g>
              );
            }}
          />
        </ScatterChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0">
        <QuadrantLabel className="left-[8%] top-[8%]" tone="primary">蓝海机会（少而精）</QuadrantLabel>
        <QuadrantLabel className="right-[8%] top-[8%]" tone="primary">热门赛道（多而火）</QuadrantLabel>
        <QuadrantLabel className="left-[8%] bottom-[18%]" tone="muted">冷门</QuadrantLabel>
        <QuadrantLabel className="right-[8%] bottom-[18%]" tone="muted">红海拥挤</QuadrantLabel>
      </div>
    </div>
  );
}

function QuadrantLabel({ className, tone, children }) {
  const cls = tone === "primary" ? "bg-brand-light text-brand" : "bg-[#f1f5f9] text-black";
  return (
    <span className={`absolute rounded px-2 py-0.5 text-[10px] font-medium ${cls} ${className}`}>
      {children}
    </span>
  );
}

function PlatformRankHeatmap({ items }) {
  const platforms = Array.from(new Set(items.map((d) => d.platform)));
  const rankTypes = Array.from(new Set(items.map((d) => d.rank_type)));
  const lookup = new Map();
  items.forEach((d) => lookup.set(`${d.platform}|${d.rank_type}`, d));

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full table-fixed text-xs text-black">
        <thead>
          <tr>
            <th className="w-24 border-b border-[#ebeef5] px-2 py-1.5 text-left font-semibold">平台＼栏位</th>
            {rankTypes.map((rt) => (
              <th
                key={rt}
                className="min-w-[88px] border-b border-[#ebeef5] px-2 py-1.5 text-center font-semibold"
                title={rt}
              >
                {rt}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {platforms.map((p) => (
            <tr key={p}>
              <td className="border-b border-[#ebeef5] px-2 py-1.5 text-left font-medium">
                {platformLabel(p)}
              </td>
              {rankTypes.map((rt) => {
                const cell = lookup.get(`${p}|${rt}`);
                if (!cell) {
                  return (
                    <td key={rt} className="border-b border-[#ebeef5] px-1 py-1">
                      <div className="h-10 rounded bg-[#fafafa]" />
                    </td>
                  );
                }
                return (
                  <td key={rt} className="border-b border-[#ebeef5] px-1 py-1">
                    <div
                      className="flex h-10 flex-col items-center justify-center rounded text-[11px]"
                      style={{ background: heatColor(cell.avg_heat) }}
                      title={`${platformLabel(p)} · ${rt}：${cell.count} 部 / 平均 DHI ${cell.avg_heat.toFixed(1)}`}
                    >
                      <div className="font-semibold tabular-nums">{cell.avg_heat.toFixed(1)}</div>
                      <div className="text-[10px] opacity-80">×{cell.count}</div>
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-2 flex items-center gap-2 text-[10px] text-black">
        <span>低 DHI</span>
        {[10, 30, 50, 70, 85, 95].map((s) => (
          <span key={s} className="inline-block h-3 w-6 rounded" style={{ background: heatColor(s) }} />
        ))}
        <span>高 DHI</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Tab 3: 标签搭配（主标签 × 副标签 → DHI / 资源位变化）
// ─────────────────────────────────────────────────────────────
function CorrelationTab({ correlations }) {
  // 默认选中第一个有数据的主标签，避免一进来就空状态
  const firstWithData =
    MAIN_ALIAS_LOOKUP.find((g) => correlations[g.key]?.baseline?.count > 0)?.key ||
    MAIN_ALIAS_LOOKUP[0].key;
  const [mainKey, setMainKey] = useState(firstWithData);
  const data = correlations[mainKey];

  return (
    <div className="space-y-4">
      <MainTagPicker selected={mainKey} onChange={setMainKey} correlations={correlations} />

      {!data || !data.baseline ? (
        <TabEmpty
          text={`当前筛选下找不到含「${data?.label || mainKey}」的剧，换个主标签或调整筛选。`}
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
            <Kpi
              label={`含「${data.label}」剧数`}
              value={data.baseline.count}
              suffix="部"
              tone="primary"
            />
            <Kpi label="主标签平均 DHI" value={data.baseline.avgDhi.toFixed(1)} />
            <Kpi
              label="主标签平均资源位"
              value={data.baseline.avgPos !== null ? `#${data.baseline.avgPos.toFixed(1)}` : "—"}
            />
          </div>

          {data.combos.length === 0 ? (
            <TabEmpty text={`含「${data.label}」的剧没有其他可对比的副标签。`} />
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
              <div className="lg:col-span-2">
                <ChartBlock
                  title={`「${data.label}」搭配辐射图`}
                  hint="中心 = 主标签，外圈节点 = 同框副标签。节点颜色越深 = 组合 DHI 越高；节点距中心越远 = 组合 DHI 比主标签单独时上升越多（向内则下降）；节点大小 = 同框次数；连线粗细 = 同框次数。"
                >
                  <TagConstellation mainLabel={data.label} combos={data.combos} />
                </ChartBlock>
              </div>
              <div className="lg:col-span-3">
                <ChartBlock
                  title={`「${data.label}」搭配明细（按同框次数排序）`}
                  hint="ΔDHI 绿色=该副标签同框时整体更热；Δ位置 ↑（绿色）= 同框时平均资源位更靠前（位置数字越小越好）；同框 1 部时数字仅供参考。"
                >
                  <ComboTable combos={data.combos} />
                </ChartBlock>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MainTagPicker({ selected, onChange, correlations }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-black opacity-70">主标签：</span>
      {MAIN_ALIAS_LOOKUP.map((g) => {
        const c = correlations[g.key]?.baseline?.count || 0;
        const active = g.key === selected;
        const disabled = c === 0;
        return (
          <button
            key={g.key}
            type="button"
            onClick={() => !disabled && onChange(g.key)}
            disabled={disabled}
            title={disabled ? `当前筛选下无含「${g.label}」剧` : undefined}
            className={`inline-flex h-7 items-center gap-1.5 rounded-full border px-3 text-xs transition-colors
              ${active
                ? "border-brand bg-brand text-white"
                : disabled
                  ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-300"
                  : "border-slate-200 bg-white text-black hover:border-brand hover:text-brand"
              }`}
          >
            {g.label}
            <span
              className={`tabular-nums text-[10px] ${active ? "opacity-90" : "opacity-60"}`}
            >
              ×{c}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * 辐射图：把主标签放中心，前 10 个副标签按角度均布在外圈。
 * - 角度：按 index 均匀分布（稳定布局，不会因数据微小变化抖动）
 * - 半径：基础环 baseR + 由 dhiDelta 归一化后微调（±28px），ΔDHI 越大节点越外
 * - 节点大小：随 count 线性放大
 * - 节点颜色：组合平均 DHI 决定（沿用 heatColor 色阶）
 * 用 SVG 自绘（recharts 没有合适的辐射 / 网络图原语）。
 */
function TagConstellation({ mainLabel, combos }) {
  const top = combos.slice(0, 10);
  if (top.length === 0) return <ChartEmpty />;

  const W = 380;
  const H = 380;
  const cx = W / 2;
  const cy = H / 2;
  const baseR = 128;
  const maxAbsDelta = Math.max(...top.map((c) => Math.abs(c.dhiDelta)), 1);
  const maxCount = Math.max(...top.map((c) => c.count), 1);

  const layout = top.map((c, i) => {
    const angle = (Math.PI * 2 * i) / top.length - Math.PI / 2;
    const r = baseR + (c.dhiDelta / maxAbsDelta) * 28;
    return {
      ...c,
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
      nodeR: 14 + Math.min(10, (c.count / maxCount) * 10),
      edgeW: Math.max(0.8, Math.min(3.5, (c.count / maxCount) * 3.5)),
    };
  });

  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[420px]">
        {/* baseline ring（参考圈：到这个圈表示组合 DHI 与主标签持平） */}
        <circle cx={cx} cy={cy} r={baseR} fill="none" stroke="#e5e7eb" strokeDasharray="4 4" />

        {/* 边 */}
        {layout.map((c) => (
          <line
            key={`edge-${c.tag}`}
            x1={cx}
            y1={cy}
            x2={c.x}
            y2={c.y}
            stroke="#cbd5e1"
            strokeWidth={c.edgeW}
            opacity={0.55}
          />
        ))}

        {/* 节点 */}
        {layout.map((c) => {
          const fill = heatColor(c.avgDhi);
          return (
            <g key={`node-${c.tag}`}>
              <title>
                {`${c.tag}\n同框 ${c.count} 部 · 组合 DHI ${c.avgDhi.toFixed(1)} (${c.dhiDelta >= 0 ? "+" : ""}${c.dhiDelta.toFixed(1)})`}
              </title>
              <circle
                cx={c.x}
                cy={c.y}
                r={c.nodeR}
                fill={fill}
                stroke="#00A877"
                strokeWidth={1}
                opacity={0.95}
              />
              <text
                x={c.x}
                y={c.y + 3}
                textAnchor="middle"
                fontSize={10}
                fill="#000"
                style={{ pointerEvents: "none" }}
              >
                {c.tag.length > 5 ? `${c.tag.slice(0, 5)}…` : c.tag}
              </text>
              <text
                x={c.x}
                y={c.y + c.nodeR + 11}
                textAnchor="middle"
                fontSize={9}
                fill="#475569"
                style={{ pointerEvents: "none" }}
              >
                ×{c.count}
              </text>
            </g>
          );
        })}

        {/* 中心主标签 */}
        <circle cx={cx} cy={cy} r={36} fill="#00BF8A" stroke="#00A877" strokeWidth={1.5} />
        <text
          x={cx}
          y={cy + 4}
          textAnchor="middle"
          fontSize={12}
          fontWeight={700}
          fill="#fff"
          style={{ pointerEvents: "none" }}
        >
          {mainLabel.length > 4 ? `${mainLabel.slice(0, 4)}…` : mainLabel}
        </text>
      </svg>

      <div className="mt-1 flex flex-wrap items-center justify-center gap-3 text-[10px] text-black opacity-70">
        <span>← 内圈：组合 DHI 低于主标签</span>
        <span>•</span>
        <span>外圈 →：组合 DHI 高于主标签</span>
      </div>
    </div>
  );
}

function ComboTable({ combos }) {
  const items = combos.slice(0, 14);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs text-black">
        <thead className="bg-[#f7f8fa]">
          <tr>
            <th className="px-2 py-1.5 text-left font-semibold">搭配标签</th>
            <th className="px-2 py-1.5 text-right font-semibold">同框</th>
            <th className="px-2 py-1.5 text-right font-semibold">组合平均 DHI</th>
            <th className="px-2 py-1.5 text-right font-semibold">Δ DHI</th>
            <th className="px-2 py-1.5 text-right font-semibold">平均位置</th>
            <th className="px-2 py-1.5 text-right font-semibold">Δ 位置</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => {
            const dhiPos = c.dhiDelta >= 0;
            const posUp = c.posDelta !== null && c.posDelta >= 0;
            return (
              <tr key={c.tag} className="border-t border-[#ebeef5] hover:bg-[#fafbfc]">
                <td className="px-2 py-1.5">
                  <span
                    className="inline-block rounded px-2 py-0.5 text-[11px]"
                    style={{ background: heatColor(c.avgDhi), color: "#0f172a" }}
                  >
                    {c.tag}
                  </span>
                </td>
                <td className="px-2 py-1.5 text-right tabular-nums">×{c.count}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{c.avgDhi.toFixed(1)}</td>
                <td
                  className={`px-2 py-1.5 text-right font-medium tabular-nums ${
                    dhiPos ? "text-emerald-600" : "text-red-500"
                  }`}
                >
                  {dhiPos ? "+" : ""}
                  {c.dhiDelta.toFixed(1)}
                </td>
                <td className="px-2 py-1.5 text-right tabular-nums">
                  {c.avgPos !== null ? `#${c.avgPos.toFixed(1)}` : "—"}
                </td>
                <td
                  className={`px-2 py-1.5 text-right font-medium tabular-nums ${
                    c.posDelta === null ? "" : posUp ? "text-emerald-600" : "text-red-500"
                  }`}
                >
                  {c.posDelta === null
                    ? "—"
                    : posUp
                      ? `↑ ${c.posDelta.toFixed(1)}`
                      : `↓ ${Math.abs(c.posDelta).toFixed(1)}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {combos.length > items.length && (
        <div className="mt-2 text-right text-[10px] text-black opacity-60">
          仅显示前 {items.length} 项（共 {combos.length} 个搭配标签）
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Tab 4: 表现榜单
// ─────────────────────────────────────────────────────────────
function RankingTab({ stats, onDramaClick }) {
  const items = stats.top;
  if (items.length === 0) return <TabEmpty text="当前筛选条件下无热度数据可排序。" />;

  const chartData = items.map((d, i) => ({
    ...d,
    rank: i + 1,
    label: `#${i + 1} ${truncate(d.title, 28)}`,
    fill: platformColor(d.platform, i),
  }));

  const platformLegend = Array.from(new Set(items.map((d) => d.platform)));

  return (
    <ChartBlock
      title={`当前筛选 TOP ${items.length}（按热度排序，点击柱体看详情）`}
      hint="柱长 = heat_score；同色柱体来自同一平台。"
    >
      <ResponsiveContainer width="100%" height={Math.max(360, items.length * 28)}>
        <BarChart
          layout="vertical"
          data={chartData}
          margin={{ top: 6, right: 48, bottom: 6, left: 8 }}
        >
          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: "#000" }} stroke="#cbd5e1" />
          <YAxis
            type="category"
            dataKey="label"
            width={260}
            tick={{ fontSize: 11, fill: "#000" }}
            interval={0}
            stroke="#cbd5e1"
          />
          <Tooltip
            cursor={{ fill: "rgba(0,191,138,0.08)" }}
            isAnimationActive={false}
            wrapperStyle={{ transition: "none" }}
            content={<DramaTooltip />}
          />
          <Bar
            dataKey="heat_score"
            radius={[0, 4, 4, 0]}
            barSize={16}
            cursor="pointer"
            onClick={(d) => onDramaClick && onDramaClick(d.payload || d)}
          >
            {chartData.map((d) => (
              <Cell key={d.id} fill={d.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-black">
        {platformLegend.map((p, i) => (
          <span key={p} className="inline-flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: platformColor(p, i) }} />
            {platformLabel(p)}
          </span>
        ))}
      </div>
    </ChartBlock>
  );
}

function DramaTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded border border-[#ebeef5] bg-white px-3 py-2 text-xs text-black shadow-[0_8px_24px_rgba(15,23,42,0.12)]">
      <div className="font-semibold">{d.title}</div>
      <div className="mt-1 text-[11px]">
        {platformLabel(d.platform)} · {d.rank_type || "未分类"} · #{d.rank_in_platform}
      </div>
      <div className="mt-1 text-[11px]">
        热度 <span className="font-semibold text-brand">{(d.heat_score || 0).toFixed(1)}</span>
        {d.episodes ? ` · ${d.episodes} 集` : ""}
      </div>
      <div className="mt-1 text-[10px] opacity-70">点击查看详情</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// 公共小组件
// ─────────────────────────────────────────────────────────────
function ChartBlock({ title, hint, children }) {
  return (
    <div className="rounded border border-[#ebeef5] bg-white p-3">
      <div className="mb-2">
        <div className="text-sm font-semibold text-black">{title}</div>
        {hint && <div className="mt-0.5 text-xs text-black opacity-70">{hint}</div>}
      </div>
      {children}
    </div>
  );
}

function ChartEmpty() {
  return (
    <div className="flex h-40 items-center justify-center text-xs text-black opacity-60">
      暂无足够数据
    </div>
  );
}

function TabEmpty({ text }) {
  return (
    <div className="flex h-40 flex-col items-center justify-center gap-2 rounded bg-[#f7f8fa] text-xs text-black">
      <BarChart3 size={18} strokeWidth={1.7} className="opacity-50" />
      <div>{text}</div>
    </div>
  );
}

function TabError({ message }) {
  return (
    <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
      加载失败：{message}
    </div>
  );
}

function TabSkeleton({ kind }) {
  const blocks = kind === "overview" ? 2 : kind === "trend" ? 2 : 1;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded bg-slate-100" />
        ))}
      </div>
      {Array.from({ length: blocks }).map((_, i) => (
        <div key={i} className="h-56 animate-pulse rounded bg-slate-100" />
      ))}
    </div>
  );
}

function KvTooltip({ active, payload, titleKey, rows }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded border border-[#ebeef5] bg-white px-3 py-2 text-xs text-black shadow-[0_8px_24px_rgba(15,23,42,0.12)]">
      <div className="font-semibold">{d[titleKey]}</div>
      {rows.map((r) => {
        const raw = d[r.key];
        const formatted = r.format ? r.format(raw) : raw;
        return (
          <div key={r.key} className="mt-0.5">
            {r.label}：<span className="font-medium">{formatted}{r.suffix || ""}</span>
          </div>
        );
      })}
    </div>
  );
}
