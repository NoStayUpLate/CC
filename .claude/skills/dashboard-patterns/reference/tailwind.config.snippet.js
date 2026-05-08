// dashboard-patterns SKILL — Tailwind 颜色 token 片段
//
// 用途：把下面的 colors 合并到目标项目的 tailwind.config.js
//       → theme.extend.colors 下。这一份是看板（筛选器 / 标签 /
//       状态按钮 / 折叠区 / Modal）渲染时引用的全部色号。
//
// 不复制色号 ≠ 跑不起来，但视觉口径会偏（按钮变蓝、选中态变灰等）。

export const dashboardColors = {
  // ── 品牌主色（绿）──────────────────────────────────────
  // 选中、active tab、强调数字、可点击文本、主按钮
  brand: {
    DEFAULT: "#00BF8A", // 主绿
    dark:    "#00A877", // hover 加深（按钮 / 链接）
    light:   "#E6F9F3", // 浅绿背景（选中项底 / 标签底 / hover 浮层）
  },

  // ── 页面背景（浅灰）───────────────────────────────────
  // 主体外层背景，避免纯白卡片之间没有层次感
  page: "#e5e7eb",

  // ── 中性色补充 ────────────────────────────────────────
  // zw.border 用于 .zw-card / .zw-chip 等组件的统一描边
  zw: {
    text: "#000000",
    secondary: "#000000",
    border: "rgb(242, 243, 245)",
  },

  // ── 评分高低指示色（可选，看板里给 GHI/DHI 分级用）──
  // 未做评分系统的项目可以删掉
  ghi: {
    high: "#00BF8A",
    mid:  "#d97706", // amber-600
    low:  "#94a3b8", // slate-400
  },
};

// ── 字号微调（建议）─────────────────────────────────────────
// Tailwind 默认 text-xs (12px) / text-sm (14px) 在密集型看板里偏小，
// 长时间阅读会累。整体上调到 +4px 让阅读更舒适，且不会触发布局错位。
// ⚠️ 副作用：text-sm (18px) 与 text-lg 默认值持平；
//     若需要明显的尺寸层级请直接用 text-base / text-lg / text-xl。
export const dashboardFontSize = {
  xs: ["1rem",     "1.5rem"],   // 16px / 24px（原 12 / 16）
  sm: ["1.125rem", "1.625rem"], // 18px / 26px（原 14 / 20）
};

// 合并到目标项目 tailwind.config.js 的示例：
//
//   import {
//     dashboardColors,
//     dashboardFontSize,
//   } from "./.claude/skills/dashboard-patterns/reference/tailwind.config.snippet.js";
//
//   /** @type {import('tailwindcss').Config} */
//   export default {
//     content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
//     theme: {
//       extend: {
//         colors: dashboardColors,
//         fontSize: dashboardFontSize,
//         // 已有的 colors 与 dashboardColors 合并即可：
//         // colors: { ...dashboardColors, /* 你已有的 */ },
//       },
//     },
//     plugins: [],
//   };
//
// 注意：Tailwind 必须在 content 列表里包含到引用 className 的所有文件，
// 否则按需生成的 CSS 会缺失 class（出现「明明加了 className，UI 没生效」的怪事）。
