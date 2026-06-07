/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // --- Design system: warm-black base + single orange accent ---------
        // "ink" = backgrounds & surfaces (warm near-black). 950 is the page,
        // higher numbers step up the elevation toward borders/dividers.
        ink: {
          DEFAULT: "#0B0B0C",
          950: "#0B0B0C", // page background
          900: "#101012", // raised page section
          800: "#161618", // card
          700: "#1F1F23", // input / elevated surface
          600: "#2A2A30", // border
          500: "#3A3A42", // strong border / divider
        },
        // "flame" = the one accent. 500 is the brand orange (#F97316).
        flame: {
          50: "#FFF4ED",
          100: "#FFE6D5",
          200: "#FECDAA",
          300: "#FDAC74",
          400: "#FB8B3C",
          500: "#F97316",
          600: "#EA580C",
          700: "#C2410C",
          800: "#9A3412",
          900: "#7C2D12",
        },
        // Recommendation palette, reused by RecoBadge + score gauge.
        reco: {
          good: "#16a34a",
          lighten: "#ca8a04",
          rest: "#ea580c",
          physio: "#dc2626",
        },
      },
      boxShadow: {
        // Soft accent glow for primary CTAs / active states.
        glow: "0 0 0 1px rgba(249,115,22,0.25), 0 8px 24px -12px rgba(249,115,22,0.45)",
      },
    },
  },
  plugins: [],
};
