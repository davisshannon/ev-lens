import { formatDistanceToNow, format } from "date-fns";
import { useEffect } from "react";
import { Link } from "react-router-dom";
import { ProviderHealthBanner } from "../components/ProviderHealthBanner";
import { SocGauge } from "../components/SocGauge";
import { SocSparkline } from "../components/SocSparkline";
import { StatusPill } from "../components/StatusPill";
import { useLatestSnapshot, useProviderHealth, useSnapshots, useVehicles } from "../hooks/useVehicles";
import { useVehicleStore } from "../stores/vehicleStore";

export function TodayPage() {
  const { data: vehicles, isLoading: vehiclesLoading } = useVehicles();
  const { activeVehicleId, setActiveVehicleId } = useVehicleStore();

  // Auto-select first vehicle
  useEffect(() => {
    if (!activeVehicleId && vehicles?.length) {
      setActiveVehicleId(vehicles[0].id);
    }
  }, [vehicles, activeVehicleId, setActiveVehicleId]);

  const vehicleId = activeVehicleId ?? undefined;
  const { data: snapshot, isLoading: snapshotLoading } = useLatestSnapshot(vehicleId);
  const { data: snapshots } = useSnapshots(vehicleId, 288);
  const { data: health } = useProviderHealth(vehicleId);

  if (vehiclesLoading) {
    return <div className="flex items-center justify-center h-48 text-gray-500">Loading…</div>;
  }

  if (!vehicles?.length) {
    return <NoVehiclesPrompt />;
  }

  const vehicle = vehicles.find((v) => v.id === activeVehicleId) ?? vehicles[0];

  return (
    <div className="space-y-4 max-w-lg mx-auto sm:max-w-2xl">
      {/* Vehicle selector (multi-vehicle ready) */}
      {vehicles.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {vehicles.map((v) => (
            <button
              key={v.id}
              onClick={() => setActiveVehicleId(v.id)}
              className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                v.id === activeVehicleId
                  ? "bg-brand-500 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
            >
              {v.display_name ?? v.model ?? "Vehicle"}
            </button>
          ))}
        </div>
      )}

      {/* Provider health warning */}
      {health && !health.healthy && <ProviderHealthBanner health={health} />}

      {/* Main card */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-100">
              {vehicle.display_name ?? vehicle.model ?? "My Vehicle"}
            </h2>
            <p className="text-sm text-gray-500">
              {vehicle.model}{vehicle.year ? ` · ${vehicle.year}` : ""}
            </p>
          </div>
          {snapshot && (
            <StatusPill state={snapshot.vehicle_state} chargingState={snapshot.charging_state} />
          )}
        </div>

        {snapshotLoading && (
          <div className="h-32 flex items-center justify-center text-gray-600 text-sm">
            Fetching vehicle state…
          </div>
        )}

        {snapshot && (
          <>
            <div className="flex items-center gap-6">
              <SocGauge
                soc={snapshot.usable_battery_level ?? snapshot.battery_level ?? 0}
                limitSoc={snapshot.charge_limit_soc ?? undefined}
                size="lg"
              />
              <div className="space-y-3 flex-1">
                <StatRow
                  label="Range"
                  value={
                    snapshot.est_battery_range_km != null
                      ? `${Math.round(snapshot.est_battery_range_km)} km`
                      : snapshot.battery_range_km != null
                      ? `${Math.round(snapshot.battery_range_km)} km`
                      : "—"
                  }
                />
                <StatRow
                  label="Charge limit"
                  value={snapshot.charge_limit_soc != null ? `${snapshot.charge_limit_soc}%` : "—"}
                />
                {snapshot.charging_state === "Charging" && (
                  <StatRow
                    label="Charging"
                    value={snapshot.charger_power_kw != null ? `${snapshot.charger_power_kw} kW` : "Active"}
                    highlight
                  />
                )}
                <StatRow
                  label="Odometer"
                  value={
                    snapshot.odometer_km != null
                      ? `${Math.round(snapshot.odometer_km).toLocaleString()} km`
                      : "—"
                  }
                />
              </div>
            </div>

            {/* Temperature row */}
            {(snapshot.inside_temp_c != null || snapshot.outside_temp_c != null) && (
              <div className="mt-4 flex gap-4 text-sm text-gray-400">
                {snapshot.outside_temp_c != null && (
                  <span>Outside: <span className="text-gray-200">{snapshot.outside_temp_c}°C</span></span>
                )}
                {snapshot.inside_temp_c != null && (
                  <span>Inside: <span className="text-gray-200">{snapshot.inside_temp_c}°C</span></span>
                )}
                {snapshot.climate_on && (
                  <span className="text-blue-400">Climate on</span>
                )}
              </div>
            )}

            {/* Status indicators */}
            <div className="mt-3 flex gap-3 text-xs text-gray-500">
              {snapshot.sentry_mode && <span className="text-yellow-500">Sentry</span>}
              {snapshot.locked === false && <span className="text-orange-400">Unlocked</span>}
              {snapshot.plugged_in && snapshot.charging_state !== "Charging" && (
                <span className="text-gray-400">Plugged in · {snapshot.charging_state}</span>
              )}
            </div>

            <p className="mt-3 text-xs text-gray-600">
              Updated {formatDistanceToNow(new Date(snapshot.observed_at))} ago ·{" "}
              {format(new Date(snapshot.observed_at), "HH:mm")}
            </p>
          </>
        )}
      </div>

      {/* 24h SoC sparkline */}
      {snapshots && snapshots.length > 1 && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4">
          <p className="text-xs text-gray-500 mb-2">SoC — last 24 hours</p>
          <SocSparkline snapshots={snapshots} />
        </div>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          to="/charging"
          className="rounded-xl bg-gray-900 border border-gray-800 p-4 hover:border-gray-700 transition-colors"
        >
          <p className="text-sm font-medium text-gray-200">Plan a charge</p>
          <p className="text-xs text-gray-500 mt-1">Optimise for your tariff</p>
        </Link>
        <Link
          to="/alerts"
          className="rounded-xl bg-gray-900 border border-gray-800 p-4 hover:border-gray-700 transition-colors"
        >
          <p className="text-sm font-medium text-gray-200">Alerts</p>
          <p className="text-xs text-gray-500 mt-1">Anomalies &amp; warnings</p>
        </Link>
      </div>
    </div>
  );
}

function StatRow({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-sm text-gray-500">{label}</span>
      <span className={`text-sm font-medium ${highlight ? "text-blue-400" : "text-gray-200"}`}>
        {value}
      </span>
    </div>
  );
}

function NoVehiclesPrompt() {
  return (
    <div className="flex flex-col items-center justify-center h-64 space-y-4 text-center px-6">
      <div className="text-4xl">🔌</div>
      <h2 className="text-lg font-semibold text-gray-200">No vehicles connected</h2>
      <p className="text-sm text-gray-500">Connect your Tesla to get started.</p>
      <Link
        to="/settings"
        className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500/90"
      >
        Connect Tesla
      </Link>
    </div>
  );
}
