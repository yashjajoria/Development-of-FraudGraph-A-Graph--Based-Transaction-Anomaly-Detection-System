/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "ui-monospace", "monospace"] },
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)", card: "rgb(var(--card) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)", fg: "rgb(var(--fg) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        accent: { DEFAULT: "#6366F1", 2: "#8B5CF6" },
      },
      boxShadow: { glow: "0 0 24px rgba(99,102,241,.45)" },
    },
  },
  plugins: [],
};
