import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/Spinner";
import { LoginPage } from "./pages/LoginPage";
// Five-tab product shell (Phase 1).
import { HomePage } from "./pages/HomePage";
import { LoadPage } from "./pages/LoadPage";
import { RoutinePage } from "./pages/RoutinePage";
import { HealthPage } from "./pages/HealthPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SettingsPage } from "./pages/SettingsPage";
// Legacy screens — kept reachable by URL during the migration (not in the nav).
// Their logic is ported into the new tabs across the remaining phases.
import { TodayPage } from "./pages/TodayPage";
import { BodyMapPage } from "./pages/BodyMapPage";
import { InsightsPage } from "./pages/InsightsPage";

export function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <Spinner label="Chargement…" />
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        {/* Five product tabs */}
        <Route path="/home" element={<HomePage />} />
        <Route path="/load" element={<LoadPage />} />
        <Route path="/routine" element={<RoutinePage />} />
        <Route path="/health" element={<HealthPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />

        {/* Legacy (transitional, not in nav) */}
        <Route path="/today" element={<TodayPage />} />
        <Route path="/body" element={<BodyMapPage />} />
        <Route path="/insights" element={<InsightsPage />} />

        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </Layout>
  );
}
