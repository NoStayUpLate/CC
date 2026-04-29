import { LineChart, ExternalLink } from "lucide-react";

// 平台 Badge 颜色映射（浅色主题）
const PLATFORM_COLOR = {
  wattpad: "text-black border-slate-300",
  royal_road: "text-black border-slate-300",
  syosetu: "text-black border-slate-300",
  kakaopage: "text-black border-slate-300",
  naver: "text-black border-slate-300",
  webnovel: "text-black border-slate-300",
};

const LANG_LABEL = { en: "英语", ja: "日语", ko: "韩语", fr: "法语" };

function truncate(text, len = 100) {
  if (!text) return "";
  return text.length > len ? text.slice(0, len) + "…" : text;
}

function buildSparkPoints(values) {
  if (!values.length) return "";
  const max = Math.max(...values, 1);
  return values
    .map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * 100;
      const y = 100 - (v / max) * 100;
      return `${x},${y}`;
    })
    .join(" ");
}

export default function NovelCard({ novel, onClick }) {
  const platformCls =
    PLATFORM_COLOR[novel.platform] || "text-black border-slate-300";
  // CH 已预计算 s_popular / s_engage / s_adapt，这里仅做可视化映射，不在前端重算 GHI。
  const sparkPoints = buildSparkPoints([
    novel.s_popular || 0,
    novel.s_engage || 0,
    novel.s_adapt || 0,
  ]);
  const ghiDots = Math.max(0, Math.min(10, Math.round((novel.ghi || 0) / 10)));

  return (
    <div
      onClick={() => onClick(novel)}
      className="zw-card zw-card-hover group flex cursor-pointer flex-col gap-4"
    >
      {/* 顶部：平台 Badge + GHI 分 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`rounded border px-2 py-0.5 text-xs ${platformCls}`}>
            {novel.platform}
          </span>
          <span className="rounded border border-slate-200 px-2 py-0.5 text-xs text-black">
            {LANG_LABEL[novel.lang] || novel.lang?.toUpperCase()}
          </span>
          {novel.has_hook && (
            <span
              title="简介含身份反转/重生/复仇等强冲突关键词"
              className="rounded border border-brand bg-brand-light px-2 py-0.5 text-xs text-brand"
            >
              黄金三秒
            </span>
          )}
        </div>

        {/* GHI 分值 */}
        <div className="text-right flex-shrink-0">
          <div className="text-3xl font-semibold tracking-tight text-brand transition-colors duration-200 tabular-nums">
            {novel.ghi}
          </div>
          <div className="text-[10px] text-black leading-none">GHI</div>
        </div>
      </div>

      {/* 书名 */}
      <h3 className="text-base font-bold text-black leading-snug line-clamp-2">
        {novel.title || "（无标题）"}
      </h3>

      {/* 简介 */}
      <p className="text-sm text-black leading-relaxed flex-1">
        {truncate(novel.summary) || <span className="italic text-black">暂无简介</span>}
      </p>

      {/* 标签芯片 */}
      {novel.tags?.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {novel.tags.slice(0, 5).map((tag) => (
            <span
              key={tag}
              className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs text-black"
            >
              {tag}
            </span>
          ))}
          {novel.tags.length > 5 && (
            <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs text-black">
              +{novel.tags.length - 5}
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          {Array.from({ length: 10 }).map((_, idx) => (
            <span
              key={idx}
              className={`h-1.5 w-1.5 rounded-full ${idx < ghiDots ? "bg-brand" : "bg-slate-200"}`}
            />
          ))}
        </div>
        <div className="inline-flex items-center gap-1 text-brand">
          <LineChart size={14} strokeWidth={1.5} />
          <svg viewBox="0 0 100 100" className="h-5 w-14">
            <polyline
              points={sparkPoints}
              fill="none"
              stroke="#00BF8A"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      {/* 底部：阅读量 & 点赞 & 跳转链接 */}
      <div className="flex items-center justify-between gap-2 border-t border-zw-border pt-3">
        <div className="flex gap-4 text-xs text-black">
          <span>阅读 {(novel.views || 0).toLocaleString("zh-CN")}</span>
          <span>点赞 {(novel.likes || 0).toLocaleString("zh-CN")}</span>
        </div>
        {novel.original_url && (
          <a
            href={novel.original_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex flex-shrink-0 items-center gap-1 text-xs text-brand transition-colors duration-200 hover:text-brand-dark"
          >
            原站 <ExternalLink size={12} strokeWidth={1.5} />
          </a>
        )}
      </div>
    </div>
  );
}
