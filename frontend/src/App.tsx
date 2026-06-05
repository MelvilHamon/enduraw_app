import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/Spinner";
import { LoginPage } from "./pages/LoginPage";
import { CheckinPage } from "./pages/CheckinPage";
import { TodayPage } from "./pages/TodayPage";
import { BodyMapPage } from "./pages/BodyMapPage";
import { MiniTestPage } from "./pages/MiniTestPage";
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
        <Route path="/today" element={<TodayPage />} />
        <Route path="/checkin" element={<CheckinPage />} />
        <Route path="/body" element={<BodyMapPage />} />
        <Route path="/tests" element={<MiniTestPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="*" element={<Navigate to="/today" replace />} />
      </Routes>
    </Layout>
  );
}
