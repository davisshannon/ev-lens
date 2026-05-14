import { formatDistanceToNow } from "date-fns";
import { useState } from "react";
import { useAlerts, useDismissAlert, useResolveAlert } from "../hooks/useBattery";
import { useVehicles } from "../hooks/useVehicles";
import { useVehicleStore } from "../stores/vehicleStore";
import type { Alert } from "../types/battery";

const SEVERITY_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  critical: { bg: "bg-red-950", text: "text-red-400", dot: "bg-red-400" },
  warning: { bg: "bg-yellow-950", text: "text-yellow-400", dot: "bg-yellow-400" },
  info: { bg: "bg-blue-950", text: "text-blue-400", dot: "bg-blue-400" },
};

export function AlertsPage() {
  const { data: vehicles } = useVehicles();
  const { activeVehicleId } = useVehicleStore();
  const vehicleId = activeVehicleId ?? vehicles?.[0]?.id;
  const [showResolved, setShowResolved] = useState(false);

  const { data: alerts, isLoading } = useAlerts(vehicleId, showResolved);
  const dismiss = useDismissAlert(vehicleId ?? "");
  const resolve = useResolveAlert(vehicleId ?? "");

  if (!vehicleId) {
    return (
      <div className="text-center py-16 text-gray-500">
        No vehicle connected. Go to Settings to connect your Tesla.
      </div>
    );
  }

  const open = alerts?.filter((a) => a.status === "open") ?? [];
  const others = alerts?.filter((a) => a.status !== "open") ?? [];

  return (
    <div className="space-y-5 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-100">Alerts</h1>
        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
            className="rounded border-gray-700 bg-gray-800 accent-brand-500"
          />
          Show resolved
        </label>
      </div>

      {isLoading ? (
        <div className="h-32 flex items-center justify-center text-gray-500">Loading…</div>
      ) : open.length === 0 && others.length === 0 ? (
        <AllClearCard />
      ) : (
        <div className="space-y-3">
          {open.length === 0 && !showResolved && <AllClearCard />}
          {open.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onDismiss={() => dismiss.mutate(alert.id)}
              onResolve={() => resolve.mutate(alert.id)}
              loading={dismiss.isPending || resolve.isPending}
            />
          ))}
          {showResolved && others.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide px-1">
                Resolved / Dismissed
              </p>
              {others.map((alert) => (
                <AlertCard key={alert.id} alert={alert} resolved />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AlertCard({
  alert,
  onDismiss,
  onResolve,
  loading,
  resolved,
}: {
  alert: Alert;
  onDismiss?: () => void;
  onResolve?: () => void;
  loading?: boolean;
  resolved?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const style = SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.info;

  return (
    <div
      className={`rounded-xl border border-gray-800 p-4 space-y-3 ${resolved ? "opacity-60" : ""}`}
    >
      <div className="flex items-start gap-3">
        <span className={`mt-1.5 h-2 w-2 rounded-full flex-shrink-0 ${style.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium text-gray-200">{alert.title}</p>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ${style.bg} ${style.text}`}
            >
              {alert.severity}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {formatDistanceToNow(new Date(alert.detected_at), { addSuffix: true })} ·{" "}
            <span className="capitalize">{alert.confidence} confidence</span>
          </p>
          <p className="text-sm text-gray-400 mt-2">{alert.summary}</p>
        </div>
      </div>

      {/* Expandable detail */}
      {(alert.evidence || alert.possible_causes || alert.recommended_actions) && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {expanded ? "Hide details" : "Show details"}
        </button>
      )}

      {expanded && (
        <div className="space-y-3 border-t border-gray-800 pt-3">
          {alert.evidence && alert.evidence.length > 0 && (
            <DetailSection title="Evidence" items={alert.evidence} />
          )}
          {alert.possible_causes && alert.possible_causes.length > 0 && (
            <DetailSection title="Possible Causes" items={alert.possible_causes} />
          )}
          {alert.recommended_actions && alert.recommended_actions.length > 0 && (
            <DetailSection title="Recommended Actions" items={alert.recommended_actions} />
          )}
        </div>
      )}

      {!resolved && (onDismiss || onResolve) && (
        <div className="flex gap-2 pt-1">
          {onResolve && (
            <button
              onClick={onResolve}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg bg-green-900 text-green-400 text-xs font-medium hover:bg-green-800 disabled:opacity-50 transition-colors"
            >
              Mark Resolved
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-400 text-xs font-medium hover:bg-gray-700 disabled:opacity-50 transition-colors"
            >
              Dismiss
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function DetailSection({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-400 mb-1">{title}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-xs text-gray-500 flex gap-2">
            <span className="text-gray-600">·</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AllClearCard() {
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-8 text-center space-y-2">
      <div className="w-10 h-10 rounded-full bg-green-900 flex items-center justify-center mx-auto">
        <span className="text-green-400 text-lg">✓</span>
      </div>
      <p className="text-gray-300 font-medium">No open alerts</p>
      <p className="text-sm text-gray-500">
        Battery anomaly detection runs automatically after each charge session.
      </p>
    </div>
  );
}
