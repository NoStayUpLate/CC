import { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ExternalLink, Info } from "lucide-react";

/**
 * DHI 算法悬浮提示，挂在表头 DHI 列名右侧。
 *
 * 注意：触发器位于 <table> 内，而 table 外层有 overflow-hidden、内层有
 * overflow-x-auto（CSS 规范让 Y 轴也变成 auto-clip），单纯的 group-hover +
 * absolute 弹窗会被祖先 clip 掉；上层 App.jsx 的 transition 容器又用了
 * translate-y-* 创建 transform context，连 position:fixed 都会被该容器收编。
 *
 * 唯一干净解：把弹窗内容用 React Portal 投到 document.body，并在触发器
 * onMouseEnter/Leave 里同步开关状态，绕过所有祖先 clip。其他 tooltip
 * （非 overflow-hidden 容器内）继续走 CSS group-hover 即可，不必改造。
 */
function DhiInfoTooltip() {
  const triggerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!open) return;
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setPos({ top: r.top, left: r.left + r.width / 2 });
  }, [open]);

  return (
    <>
      <span
        ref={triggerRef}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="ml-1 inline-flex cursor-default items-center align-middle text-black hover:text-brand transition-colors duration-200"
      >
        <Info size={12} strokeWidth={1.5} />
      </span>
      {open && createPortal(
        <div
          // viewport 坐标：top = 触发器顶 - 8px gap；left = 触发器水平中点
          // transform 把弹窗往左、向上拉成"在触发器上方居中"
          style={{
            position: "fixed",
            top: pos.top - 8,
            left: pos.left,
            transform: "translate(-50%, -100%)",
            zIndex: 100,
          }}
          className="w-[460px] rounded-lg border border-[#ebeef5] bg-white p-4 space-y-3 text-left font-normal shadow-[0_12px_36px_rgba(15,23,42,0.12)]"
        >
          <div className="rounded border border-[#ebeef5] bg-[#f7f8fa] px-3 py-2 text-xs text-black">
            DHI = S_tag × 0.45 + S_position × 0.35 + S_recency × 0.20
          </div>
          <ul className="ml-4 list-disc space-y-1 text-xs leading-relaxed text-black">
            <li><strong>S_tag</strong>：题材匹配度，命中 S 级标签 +25 / A 级 +12，基线 50，cap 100</li>
            <li><strong>S_position</strong>：资源位强度，按平台内名次线性换算（第 1 名 100，每后退 -8）</li>
            <li><strong>S_recency</strong>：数据新鲜度，距今 1 天 -10，10 天前归零</li>
          </ul>
          {/* 双层向下三角：外灰边 + 内白填，pointer-events-none 防 hover 抖动 */}
          <span
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-full h-0 w-0 -translate-x-1/2 border-l-[7px] border-r-[7px] border-t-[7px] border-l-transparent border-r-transparent border-t-[#dcdfe6]"
          />
          <span
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-full -mt-px h-0 w-0 -translate-x-1/2 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-white"
          />
        </div>,
        document.body
      )}
    </>
  );
}

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
      {Array.from({ length: 8 }).map((__, cellIdx) => (
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
          className="max-w-[86px] truncate rounded bg-brand-light px-1.5 py-0.5 text-[11px] text-brand"
          title={tag}
        >
          {tag}
        </span>
      ))}
      {hidden.length > 0 && (
        <span className="group relative inline-flex">
          <span className="rounded bg-brand-light px-1.5 py-0.5 text-[11px] text-brand cursor-default">
            +{hidden.length}
          </span>
          {/* 向上弹出的 tooltip：白底圆角，内含绿色芯片，底部带向下小三角 */}
          <span className="invisible absolute left-1/2 -translate-x-1/2 bottom-[calc(100%+8px)] z-30 min-w-[140px] max-w-[280px] rounded-lg border border-[#dcdfe6] bg-white px-3 py-2 opacity-0 shadow-[0_8px_24px_rgba(15,23,42,0.12)] transition-opacity group-hover:visible group-hover:opacity-100">
            <span className="flex flex-wrap gap-1.5">
              {hidden.map((t) => (
                <span
                  key={t}
                  className="rounded bg-brand-light px-2 py-0.5 text-[11px] text-brand whitespace-nowrap"
                >
                  {t}
                </span>
              ))}
            </span>
            {/* 向下三角：先画浅灰边线层，再画白色填充层覆盖 */}
            <span
              aria-hidden
              className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full h-0 w-0 border-l-[7px] border-r-[7px] border-t-[7px] border-l-transparent border-r-transparent border-t-[#dcdfe6]"
            />
            <span
              aria-hidden
              className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full -mt-px h-0 w-0 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-white"
            />
          </span>
        </span>
      )}
    </div>
  );
}

export default function DramaTable({ dramas, loading, onTitleClick, footer }) {
  const isEmpty = !loading && (!dramas || dramas.length === 0);

  // sticky thead 关键约束：
  // 1) 外层 wrapper ❌ 不能有 overflow-hidden，会困住 thead
  // 2) 表格与 thead 之间 ❌ 不能有任何 overflow 容器（包括 overflow-x-auto，
  //    它会被规范隐式补成 overflow-y-auto，再次困住 thead）
  // 3) 横向溢出由 <main> 自行处理（main 的 overflow-y-auto 已经
  //    隐式让 overflow-x 也是 auto，窄屏会自动出现横向滚动条）
  // 4) thead sticky top-0 z-20：粘在视口顶端，z-20 低于 modal/tooltip/header
  return (
    <div className="rounded-sm border border-[#ebeef5] bg-white">
      <table className="min-w-[940px] w-full table-fixed text-left text-xs text-black">
        <thead className="sticky top-0 z-20 bg-[#f2f3f5] text-black shadow-[0_1px_0_#ebeef5]">
            <tr className="h-[68px]">
              <th className="w-[320px] px-3 font-semibold">短剧名称</th>
              <th className="w-[110px] px-3 font-semibold">平台</th>
              <th className="w-[110px] px-3 font-semibold">栏目</th>
              <th className="w-[100px] px-3 text-right font-semibold">资源位位置</th>
              <th className="w-[90px] px-3 text-right font-semibold">
                <span className="inline-flex items-center justify-end gap-1">
                  DHI
                  <DhiInfoTooltip />
                </span>
              </th>
              <th className="w-[80px] px-3 text-right font-semibold">集数</th>
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
                  <td
                    className="px-3 text-right font-semibold tabular-nums text-brand"
                    title={`题材 ${(drama.s_tag || 0).toFixed(1)} · 资源位 ${(drama.s_position || 0).toFixed(1)} · 新鲜度 ${(drama.s_recency || 0).toFixed(1)}`}
                  >
                    {(drama.dhi || 0).toFixed(1)}
                  </td>
                  <td className="px-3 text-right tabular-nums text-black">{drama.episodes ?? "-"}</td>
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

      {isEmpty && (
        <div className="border-t border-[#ebeef5] py-12 text-center text-sm text-black">
          暂无匹配短剧数据，请先触发抓取。
        </div>
      )}

      {/* 表格页脚（分页器） —— 与表格共用同一个 bordered 容器，
          通过 border-t 一根细线区隔，视觉上是同一个可视化单元 */}
      {footer && !isEmpty && (
        <div className="border-t border-[#ebeef5] bg-white">
          {footer}
        </div>
      )}
    </div>
  );
}
