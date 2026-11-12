import type { Config } from "tailwindcss";
// Paleta da identidade visual SIME: fundo #F4F6F9, azul #5270DA, menu branco, cartões de 12 px.
export default {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        marca: { 50: "#f3f5fd", 100: "#eaeefb", 200: "#d3dbf6", 300: "#aebcee", 400: "#8197e4", 500: "#6680de", 600: "#5270da", 700: "#4664c8", 800: "#3a52a8", 900: "#2c3d7d" },
        ambar: { 300: "#f5d27a", 400: "#e0a526", 500: "#ca8a04" },
        sime: { fundo: "#f4f6f9", tinta: "#0f172a", suave: "#64748b", borda: "rgba(15,23,42,.08)" },
      },
      fontFamily: { sans: ["Inter", "Segoe UI", "system-ui", "-apple-system", "Roboto", "sans-serif"] },
      boxShadow: { sime: "0 1px 3px rgba(15,23,42,.035)" },
    },
  },
  plugins: [],
} satisfies Config;
