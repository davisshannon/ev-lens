import { format } from "date-fns";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useBatteryEstimates, useLatestBatteryEstimate } from "../hooks/useBattery";
import { useVehicles } from "../hooks/useVehicles";
import { useVehicleStore } from "../stores/vehicleStore";
import type { BatteryEstimate } from "../types/battery";

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "text-green-400",
  moderate: "text-yellow-400",
  low: "text-orange-400",
  unknown: "text-gray-500",
};

export function BatteryPage() {
  const { data: vehicles } = useVehicles();
  const { activeVehicleId } = useVehicleStore();
  const vehicleId = activeVehicleId ?? vehicles?.[0]?.id;

  const { data: latest, isLoading: latestLoading } = useLatestBatteryEstimate(vehicleId);
  const { data: history } = useBatteryEstimates(vehicleId, 90);

  if (!vehicleId) {
    return (
      <div className="text-center py-16 text-gray-500">
        No vehicle connected. Go to Settings to connect your Tesla.
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-100">Battery Health</h1>

      {latestLoading ? (
        <div className="h-32 flex items-center justify-center text-gray-500">Loading…</div>
      ) : latest ? (
        <HealthCard estimate={latest} />
      ) : (
        <EmptyState />
      )}

      {history && history.length > 1 && <DegradationChart estimates={history} />}
    </div>
  );
}

function HealthCard({ estimate }: { estimate: BatteryEstimate }) {
  const degradation = estimate.degradation_pct;
  const usable = estimate.estimated_usable_kwh;
  const nominal = estimate.nominal_kwh;
  const confidenceClass = CONFIDENCE_COLORS[estimate.confidence] ?? "text-gray-400";

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
      <div className="flex items-start justify-between">
        <h2 className="text-base font-medium text-gray-200">Current Estimate</h2>
        <span className={`text-xs font-medium uppercase tracking-wide ${confidenceClass}`}>
          {estimate.confidence} confidence
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <Stat label="Usable Capacity" value={`${usable.toFixed(1)} kWh`} />
        {nominal && <Stat label="Nominal" value={`${nominal.toFixed(1)} kWh`} />}
        {degradation != null ? (
          <Stat
            label="Degradation"
            value={`${degradation.toFixed(1)}%`}
            valueClass={degradation > 15 ? "text-orange-400" : degradation > 25 ? "text-red-400" : "text-gray-200"}
          />
        ) : (
          <Stat label="Degradation" value="—" />
        )}
        <Stat label="Sessions Used" value={String(estimate.sessions_used)} />
        <Stat
          label="Calculated"
          value={format(new Date(estimate.calculated_at), "MMM d, yyyy")}
        />
      </div>

      {estimate.explanation && estimate.explanation.length > 0 && (
        <div className="border-t border-gray-800 pt-3 space-y-1">
          {estimate.explanation.map((line, i) => (
            <p key={i} className="text-sm text-gray-400">
              {line}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function DegradationChart({ estimates }: { estimates: BatteryEstimate[] }) {
  const data = [...estimates]
    .reverse()
    .map((e) => ({
      date: format(new Date(e.calculated_at), "MMM d"),
      kwh: Number(e.estimated_usable_kwh.toFixed(2)),
      degradation: e.degradation_pct != null ? Number(e.degradation_pct.toFixed(1)) : null,
    }));

  const nominal = estimates[0]?.nominal_kwh;

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-3">
      <h2 className="text-base font-medium text-gray-200">Capacity History</h2>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 11 }} />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            unit=" kWh"
            width={60}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            labelStyle={{ color: "#d1d5db" }}
            itemStyle={{ color: "#60a5fa" }}
            formatter={(v: number) => [`${v} kWh`, "Usable"]}
          />
          {nominal && (
            <ReferenceLine
              y={nominal}
              stroke="#6b7280"
              strokeDasharray="4 4"
              label={{ value: "Nominal", fill: "#6b7280", fontSize: 11, position: "insideTopRight" }}
            />
          )}
          <Line
            type="monotone"
            dataKey="kwh"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Stat({
  label,
  value,
  valueClass = "text-gray-200",
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-lg font-semibold mt-0.5 ${valueClass}`}>{value}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-8 text-center space-y-2">
      <p className="text-gray-300 font-medium">No battery estimate yet</p>
      <p className="text-sm text-gray-500">
        Battery health is calculated automatically after several charge sessions. Check back once
        you have a few completed charges.
      </p>
    </div>
  );
}
