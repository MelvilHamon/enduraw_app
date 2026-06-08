import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";
// Self-hosted fonts (bundled → work offline in the PWA, no Google Fonts fetch).
// Inter for body/UI, Archivo (with its width axis) for athletic display titles.
import "@fontsource-variable/inter/wght.css";
import "@fontsource-variable/archivo/wdth.css";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
