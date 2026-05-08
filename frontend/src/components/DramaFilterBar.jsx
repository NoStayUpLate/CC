import { Search, SlidersHorizontal } from "lucide-react";
import { MultiSelectFilter } from "./DropdownFilter";

const LANG_LABEL = {
  en: "英语",
  ja: "日语",
  ko: "韩语",
  fr: "法语",
};

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

const RECOMMENDATION_OPTIONS = [
  { val: "轮播推荐", label: "轮播推荐" },
  { val: "顶部推荐", label: "顶部推荐" },
  { val: "推荐栏位", label: "推荐栏位" },
  { val: "近期热门", label: "近期热门" },
  { val: "热门榜单", label: "热门榜单" },
  { val: "当前热门", label: "当前热门" },
  { val: "最近上新", label: "最近上新" },
];

const PLATFORM_RECOMMENDATION_OPTIONS = {
  netshort: ["轮播推荐", "推荐栏位", "最近上新"],
  dramabox: ["顶部推荐", "推荐栏位", "近期热门"],
  reelshort: ["最近上新"],
  dramareels: ["轮播推荐", "推荐栏位", "最近上新"],
  dramawave: ["轮播推荐", "推荐栏位", "最近上新"],
  goodshort: ["近期热门", "推荐栏位", "热门榜单", "当前热门"],
  moboreels: ["近期热门", "推荐栏位", "最近上新"],
  shortmax: ["推荐栏位", "最近上新", "近期热门"],
};

const RECOMMENDATION_TAGS = new Set(RECOMMENDATION_OPTIONS.map((item) => item.val));

export default function DramaFilterBar({
  filters,
  onChange,
  onSearch,
  platforms,
  langs,
  topTags,
}) {
  const platformOptions = (platforms || []).map((p) => ({
    val: p,
    label: PLATFORM_LABEL[p] || p,
  }));

  const langOptions = (langs || []).map((l) => ({
    val: l,
    label: LANG_LABEL[l] || l,
  }));

  // 推荐栏位级联：取所选平台并集（多选时显示任意平台支持的栏位），
  // 没选平台时显示所有栏位。
  const selectedPlatforms = (filters.platform || "")
    .split(",").map((s) => s.trim()).filter(Boolean);
  const platformRecommendationValues = selectedPlatforms.length
    ? Array.from(new Set(
        selectedPlatforms.flatMap(
          (p) => PLATFORM_RECOMMENDATION_OPTIONS[p] || RECOMMENDATION_OPTIONS.map((it) => it.val)
        )
      ))
    : RECOMMENDATION_OPTIONS.map((item) => item.val);
  const recommendationOptions = RECOMMENDATION_OPTIONS.filter((item) =>
    platformRecommendationValues.includes(item.val)
  );
  // 多选模式下仅保留仍然可选的 rank_type，避免切换平台后留下"幽灵选中"
  const allowedRankTypes = new Set(recommendationOptions.map((it) => it.val));
  const filteredRankTypeValue = (filters.rank_type || "")
    .split(",").map((s) => s.trim()).filter(Boolean)
    .filter((v) => allowedRankTypes.has(v))
    .join(",");

  const tagOptions = (topTags || [])
    .filter((t) => !RECOMMENDATION_TAGS.has(t))
    .map((t) => ({ val: t, label: t }));

  const handlePlatformChange = (value) => {
    onChange("platform", value);
    // 切换平台后，把当前 rank_type 中已经不属于新平台并集的项剔除
    if (filters.rank_type) {
      const newPlatforms = value.split(",").map((s) => s.trim()).filter(Boolean);
      const newAllowed = newPlatforms.length
        ? new Set(newPlatforms.flatMap(
            (p) => PLATFORM_RECOMMENDATION_OPTIONS[p] || RECOMMENDATION_OPTIONS.map((it) => it.val)
          ))
        : new Set(RECOMMENDATION_OPTIONS.map((it) => it.val));
      const cleaned = filters.rank_type
        .split(",").map((s) => s.trim()).filter(Boolean)
        .filter((v) => newAllowed.has(v))
        .join(",");
      if (cleaned !== filters.rank_type) {
        onChange("rank_type", cleaned);
      }
    }
  };

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
          <MultiSelectFilter
            label="平台"
            options={platformOptions}
            value={filters.platform || ""}
            onChange={handlePlatformChange}
          />
        )}

        {langOptions.length > 0 && (
          <MultiSelectFilter
            label="语种"
            options={langOptions}
            value={filters.lang || ""}
            onChange={(v) => onChange("lang", v)}
          />
        )}

        <MultiSelectFilter
          label="推荐栏位"
          options={recommendationOptions}
          value={filteredRankTypeValue}
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
          <span className="w-[5em] flex-shrink-0 text-xs font-semibold text-black">剧名</span>
          <div className="relative flex-1">
            <Search
              size={14}
              strokeWidth={1.5}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-black"
            />
            <input
              type="text"
              placeholder="输入短剧标题关键词..."
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
