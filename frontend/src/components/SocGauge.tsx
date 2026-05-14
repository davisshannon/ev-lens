import { clsx } from "clsx";

interface Props {
  soc: number;        // 0–100
  limitSoc?: number;  // charge limit indicator
  size?: "sm" | "md" | "lg";
}

const SIZE = { sm: 80, md: 120, lg: 160 };

export function SocGauge({ soc, limitSoc, size = "md" }: Props) {
  const dim = SIZE[size];
  const r = (dim / 2) * 0.8;
  const cx = dim / 2;
  const cy = dim / 2;
  const circumference = 2 * Math.PI * r;
  const filled = circumference * (soc / 100);

  const color =
    soc >= 60 ? "#22c55e" :   // green
    soc >= 30 ? "#eab308" :   // yellow
                "#ef4444";    // red

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: dim, height: dim }}>
      <svg width={dim} height={dim} className="-rotate-90">
        {/* Track */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#374151" strokeWidth={size === "lg" ? 12 : 8} />
        {/* Fill */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke={color}
          strokeWidth={size === "lg" ? 12 : 8}
          strokeDasharray={`${filled} ${circumference}`}
          strokeLinecap="round"
        />
        {/* Limit indicator */}
        {limitSoc !== undefined && (
          <circle
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke="#6b7280"
            strokeWidth={size === "lg" ? 3 : 2}
            strokeDasharray={`2 ${circumference - 2}`}
            strokeDashoffset={-(circumference * (limitSoc / 100))}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={clsx("font-bold tabular-nums", size === "lg" ? "text-3xl" : size === "md" ? "text-xl" : "text-sm")}>
          {Math.round(soc)}%
        </span>
        {size !== "sm" && (
          <span className="text-xs text-gray-400">SoC</span>
        )}
      </div>
    </div>
  );
}
