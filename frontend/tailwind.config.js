/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Recommendation palette, reused by RecoBadge + score gauge.
        reco: {
          good: "#16a34a",
          lighten: "#ca8a04",
          rest: "#ea580c",
          physio: "#dc2626",
        },
      },
    },
  },
  plugins: [],
};
