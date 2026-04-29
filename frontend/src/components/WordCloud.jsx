/**
 * WordCloud — 关键词云图组件（核心冲突点扫描）
 *
 * Props:
 *   keywords - {[word: string]: number} | null
 */

const MIN_FONT = 13;
const MAX_FONT = 36;

function getColor(ratio) {
  return ratio > 0.75 ? "#000000" : "#111111";
}

export default function WordCloud({ keywords }) {
  if (!keywords || Object.keys(keywords).length === 0) {
    return (
      <p className="py-5 text-center text-sm italic text-black">
        正文内容受限，暂无云图
      </p>
    );
  }

  const entries = Object.entries(keywords).sort(([, a], [, b]) => b - a);
  const maxCount = entries[0][1];
  const minCount = entries[entries.length - 1][1];
  const range = maxCount - minCount || 1;

  return (
    <div className="flex flex-wrap gap-x-3 gap-y-2 justify-center items-baseline py-2">
      {entries.map(([word, count]) => {
        const ratio = (count - minCount) / range;
        const fontSize = MIN_FONT + Math.round(ratio * (MAX_FONT - MIN_FONT));
        return (
          <span
            key={word}
            style={{ fontSize: `${fontSize}px`, color: getColor(ratio) }}
            className="font-semibold leading-tight cursor-default select-none
                       transition-opacity duration-150 hover:opacity-60"
            title={`${word}: 出现 ${count} 次`}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
}
