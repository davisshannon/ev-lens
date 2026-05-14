import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { format } from "date-fns";
import type { Snapshot } from "../types/vehicle";

interface Props {
  snapshots: Snapshot[];
}

export function SocSparkline({ snapshots }: Props) {
  const data = [...snapshots]
    .reverse()
    .map((s) => ({
      t: s.observed_at,
      soc: s.usable_battery_level ?? s.battery_level,
    }))
    .filter((d) => d.soc !== null);

  if (data.length < 2) return null;

  return (
    <div className="h-24 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: -20 }}>
          <defs>
            <linearGradient id="socGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="t"
            tickFormatter={(v) => format(new Date(v), "HH:mm")}
            tick={{ fill: "#6b7280", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis domain={[0, 100]} hide />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 6 }}
            labelFormatter={(v) => format(new Date(v), "HH:mm")}
            formatter={(v: number) => [`${v}%`, "SoC"]}
            labelStyle={{ color: "#9ca3af", fontSize: 11 }}
            itemStyle={{ color: "#0ea5e9", fontSize: 12 }}
          />
          <Area
            type="monotone"
            dataKey="soc"
            stroke="#0ea5e9"
            strokeWidth={2}
            fill="url(#socGrad)"
            dot={false}
            activeDot={{ r: 3, fill: "#0ea5e9" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
