import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useCosts } from "../hooks/useBattery";
import { useVehicles } from "../hooks/useVehicles";
import { useVehicleStore } from "../stores/vehicleStore";
import type { CostSummary } from "../types/battery";

const MONTH_OPTIONS = [
  { label: "3 mo", months: 3 },
  { label: "6 mo", months: 6 },
  { label: "12 mo", months: 12 },
];

export function CostsPage() {
  const { data: vehicles } = useVehicles();
  const { activeVehicleId } = useVehicleStore();
  const vehicleId = activeVehicleId ?? vehicles?.[0]?.id;
  const [months, setMonths] = useState(6);

  const { data: costs, isLoading } = useCosts(vehicleId, months);

  if (!vehicleId) {
    return (
      <div className="text-center py-16 text-gray-500">
        No vehicle connected. Go to Settings to connect your Tesla.
      </div>
    );
  }

  const totalCost = costs?.reduce((s, c) => s + c.total_cost, 0) ?? 0;
  const totalKwh = costs?.reduce((s, c) => s + c.total_kwh, 0) ?? 0;
  const totalSessions = costs?.reduce((s, c) => s + c.session_count, 0) ?? 0;
  const avgSolarPct =
    costs && costs.length > 0
      ? costs.reduce((s, c) => s + c.solar_pct, 0) / costs.length
      : 0;
  const currency = costs?.[0]?.currency ?? "USD";
  const currencySymbol = currency === "USD" ? "$" : currency === "EUR" ? "€" : currency === "GBP" ? "£" : currency;

  return (
    <div className="space-y-5 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-100">Charging Costs</h1>
        <div className="flex gap-1">
          {MONTH_OPTIONS.map((o) => (
            <button
              key={o.months}
              onClick={() => setMonths(o.months)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                months === o.months
                  ? "bg-brand-500 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="h-32 flex items-center justify-center text-gray-500">Loading…</div>
      ) : costs && costs.length > 0 ? (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <SummaryCard label="Total Cost" value={`${currencySymbol}${totalCost.toFixed(2)}`} />
            <SummaryCard label="Total Energy" value={`${totalKwh.toFixed(1)} kWh`} />
            <SummaryCard label="Sessions" value={String(totalSessions)} />
            <SummaryCard label="Solar Mix" value={`${avgSolarPct.toFixed(0)}%`} />
          </div>

          {/* Bar chart */}
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-3">
            <h2 className="text-base font-medium text-gray-200">Monthly Spend</h2>
            <CostBarChart costs={costs} currencySymbol={currencySymbol} />
          </div>

          {/* Monthly table */}
          <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-4 py-3 text-gray-500 font-medium">Month</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">Cost</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium hidden sm:table-cell">
                    Energy
                  </th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium hidden sm:table-cell">
                    ¢/kWh
                  </th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">Solar</th>
                  <th className="text-right px-4 py-3 text-gray-500 font-medium">Sessions</th>
                </tr>
              </thead>
              <tbody>
                {[...costs].reverse().map((c) => (
                  <CostRow key={c.period} cost={c} currencySymbol={currencySymbol} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-8 text-center">
          <p className="text-gray-400">No cost data yet.</p>
          <p className="text-sm text-gray-500 mt-1">
            Costs are calculated once charge sessions complete and a tariff is configured.
          </p>
        </div>
      )}
    </div>
  );
}

function CostBarChart({
  costs,
  currencySymbol,
}: {
  costs: CostSummary[];
  currencySymbol: string;
}) {
  const data = costs.map((c) => ({
    month: c.period.slice(5), // "05" from "2026-05"
    cost: Number(c.total_cost.toFixed(2)),
    solar: Number(c.solar_pct.toFixed(0)),
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} barCategoryGap="30%">
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
        <XAxis dataKey="month" tick={{ fill: "#9ca3af", fontSize: 11 }} />
        <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} width={50} />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
          labelStyle={{ color: "#d1d5db" }}
          formatter={(v: number) => [`${currencySymbol}${v.toFixed(2)}`, "Cost"]}
        />
        <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.solar > 50 ? "#34d399" : entry.solar > 20 ? "#60a5fa" : "#818cf8"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function CostRow({ cost, currencySymbol }: { cost: CostSummary; currencySymbol: string }) {
  const centsPerKwh =
    cost.avg_cost_per_kwh != null ? (cost.avg_cost_per_kwh * 100).toFixed(1) : "—";

  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
      <td className="px-4 py-3 text-gray-300">{cost.period}</td>
      <td className="px-4 py-3 text-right text-gray-200 font-medium">
        {currencySymbol}{cost.total_cost.toFixed(2)}
      </td>
      <td className="px-4 py-3 text-right text-gray-400 hidden sm:table-cell">
        {cost.total_kwh.toFixed(1)} kWh
      </td>
      <td className="px-4 py-3 text-right text-gray-400 hidden sm:table-cell">{centsPerKwh}</td>
      <td className="px-4 py-3 text-right">
        <span
          className={`text-xs font-medium ${
            cost.solar_pct > 50
              ? "text-green-400"
              : cost.solar_pct > 20
              ? "text-blue-400"
              : "text-gray-500"
          }`}
        >
          {cost.solar_pct.toFixed(0)}%
        </span>
      </td>
      <td className="px-4 py-3 text-right text-gray-500">{cost.session_count}</td>
    </tr>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-3 text-center">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-lg font-semibold text-gray-200 mt-1">{value}</p>
    </div>
  );
}
