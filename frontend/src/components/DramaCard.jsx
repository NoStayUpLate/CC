import { LineChart, ExternalLink } from "lucide-react";

const PLATFORM_COLOR = {
  netshort: "text-black border-slate-300",
  reelshort: "text-black border-slate-300",
  dramabox: "text-black border-slate-300",
  dramareels: "text-black border-slate-300",
  dramawave: "text-black border-slate-300",
  shortmax: "text-black border-slate-300",
};

function buildSparkPoints(base = 0) {
  const v1 = Math.max(10, Math.min(100, base));
  const v2 = Math.max(8, Math.min(100, base * 0.88));
  const v3 = Math.max(6, Math.min(100, base * 0.96));
  const vals = [v1, v2, v3];
  const max = Math.max(...vals, 1);
  return vals
    .map((v, i) => `${(i / 2) * 100},${100 - (v / max) * 100}`)
    .join(" ");
}

export default function DramaCard({ drama, onClick }) {
  const platformCls = PLATFORM_COLOR[drama.platform] || "text-black border-slate-300";
  const sparkPoints = buildSparkPoints(drama.dhi || 0);

  return (
    <div
      onClick={() => onClick(drama)}
      className="zw-card zw-card-hover group flex cursor-pointer flex-col gap-4"
    >
      {drama.cover_url && (
        <div className="aspect-[3/4] w-full overflow-hidden rounded bg-slate-100 border border-zw-border">
          <img
            src={drama.cover_url}
            alt={`${drama.title || "短剧"}封面`}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-[1.02]"
          />
        </div>
      )}

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`rounded border px-2 py-0.5 text-xs ${platformCls}`}>
            {drama.platform}
          </span>
          <span className="rounded border border-brand bg-brand-light px-2 py-0.5 text-xs text-brand">
            {drama.rank_type || "未分类"}
          </span>
        </div>

        <div className="text-right">
          <div className="text-xs text-black">资源位位置</div>
          <div className="text-lg font-bold text-brand tabular-nums">#{drama.rank_in_platform}</div>
        </div>
      </div>

      <h3 className="text-base font-bold text-black leading-snug line-clamp-2">
        {drama.title || "（无标题）"}
      </h3>

      <p className="text-sm text-black leading-relaxed flex-1 line-clamp-3">
        {drama.summary || "暂无简介"}
      </p>

      {drama.tags?.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {drama.tags.map((tag) => (
            <span
              key={tag}
              className="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs text-black"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-end text-brand gap-1">
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

      <div className="flex items-center justify-between gap-2 border-t border-zw-border pt-3">
        <div className="flex gap-4 text-xs text-black">
          <span>DHI {(drama.dhi || 0).toFixed(1)}</span>
          <span>集数 {drama.episodes ?? "-"}</span>
        </div>
        {drama.source_url && (
          <a
            href={drama.source_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-xs text-brand hover:text-brand-dark transition-colors duration-200 flex items-center gap-1 flex-shrink-0"
          >
            来源 <ExternalLink size={12} strokeWidth={1.5} />
          </a>
        )}
      </div>
    </div>
  );
}
