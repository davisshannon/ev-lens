import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { TodayPage } from "./pages/Today";
import { ChargingPage } from "./pages/Charging";
import { BatteryPage } from "./pages/Battery";
import { DrivesPage } from "./pages/Drives";
import { CostsPage } from "./pages/Costs";
import { AlertsPage } from "./pages/Alerts";
import { SettingsPage } from "./pages/Settings";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/today" replace />} />
        <Route path="today" element={<TodayPage />} />
        <Route path="charging" element={<ChargingPage />} />
        <Route path="battery" element={<BatteryPage />} />
        <Route path="drives" element={<DrivesPage />} />
        <Route path="costs" element={<CostsPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
