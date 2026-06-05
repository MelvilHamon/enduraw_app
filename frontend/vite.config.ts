/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// Dev: proxy /api to the FastAPI backend so the browser stays same-origin (no
// CORS). Prod: FastAPI serves the built assets, so relative /api calls just work.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      // Offline app shell / runtime caching is step 12; here we only precache the
      // build output so the app is installable.
      manifest: {
        name: "Enduraw Form Tracker",
        short_name: "Enduraw",
        description: "Readiness check-ins, niggles and mini-tests for endurance athletes.",
        theme_color: "#0f172a",
        background_color: "#0f172a",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
          { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
