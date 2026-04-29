import { useEffect, useRef, useState } from "react";

function FieldShell({ label, children }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <span className="w-[5em] flex-shrink-0 text-xs font-semibold text-black">{label}</span>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export function SelectFilter({ label, options, value, onChange, allLabel = "全部" }) {
  return (
    <FieldShell label={label}>
      <select
        value={value || ""}
        onChange={(event) => onChange(event.target.value)}
        className="zw-field w-full"
      >
        <option value="">{allLabel}</option>
        {options.map(({ val, label: optionLabel }) => (
          <option key={val} value={val}>
            {optionLabel}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

export function MultiSelectFilter({ label, options, value, onChange, allLabel = "全部" }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const selected = value ? value.split(",").map((t) => t.trim()).filter(Boolean) : [];
  const selectedSet = new Set(selected);

  useEffect(() => {
    if (!open) return undefined;
    const handleClick = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    window.addEventListener("mousedown", handleClick);
    return () => window.removeEventListener("mousedown", handleClick);
  }, [open]);

  const toggleValue = (val) => {
    const next = selectedSet.has(val)
      ? selected.filter((item) => item !== val)
      : [...selected, val];
    onChange(next.join(","));
  };

  const displayText = selected.length
    ? options
        .filter((option) => selectedSet.has(option.val))
        .map((option) => option.label)
        .join("、")
    : allLabel;

  return (
    <FieldShell label={label}>
      <div ref={rootRef} className="relative">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="zw-field flex w-full items-center justify-between gap-2 text-left"
        >
          <span className="truncate text-black">
            {displayText}
          </span>
          <span className="text-xs text-black">∨</span>
        </button>

        {open && (
          <div className="absolute left-0 right-0 top-[calc(100%+4px)] z-30 max-h-64 overflow-y-auto rounded-sm border border-[#dcdfe6] bg-white p-1 shadow-[0_8px_24px_rgba(15,23,42,0.10)]">
            <button
              type="button"
              onClick={() => onChange("")}
              className={`flex w-full items-center rounded px-3 py-2 text-left text-sm transition-colors ${
                selected.length === 0
                  ? "bg-brand-light text-brand"
                  : "text-black hover:bg-slate-50 hover:text-black"
              }`}
            >
              {allLabel}
            </button>
            {options.map(({ val, label: optionLabel }) => (
              <button
                type="button"
                key={val}
                onClick={() => toggleValue(val)}
                className={`flex w-full items-center justify-between gap-2 rounded px-3 py-2 text-left text-sm transition-colors ${
                  selectedSet.has(val)
                    ? "bg-brand-light text-brand"
                    : "text-black hover:bg-slate-50 hover:text-black"
                }`}
              >
                <span className="truncate">{optionLabel}</span>
                {selectedSet.has(val) && <span className="text-xs">✓</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </FieldShell>
  );
}
