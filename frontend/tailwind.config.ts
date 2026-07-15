import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#EFEFE8",
        ink: "#101114",
        blueprint: "#1E3FE0",
        marker: "#FF8C1A",
        signal: "#7A3BF5",
        void: "#E8402C"
      },
      fontFamily: {
        display: ['"Space Grotesk"', "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"]
      },
      boxShadow: {
        stamp: "4px 4px 0 var(--ink)"
      }
    }
  },
  plugins: []
} satisfies Config;
