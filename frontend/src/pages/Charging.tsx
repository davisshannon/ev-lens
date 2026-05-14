import { format, formatDistanceToNow } from "date-fns";
import { useState } from "react";
import { useCreatePlan, useChargePlans, useChargeSessions, useTariffs } from "../hooks/useCharges";
import { useLatestSnapshot, useVehicles } from "../hooks/useVehicles";
import { useVehicleStore } from "../stores/vehicleStore";
import type { ChargePlan, ChargeSession } from "../types/charge";

export function ChargingPage() {
  const { data: vehicles } = useVehicles();
  const { activeVehicleId } = useVehicleStore();
  const vehicleId = activeVehicleId ?? vehicles?.[0]?.id;

  const { data: snapshot } = useLatestSnapshot(vehicleId);
  const { data: sessions } = useChargeSessions(vehicleId);
  const { data: plans } = useChargePlans(vehicleId);
  const { data: tariffs } = useTariffs();
  const createPlan = useCreatePlan(vehicleId ?? "");

  const [targetSoc, setTargetSoc] = useState(80);
  const [selectedTariffId, setSelectedTariffId] = useState<string>("");
  const [departureTime, setDepartureTime] = useState("");
  const [planError, setPlanError] = useState<string | null>(null);

  const currentSoc = snapshot?.usable_battery_level ?? snapshot?.battery_level ?? 50;
  const latestPlan = plans?.[0];

  async function handleCreatePlan() {
    if (!vehicleId) return;
    setPlanError(null);
    try {
      await createPlan.mutateAsync({
        vehicle_id: vehicleId,
        current_soc: currentSoc,
        target_soc: targetSoc,
        tariff_id: selectedTariffId || undefined,
        departure_time: departureTime || undefined,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create plan";
      setPlanError(msg);
    }
  }

  if (!vehicleId) {
    return (
      <div className="text-center py-16 text-gray-500">
        No vehicle connected. Go to Settings to connect your Tesla.
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-lg mx-auto sm:max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-100">Charging</h1>

      {/* Charge plan generator */}
      <section className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
        <h2 className="text-base font-medium text-gray-200">Plan a charge</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Current SoC</label>
            <div className="text-2xl font-bold text-gray-100">{Math.round(currentSoc)}%</div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Target SoC</label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={Math.ceil(currentSoc) + 1}
                max={100}
                value={targetSoc}
                onChange={(e) => setTargetSoc(Number(e.target.value))}
                className="flex-1 accent-brand-500"
              />
              <span className="text-lg font-semibold text-gray-100 w-12 text-right">{targetSoc}%</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {tariffs && tariffs.length > 0 && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">Tariff</label>
              <select
                value={selectedTariffId}
                onChange={(e) => setSelectedTariffId(e.target.value)}
                className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2"
              >
                <option value="">Default tariff</option>
                {tariffs.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs text-gray-500 mb-1">Departure (optional)</label>
            <input
              type="datetime-local"
              value={departureTime}
              onChange={(e) => setDepartureTime(e.target.value)}
              className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2"
            />
          </div>
        </div>

        {planError && (
          <p className="text-sm text-red-400 bg-red-950 rounded-lg px-3 py-2">{planError}</p>
        )}

        <button
          onClick={handleCreatePlan}
          disabled={createPlan.isPending || targetSoc <= currentSoc}
          className="w-full rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-500/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createPlan.isPending ? "Calculating…" : "Generate charge plan"}
        </button>
      </section>

      {/* Latest plan result */}
      {latestPlan && <PlanCard plan={latestPlan} />}

      {/* Session history */}
      {sessions && sessions.length > 0 && (
        <section className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-3">
          <h2 className="text-base font-medium text-gray-200">Recent sessions</h2>
          <div className="space-y-2">
            {sessions.slice(0, 10).map((s) => (
              <SessionRow key={s.id} session={s} />
            ))}
          </div>
        </section>
      )}

      {sessions?.length === 0 && (
        <div className="text-center py-8 text-gray-600 text-sm">
          No charge sessions yet. Sessions are detected automatically from vehicle snapshots.
        </div>
      )}
    </div>
  );
}

function PlanCard({ plan }: { plan: ChargePlan }) {
  const confidence_color =
    plan.confidence === "high" ? "text-green-400" :
    plan.confidence === "moderate" ? "text-yellow-400" : "text-gray-400";

  return (
    <section className="rounded-xl bg-gray-900 border border-brand-500/30 p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-medium text-gray-200">Charge plan</h2>
        <span className={`text-xs font-medium ${confidence_color}`}>
          {plan.confidence} confidence
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {plan.recommended_start && (
          <StatBox
            label="Start charging"
            value={format(new Date(plan.recommended_start), "HH:mm")}
            sub={formatDistanceToNow(new Date(plan.recommended_start), { addSuffix: true })}
          />
        )}
        {plan.recommended_stop && (
          <StatBox
            label="Finish by"
            value={format(new Date(plan.recommended_stop), "HH:mm")}
          />
        )}
        {plan.expected_kwh != null && (
          <StatBox label="Energy needed" value={`${plan.expected_kwh.toFixed(1)} kWh`} />
        )}
        {plan.expected_cost != null && (
          <StatBox
            label="Estimated cost"
            value={`${plan.expected_cost_currency ?? "$"}${plan.expected_cost.toFixed(2)}`}
          />
        )}
      </div>

      {plan.explanation && plan.explanation.length > 0 && (
        <ul className="space-y-1">
          {plan.explanation.map((line, i) => (
            <li key={i} className="text-xs text-gray-400 flex gap-2">
              <span className="text-gray-600 shrink-0">›</span>
              {line}
            </li>
          ))}
        </ul>
      )}

      <p className="text-xs text-gray-600">
        Generated {formatDistanceToNow(new Date(plan.created_at))} ago
      </p>
    </section>
  );
}

function SessionRow({ session }: { session: ChargeSession }) {
  const kwh = session.wall_kwh_actual ?? session.wall_kwh_estimated ?? session.battery_kwh_added;
  const socDelta = session.start_soc != null && session.end_soc != null
    ? Math.round(session.end_soc - session.start_soc)
    : null;
  const duration = session.started_at && session.ended_at
    ? Math.round((new Date(session.ended_at).getTime() - new Date(session.started_at).getTime()) / 60000)
    : null;

  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
      <div>
        <p className="text-sm text-gray-200">
          {format(new Date(session.started_at), "MMM d, HH:mm")}
          {session.ended_at && ` → ${format(new Date(session.ended_at), "HH:mm")}`}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">
          {socDelta != null && `+${socDelta}% SoC`}
          {duration != null && ` · ${duration}m`}
          {session.avg_power_kw != null && ` · ${session.avg_power_kw} kW avg`}
        </p>
      </div>
      <div className="text-right">
        {kwh != null && (
          <p className="text-sm font-medium text-gray-200">{kwh.toFixed(1)} kWh</p>
        )}
        {session.cost_estimated != null && (
          <p className="text-xs text-gray-500">
            {session.cost_currency ?? "$"}{session.cost_estimated.toFixed(2)}
          </p>
        )}
        {session.energy_source && session.energy_source !== "grid" && (
          <p className="text-xs text-green-500 capitalize">{session.energy_source}</p>
        )}
      </div>
    </div>
  );
}

function StatBox({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg bg-gray-800 px-3 py-2.5">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-base font-semibold text-gray-100 mt-0.5">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}
