/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#00BF8A",
          dark:    "#00A877",
          light:   "#E6F9F3",
        },
        page: "#e5e7eb",
        zw: {
          text: "#000000",
          secondary: "#000000",
          border: "rgb(242, 243, 245)",
        },
        ghi: {
          high: "#00BF8A",
          mid:  "#d97706", // amber-600
          low:  "#94a3b8", // slate-400
        },
      },
      // 调高常用字号到 +4px 一档，让长时间阅读不累。
      // 只覆盖 xs / sm（最常用），其余保持 Tailwind 默认。
      // ⚠️ 副作用：text-sm (18px) 与 text-lg 默认值持平；
      //     若需要明显的尺寸层级请直接用 text-base / text-lg / text-xl。
      fontSize: {
        xs: ["1rem",     "1.5rem"],     // 16px / 24px（原 12 / 16）
        sm: ["1.125rem", "1.625rem"],   // 18px / 26px（原 14 / 20）
      },
    },
  },
  plugins: [],
};
