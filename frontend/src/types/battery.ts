export interface BatteryEstimate {
  id: string;
  vehicle_id: string;
  calculated_at: string;
  estimated_usable_kwh: number;
  nominal_kwh: number | null;
  degradation_pct: number | null;
  confidence: string;
  sessions_used: number;
  explanation: string[] | null;
}

export interface DriveSession {
  started_at: string;
  ended_at: string;
  distance_km: number | null;
  energy_kwh: number | null;
  efficiency_wh_per_km: number | null;
  start_soc: number | null;
  end_soc: number | null;
  max_speed_kmh: number | null;
  duration_minutes: number;
}

export interface CostSummary {
  period: string;
  total_cost: number;
  total_kwh: number;
  currency: string;
  session_count: number;
  avg_cost_per_kwh: number | null;
  avg_cost_per_100km: number | null;
  solar_kwh: number;
  grid_kwh: number;
  solar_pct: number;
}

export interface Alert {
  id: string;
  vehicle_id: string;
  detected_at: string;
  resolved_at: string | null;
  alert_type: string;
  severity: string;
  confidence: string;
  status: string;
  title: string;
  summary: string;
  evidence: string[] | null;
  possible_causes: string[] | null;
  recommended_actions: string[] | null;
}
