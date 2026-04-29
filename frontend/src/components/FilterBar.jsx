import { Search, SlidersHorizontal } from "lucide-react";
import { MultiSelectFilter, SelectFilter } from "./DropdownFilter";

// 语种代码 → 显示名称映射
const LANG_LABEL = {
  en: "英语",
  ja: "日语",
  ko: "韩语",
  fr: "法语",
};

// 平台 → 显示名称映射
const PLATFORM_LABEL = {
  wattpad:    "Wattpad",
  royal_road: "Royal Road",
  syosetu:    "Syosetu",
  kakaopage:  "KakaoPage",
  naver:      "Naver",
  munpia:     "Munpia",
  webnovel:   "Webnovel",
  inkitt:     "Inkitt",
  alphapolis: "Alphapolis",
  delitoon:   "Delitoon",
};

export default function FilterBar({ filters, onChange, onSearch, platforms, langs, topTags }) {
  const platformOptions = (platforms || []).map((p) => ({
    val: p,
    label: PLATFORM_LABEL[p] || p,
  }));

  const langOptions = (langs || []).map((l) => ({
    val: l,
    label: LANG_LABEL[l] || l,
  }));

  const tagOptions = (topTags || []).map((t) => ({ val: t, label: t }));

  const resetFilters = () => {
    onChange("platform", "");
    onChange("lang", "");
    onChange("tags", "");
    onChange("title", "");
    onChange("rank_type", "");
  };

  return (
    <div className="zw-card">
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-black">
        <SlidersHorizontal size={14} strokeWidth={1.5} />
        精准筛选
      </div>
      <div className="grid grid-cols-1 gap-x-6 gap-y-3 lg:grid-cols-2 xl:grid-cols-4">
        {platformOptions.length > 0 && (
          <SelectFilter
            label="平台"
            options={platformOptions}
            value={filters.platform || ""}
            onChange={(v) => onChange("platform", v)}
          />
        )}

        {langOptions.length > 0 && (
          <SelectFilter
            label="语种"
            options={langOptions}
            value={filters.lang || ""}
            onChange={(v) => onChange("lang", v)}
          />
        )}

        <SelectFilter
          label="榜单"
          options={[
            { val: "daily",   label: "日榜" },
            { val: "weekly",  label: "周榜" },
            { val: "monthly", label: "月榜" },
          ]}
          value={filters.rank_type || ""}
          onChange={(v) => onChange("rank_type", v)}
        />

        {tagOptions.length > 0 && (
          <MultiSelectFilter
            label="标签"
            options={tagOptions}
            value={filters.tags || ""}
            onChange={(v) => onChange("tags", v)}
          />
        )}

        <div className="flex min-w-0 items-center gap-2">
          <span className="w-[5em] flex-shrink-0 text-xs font-semibold text-black">书名</span>
          <div className="relative flex-1">
            <Search
              size={14}
              strokeWidth={1.5}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-black"
            />
            <input
              type="text"
              placeholder="输入书名关键词..."
              value={filters.title || ""}
              onChange={(e) => onChange("title", e.target.value)}
              className="zw-field w-full pl-8"
            />
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2 md:pl-[calc(5em+8px)]">
        <button type="button" onClick={onSearch} className="zw-primary-btn">
          查询
        </button>
        <button
          type="button"
          onClick={resetFilters}
          className="zw-default-btn"
        >
          重置
        </button>
      </div>
    </div>
  );
}
