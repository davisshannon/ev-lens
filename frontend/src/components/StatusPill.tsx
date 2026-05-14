import { clsx } from "clsx";

type Status = "online" | "asleep" | "offline" | "charging" | "driving" | "unknown";

const LABEL: Record<Status, string> = {
  online: "Online",
  asleep: "Asleep",
  offline: "Offline",
  charging: "Charging",
  driving: "Driving",
  unknown: "Unknown",
};

const COLORS: Record<Status, string> = {
  online: "bg-green-900 text-green-300",
  asleep: "bg-gray-800 text-gray-400",
  offline: "bg-red-900 text-red-300",
  charging: "bg-blue-900 text-blue-300",
  driving: "bg-purple-900 text-purple-300",
  unknown: "bg-gray-800 text-gray-500",
};

interface Props {
  state: string | null;
  chargingState?: string | null;
}

function resolveStatus(state: string | null, chargingState?: string | null): Status {
  if (chargingState === "Charging") return "charging";
  if (state === "online") return "online";
  if (state === "asleep") return "asleep";
  if (state === "offline") return "offline";
  return "unknown";
}

export function StatusPill({ state, chargingState }: Props) {
  const status = resolveStatus(state, chargingState);
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", COLORS[status])}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {LABEL[status]}
    </span>
  );
}
