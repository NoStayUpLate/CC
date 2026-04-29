import { useEffect, useRef, useState } from "react";

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
        className={`h-full w-full max-w-[720px] overflow-y-auto bg-white border-l border-zw-border shadow-[-12px_0_36px_rgba(15,23,42,0.18)]
                    transition-all duration-500 ease-out transform
                    ${isClosing ? "translate-x-full opacity-0" : "translate-x-0 opacity-100"}`}
      >
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[#ebeef5] bg-white px-6 py-5">
          <div>
            <h3 className="text-lg font-bold text-black">{drama.title}</h3>
            <p className="text-xs text-black mt-1">
              平台 {drama.platform} · {drama.rank_type || "未分类"} · 资源位位置 #{drama.rank_in_platform}
            </p>
          </div>
          <button
            onClick={closeWithAnimation}
            className="flex h-8 w-8 items-center justify-center rounded bg-slate-100 text-xl leading-none text-black hover:bg-brand-light hover:text-brand"
          >
            ×
          </button>
        </div>

        <div className="space-y-5 px-6 py-5">
          {drama.cover_url && (
            <div className="mx-auto aspect-[3/4] w-full max-w-[220px] overflow-hidden rounded border border-zw-border bg-slate-100">
              <img
                src={drama.cover_url}
                alt={`${drama.title || "短剧"}封面`}
                loading="lazy"
                className="h-full w-full object-cover"
              />
            </div>
          )}

          <Section title="短剧简介">
            <p className="text-sm leading-relaxed text-black">
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

          <Section title="基础信息">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Info label="热度分" value={(drama.heat_score || 0).toFixed(1)} />
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
              className="inline-flex rounded bg-brand px-4 py-2 text-sm text-black hover:bg-brand-dark"
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
      <h4 className="text-sm font-semibold text-black">{title}</h4>
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
