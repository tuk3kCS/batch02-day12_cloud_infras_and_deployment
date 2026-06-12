import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#08111f",
          900: "#0d1828",
          800: "#132236",
          700: "#20324a"
        },
        cyan: {
          450: "#22d3ee"
        }
      },
      boxShadow: {
        panel: "0 18px 48px rgba(0, 0, 0, 0.26)"
      }
    }
  },
  plugins: []
} satisfies Config;
