/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Segoe UI", "PingFang SC", "Microsoft YaHei", "sans-serif"],
        body: ["Segoe UI", "PingFang SC", "Microsoft YaHei", "sans-serif"],
      },
      boxShadow: {
        panel: "0 20px 60px rgba(15, 23, 42, 0.12)",
      },
      colors: {
        ink: "#112033",
        mist: "#f3f7fb",
        line: "#d7e3f1",
        brand: {
          50: "#edf7ff",
          100: "#d8ecff",
          500: "#1677ff",
          700: "#0d4fb5"
        },
        accent: "#0f766e",
        warm: "#f97316"
      }
    },
  },
  plugins: [],
};
