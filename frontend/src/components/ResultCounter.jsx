export default function ResultCounter({ total, loading, error }) {
  if (error) {
    return (
      <div className="rounded border border-red-200 bg-red-50 px-3 py-1.5 text-xs text-red-500">
        查询失败：{error}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="h-7 w-36 animate-pulse rounded bg-slate-100" />
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-black">匹配结果</span>
      <span className="text-base font-bold tabular-nums text-brand">
        {total.toLocaleString("zh-CN")}
      </span>
      <span className="text-black">条</span>
    </div>
  );
}
