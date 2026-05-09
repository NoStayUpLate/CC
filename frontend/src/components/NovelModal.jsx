/**
 * NovelModal 组件
 *
 * Props:
 *   novel   - NovelOut 对象（null 时不渲染）
 *   onClose - () => void
 */
import { useState, useEffect, useRef, useCallback, useLayoutEffect } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { fetchNovel } from "../api/client";
import WordCloud from "./WordCloud";

const ENTER_LEAVE_MS = 260;
const SUMMARY_CLAMP_LINES = 12;

/** 简介展示组件：超过 12 行折叠，提供展开/收起按钮。 */
function SummaryWithCollapse({ text }) {
  const ref = useRef(null);
  const [expanded, setExpanded] = useState(false);
  const [overflowing, setOverflowing] = useState(false);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    // collapse 状态下用 scrollHeight 判定是否被截断（line-clamp 不影响 scrollHeight）
    setOverflowing(el.scrollHeight - el.clientHeight > 1);
  }, [text]);

  if (!text) {
    return <p className="text-xs italic text-black">暂无数据</p>;
  }

  const clampStyle = expanded
    ? undefined
    : {
        display: "-webkit-box",
        WebkitLineClamp: SUMMARY_CLAMP_LINES,
        WebkitBoxOrient: "vertical",
        overflow: "hidden",
      };

  return (
    <div className="space-y-2">
      <p
        ref={ref}
        className="text-xs text-black leading-relaxed whitespace-pre-line"
        style={clampStyle}
      >
        {text}
      </p>
      {overflowing && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="inline-flex items-center gap-1 text-xs text-brand hover:text-brand-dark transition-colors"
        >
          {expanded ? "收起" : "展开全部"}
          {expanded ? (
            <ChevronUp size={12} strokeWidth={1.7} />
          ) : (
            <ChevronDown size={12} strokeWidth={1.7} />
          )}
        </button>
      )}
    </div>
  );
}

function ghiLevel(ghi) {
  if (ghi >= 80) return { label: "S 级爆款潜力", color: "text-brand" };
  if (ghi >= 65) return { label: "A 级高潜力", color: "text-blue-500" };
  if (ghi >= 45) return { label: "B 级待观察", color: "text-amber-500" };
  return { label: "C 级低潜力", color: "text-black" };
}

function ScoreBar({ label, value, hint, colorClass = "bg-brand" }) {
  const pct = Math.min(Math.max(value, 0), 100);
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center text-xs">
        <span className="text-black">{label}</span>
        <span className="font-bold text-black tabular-nums">{pct.toFixed(1)}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full progress-bar-animated ${colorClass}`}
          style={{ "--target-width": `${pct}%`, width: `${pct}%` }}
        />
      </div>
      {hint && <p className="text-xs text-black leading-relaxed">{hint}</p>}
    </div>
  );
}

const ADAPT_HINT = {
  en: "英语市场：狼人题材极度契合 AI 短剧（降低变身特效成本）；霸总类适合真人短剧。",
  ja: "日语市场：恶役千金具有极强视觉符号感，推荐 AI 风格化处理宫廷场景。",
  ko: "韩语市场：强调「打脸」逻辑和身份反转，适合真人 / AI 兼顾。",
  fr: "法语市场：侧重氛围感营造，推荐真人短剧表现心理张力。",
};

export default function NovelModal({ novel, onClose }) {
  const [keywords, setKeywords] = useState(null);
  const [kwLoading, setKwLoading] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const closeTimerRef = useRef(null);

  const closeWithAnimation = useCallback(() => {
    setIsClosing(true);
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
    }
    closeTimerRef.current = setTimeout(() => {
      onClose();
    }, ENTER_LEAVE_MS);
  }, [onClose]);

  useEffect(() => {
    if (!novel) return;
    const handler = (e) => e.key === "Escape" && closeWithAnimation();
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [novel, closeWithAnimation]);

  useEffect(() => {
    document.body.style.overflow = novel ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [novel]);

  useEffect(() => {
    if (novel) {
      setIsClosing(false);
    }
    return undefined;
  }, [novel]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) {
        clearTimeout(closeTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!novel?.id) return;
    setKeywords(null);
    setKwLoading(true);
    fetchNovel(novel.id)
      .then((data) => setKeywords(data.top_keywords ?? null))
      .catch(() => setKeywords(null))
      .finally(() => setKwLoading(false));
  }, [novel?.id]);

  if (!novel) return null;

  const level = ghiLevel(novel.ghi);
  const adaptHint = ADAPT_HINT[novel.lang] || "暂无特定改编建议。";

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 backdrop-blur-sm
                 transition-all duration-300 ease-out
                 ${isClosing ? "bg-slate-900/0 opacity-0" : "bg-slate-900/35 opacity-100"}`}
      onClick={(e) => e.target === e.currentTarget && closeWithAnimation()}
    >
      <div
        className={`bg-white border border-zw-border rounded-lg
                   w-full max-w-2xl max-h-[calc(100dvh-24px)] sm:max-h-[calc(100dvh-48px)] overflow-y-auto
                   shadow-[0_18px_60px_rgba(15,23,42,0.18)]
                   transition-all duration-300 ease-out transform
                   ${isClosing ? "opacity-0 scale-95 translate-y-2" : "opacity-100 scale-100 translate-y-0"}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="sticky top-0 bg-white
                        flex items-center justify-between px-6 py-4 rounded-t-lg z-10">
          <h2 className="text-base font-bold text-black pr-4 line-clamp-1">
            {novel.title || "（无标题）"}
          </h2>
          <button
            onClick={closeWithAnimation}
            className="flex-shrink-0 w-8 h-8 rounded bg-slate-100 hover:bg-brand-light
                       flex items-center justify-center text-black hover:text-brand
                       transition-colors duration-200 text-base leading-none"
            aria-label="关闭"
          >
            ×
          </button>
        </div>

        {/* 内容区 */}
        <div className="px-6 py-5 space-y-6">
          {/* 元信息行 */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="px-3 py-1 bg-slate-100 rounded text-black">
              {novel.platform}
            </span>
            <span className="px-3 py-1 bg-slate-100 rounded text-black">
              {novel.lang?.toUpperCase()}
            </span>
            {novel.has_hook && (
              <span className="px-3 py-1 bg-brand-light text-brand rounded font-medium">
                黄金三秒命中
              </span>
            )}
            <span className={`px-3 py-1 rounded font-semibold ${level.color} bg-slate-100`}>
              {level.label}
            </span>
          </div>

          {/* 简介 */}
          <div>
            <h3 className="text-xs text-black mb-2 font-medium">小说简介</h3>
            <SummaryWithCollapse text={novel.summary} />
          </div>

          {/* 标签 */}
          {novel.tags?.length > 0 && (
            <div>
              <h3 className="text-xs text-black mb-2 font-medium">题材标签</h3>
              <div className="flex flex-wrap gap-2">
                {novel.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs px-2.5 py-1 bg-slate-100 text-black rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* GHI 算法分项 */}
          <div>
            <div className="flex items-baseline gap-3 mb-4">
              <h3 className="text-xs text-black font-medium">AI 短剧适配度 (GHI)</h3>
              <span className="text-2xl font-black text-brand tabular-nums">
                {novel.ghi}
              </span>
              <span className="text-xs text-black">/ 100</span>
            </div>
            <div className="space-y-4">
              <ScoreBar
                label="基础热度 S_popular (×0.3)"
                value={novel.s_popular}
                hint={`基于阅读量对数标准化。当前权重贡献：${(novel.s_popular * 0.3).toFixed(2)} 分`}
                colorClass="bg-blue-400"
              />
              <ScoreBar
                label="互动热度 S_engage (×0.3)"
                value={novel.s_engage}
                hint={`点赞/阅读比 × 语种系数（韩语×1.2 / 英语×0.8）。贡献：${(novel.s_engage * 0.3).toFixed(2)} 分`}
                colorClass="bg-purple-400"
              />
              <ScoreBar
                label="改编适配 S_adapt (×0.4)"
                value={novel.s_adapt}
                hint={`S 级标签（狼人/重生/复仇/恶役千金）90-100 分；≥2 个 S 级额外+15%。贡献：${(novel.s_adapt * 0.4).toFixed(2)} 分`}
                colorClass="bg-brand"
              />
            </div>
          </div>

          {/* 核心冲突点扫描（关键词云）*/}
          <div className="rounded-lg border border-zw-border bg-[#f7f8fa] p-4">
            <h3 className="text-xs text-black mb-3 font-medium">
              核心冲突点扫描
              <span className="ml-2 text-black font-normal">（前三章高频词）</span>
            </h3>
            {kwLoading ? (
              <div className="py-4 flex justify-center">
                <span className="text-xs text-black animate-pulse">正在分析章节文本…</span>
              </div>
            ) : (
              <WordCloud keywords={keywords} />
            )}
          </div>

          {/* 热度逻辑提示 */}
          <div className="rounded-lg border border-zw-border bg-[#f7f8fa] p-4">
            <h3 className="text-xs text-black mb-1.5 font-medium">热度逻辑提示</h3>
            <p className="text-xs text-black leading-relaxed">{adaptHint}</p>
          </div>

          {/* 数据统计 */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "累计阅读量", value: (novel.views || 0).toLocaleString("zh-CN") },
              { label: "点赞 / 互动量", value: (novel.likes || 0).toLocaleString("zh-CN") },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg border border-zw-border bg-[#f7f8fa] p-3 text-center">
                <div className="text-xs text-black mb-1">{label}</div>
                <div className="text-lg font-bold text-black tabular-nums">{value}</div>
              </div>
            ))}
          </div>

          {/* 访问原站按钮 */}
          <a
            href={novel.original_url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center py-3 rounded font-semibold text-xs
                       bg-brand hover:bg-brand-dark text-black transition-colors"
          >
            访问原站查看全文
          </a>
        </div>
      </div>
    </div>
  );
}
