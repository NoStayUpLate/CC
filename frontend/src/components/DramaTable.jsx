import { ExternalLink } from "lucide-react";

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

function SkeletonRows() {
  return Array.from({ length: 8 }).map((_, idx) => (
    <tr key={idx} className="border-b border-[#ebeef5]">
      {Array.from({ length: 9 }).map((__, cellIdx) => (
        <td key={cellIdx} className="px-3 py-2">
          <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
        </td>
      ))}
    </tr>
  ));
}

function Tags({ tags = [] }) {
  const filtered = tags.filter((tag) => tag && !SECTION_TAGS.has(tag));
  const shown = filtered.slice(0, 3);
  const hidden = filtered.slice(3);
  if (!shown.length) return <span>-</span>;
  return (
    <div className="flex min-w-0 flex-wrap gap-1">
      {shown.map((tag) => (
        <span
          key={tag}
          className="max-w-[86px] truncate rounded border border-[#dcdfe6] bg-white px-1.5 py-0.5 text-[11px] text-black"
          title={tag}
        >
          {tag}
        </span>
      ))}
      {hidden.length > 0 && (
        <span className="group relative rounded border border-[#dcdfe6] bg-white px-1.5 py-0.5 text-[11px] text-black">
          +{hidden.length}
          <span className="invisible absolute left-0 top-[calc(100%+4px)] z-30 min-w-40 max-w-72 rounded border border-[#dcdfe6] bg-white p-2 text-left text-[11px] leading-5 text-black opacity-0 shadow-[0_8px_24px_rgba(15,23,42,0.12)] transition-opacity group-hover:visible group-hover:opacity-100">
            {hidden.join("、")}
          </span>
        </span>
      )}
    </div>
  );
}

export default function DramaTable({ dramas, loading, onTitleClick }) {
  const isEmpty = !loading && (!dramas || dramas.length === 0);

  return (
    <div className="overflow-hidden rounded-sm border border-[#ebeef5] bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-[1120px] w-full table-fixed text-left text-xs text-black">
          <thead className="bg-[#f2f3f5] text-black shadow-[0_1px_0_#ebeef5]">
            <tr className="h-10">
              <th className="w-[320px] px-3 font-semibold">短剧名称</th>
              <th className="w-[110px] px-3 font-semibold">平台</th>
              <th className="w-[110px] px-3 font-semibold">栏目</th>
              <th className="w-[100px] px-3 text-right font-semibold">资源位位置</th>
              <th className="w-[90px] px-3 text-right font-semibold">热度</th>
              <th className="w-[80px] px-3 text-right font-semibold">集数</th>
              <th className="w-[180px] px-3 font-semibold">标签</th>
              <th className="w-[110px] px-3 font-semibold">抓取日期</th>
              <th className="w-[90px] px-3 text-center font-semibold">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <SkeletonRows />
            ) : (
              dramas.map((drama) => (
                <tr
                  key={drama.id}
                  className="h-[68px] border-b border-[#ebeef5] bg-white hover:bg-[#f7f8fa]"
                >
                  <td className="px-3 py-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <div className="h-12 w-9 flex-shrink-0 overflow-hidden rounded border border-[#ebeef5] bg-[#f5f7fa]">
                        {drama.cover_url ? (
                          <img
                            src={drama.cover_url}
                            alt={`${drama.title || "短剧"}封面`}
                            loading="lazy"
                            className="h-full w-full object-cover"
                          />
                        ) : null}
                      </div>
                      <div className="min-w-0">
                        <button
                          type="button"
                          onClick={() => onTitleClick(drama)}
                          className="block max-w-full truncate text-left text-sm font-semibold text-black hover:text-brand"
                          title={drama.title}
                        >
                          {drama.title || "（无标题）"}
                        </button>
                        <div className="mt-1 max-w-[240px]">
                          <Tags tags={drama.tags || []} />
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 text-black">{PLATFORM_LABEL[drama.platform] || drama.platform}</td>
                  <td className="px-3 text-black">{drama.rank_type || "未分类"}</td>
                  <td className="px-3 text-right tabular-nums text-black">#{drama.rank_in_platform || "-"}</td>
                  <td className="px-3 text-right font-semibold tabular-nums text-brand">
                    {(drama.heat_score || 0).toFixed(1)}
                  </td>
                  <td className="px-3 text-right tabular-nums text-black">{drama.episodes ?? "-"}</td>
                  <td className="px-3 text-black">-</td>
                  <td className="px-3 text-black">{drama.crawl_date || "-"}</td>
                  <td className="px-3 text-center">
                    {drama.source_url ? (
                      <a
                        href={drama.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center gap-1 text-brand hover:text-brand-dark"
                      >
                        原站
                        <ExternalLink size={12} strokeWidth={1.6} />
                      </a>
                    ) : (
                      <span>-</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {isEmpty && (
        <div className="border-t border-[#ebeef5] py-12 text-center text-sm text-black">
          暂无匹配短剧数据，请先触发抓取。
        </div>
      )}
    </div>
  );
}
