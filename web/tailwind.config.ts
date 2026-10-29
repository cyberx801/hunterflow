import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        app: "#0B0E12",
        surface: "#12161C",
        raised: "#1A2027",
        border: "#232B34",
        "border-strong": "#2E3945",
        "text-primary": "#E6EAF0",
        "text-secondary": "#9AA6B2",
        "text-muted": "#66727E",
        accent: {
          DEFAULT: "#F59E0B",
          hover: "#FBBF24",
        },
        danger: "#F87171",
        warning: "#FBBF24",
        success: "#34D399",
        info: "#60A5FA",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      borderRadius: {
        panel: "6px",
      },
    },
  },
  plugins: [],
};

export default config;
