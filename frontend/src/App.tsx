import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import { Layout } from "./components/Layout";
import { AlertsPage } from "./pages/Alerts";
import { AssistantPage } from "./pages/Assistant";
import { BatteryPage } from "./pages/Battery";
import { ChargingPage } from "./pages/Charging";
import { CostsPage } from "./pages/Costs";
import { DrivesPage } from "./pages/Drives";
import { ImportsPage } from "./pages/Imports";
import { LoginPage } from "./pages/Login";
import { SetupPage } from "./pages/Setup";
import { SettingsPage } from "./pages/Settings";
import { TodayPage } from "./pages/Today";

interface SetupStatus {
  needs_setup: boolean;
  bridge_secret: string | null;
}

type AppState = "loading" | "setup" | "login" | "ready";

export function App() {
  const [appState, setAppState] = useState<AppState>("loading");
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);

  useEffect(() => {
    async function checkStatus() {
      try {
        const { data } = await api.get<SetupStatus>("/auth/setup-status");
        if (data.needs_setup) {
          setSetupStatus(data);
          setAppState("setup");
          return;
        }
      } catch {
        // If we can't reach the backend, show login (will show its own error)
      }
      const token = localStorage.getItem("ev_lens_token");
      setAppState(token ? "ready" : "login");
    }
    checkStatus();
  }, []);

  if (appState === "loading") {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-500 text-sm">Loading…</div>
      </div>
    );
  }

  if (appState === "setup" && setupStatus) {
    return <SetupPage status={setupStatus} />;
  }

  if (appState === "login") {
    return <LoginPage onLogin={() => setAppState("ready")} />;
  }

  return (
    <Routes>
      <Route element={<Layout onLogout={() => {
        localStorage.removeItem("ev_lens_token");
        setAppState("login");
      }} />}>
        <Route index element={<Navigate to="/today" replace />} />
        <Route path="today" element={<TodayPage />} />
        <Route path="charging" element={<ChargingPage />} />
        <Route path="battery" element={<BatteryPage />} />
        <Route path="drives" element={<DrivesPage />} />
        <Route path="costs" element={<CostsPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="assistant" element={<AssistantPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="imports" element={<ImportsPage />} />
      </Route>
    </Routes>
  );
}
