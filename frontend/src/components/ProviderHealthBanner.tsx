import { formatDistanceToNow } from "date-fns";
import type { ProviderHealth } from "../types/vehicle";

interface Props {
  health: ProviderHealth;
}

export function ProviderHealthBanner({ health }: Props) {
  if (health.healthy) return null;

  return (
    <div className="rounded-lg bg-red-950 border border-red-800 px-4 py-3 text-sm">
      <p className="font-medium text-red-300">Vehicle data may be stale</p>
      {health.last_error && (
        <p className="mt-1 text-red-400 text-xs">{health.last_error}</p>
      )}
      {health.last_success_at && (
        <p className="mt-1 text-red-500 text-xs">
          Last success {formatDistanceToNow(new Date(health.last_success_at))} ago
        </p>
      )}
    </div>
  );
}
