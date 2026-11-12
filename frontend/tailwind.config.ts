import type { Config } from "tailwindcss";
export default {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        marca: { 50: "#effaf8", 100: "#d6f1ec", 200: "#ade3da", 400: "#3fb3a3", 500: "#1d9686", 600: "#14786d", 700: "#0f5e5c", 800: "#0d4a49", 900: "#0b3a3a" },
        ambar: { 300: "#f8cf7f", 400: "#f2a541", 500: "#e08a1e" },
      },
      fontFamily: { sans: ["Segoe UI", "system-ui", "-apple-system", "Roboto", "sans-serif"] },
    },
  },
  plugins: [],
} satisfies Config;
