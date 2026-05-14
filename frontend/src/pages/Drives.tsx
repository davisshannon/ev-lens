import { formatDistanceToNow, format } from "date-fns";
import { useState } from "react";
import { useDrives } from "../hooks/useBattery";
import { useVehicles } from "../hooks/useVehicles";
import { useVehicleStore } from "../stores/vehicleStore";
import type { DriveSession } from "../types/battery";

const RANGE_OPTIONS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
];

export function DrivesPage() {
  const { data: vehicles } = useVehicles();
  const { activeVehicleId } = useVehicleStore();
  const vehicleId = activeVehicleId ?? vehicles?.[0]?.id;
  const [days, setDays] = useState(30);

  const { data: drives, isLoading } = useDrives(vehicleId, days);

  if (!vehicleId) {
    return (
      <div className="text-center py-16 text-gray-500">
        No vehicle connected. Go to Settings to connect your Tesla.
      </div>
    );
  }

  const totalDistance = drives?.reduce((s, d) => s + (d.distance_km ?? 0), 0) ?? 0;
  const totalEnergy = drives?.reduce((s, d) => s + (d.energy_kwh ?? 0), 0) ?? 0;

  return (
    <div className="space-y-5 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-100">Drives</h1>
        <div className="flex gap-1">
          {RANGE_OPTIONS.map((o) => (
            <button
              key={o.days}
              onClick={() => setDays(o.days)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                days === o.days
                  ? "bg-brand-500 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary row */}
      {drives && drives.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <SummaryCard label="Drives" value={String(drives.length)} />
          <SummaryCard label="Distance" value={`${totalDistance.toFixed(0)} km`} />
          <SummaryCard label="Energy Used" value={totalEnergy > 0 ? `${totalEnergy.toFixed(1)} kWh` : "—"} />
        </div>
      )}

      {isLoading ? (
        <div className="h-32 flex items-center justify-center text-gray-500">Loading…</div>
      ) : drives && drives.length > 0 ? (
        <div className="space-y-2">
          {drives.map((drive, i) => (
            <DriveRow key={i} drive={drive} />
          ))}
        </div>
      ) : (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-8 text-center">
          <p className="text-gray-400">No drives recorded in this period.</p>
          <p className="text-sm text-gray-500 mt-1">
            Drives are derived from vehicle snapshots while moving.
          </p>
        </div>
      )}
    </div>
  );
}

function DriveRow({ drive }: { drive: DriveSession }) {
  const start = new Date(drive.started_at);
  const durationH = Math.floor(drive.duration_minutes / 60);
  const durationM = Math.round(drive.duration_minutes % 60);
  const durationStr = durationH > 0 ? `${durationH}h ${durationM}m` : `${durationM}m`;

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-200">
            {format(start, "EEE, MMM d")} · {format(start, "h:mm a")}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {formatDistanceToNow(start, { addSuffix: true })} · {durationStr}
          </p>
        </div>
        {drive.distance_km != null && (
          <span className="text-sm font-semibold text-gray-200">
            {drive.distance_km.toFixed(1)} km
          </span>
        )}
      </div>

      <div className="flex gap-4 flex-wrap">
        {drive.start_soc != null && drive.end_soc != null && (
          <Chip
            label="SoC"
            value={`${drive.start_soc.toFixed(0)}% → ${drive.end_soc.toFixed(0)}%`}
          />
        )}
        {drive.energy_kwh != null && (
          <Chip label="Energy" value={`${drive.energy_kwh.toFixed(2)} kWh`} />
        )}
        {drive.efficiency_wh_per_km != null && (
          <Chip label="Efficiency" value={`${drive.efficiency_wh_per_km.toFixed(0)} Wh/km`} />
        )}
        {drive.max_speed_kmh != null && (
          <Chip label="Max speed" value={`${drive.max_speed_kmh.toFixed(0)} km/h`} />
        )}
      </div>
    </div>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-xs">
      <span className="text-gray-500">{label}: </span>
      <span className="text-gray-300">{value}</span>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-3 text-center">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-xl font-semibold text-gray-200 mt-1">{value}</p>
    </div>
  );
}
