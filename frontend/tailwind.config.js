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
    },
  },
  plugins: [],
};
