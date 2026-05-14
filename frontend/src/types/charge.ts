export interface ChargeSession {
  id: string;
  vehicle_id: string;
  location_id: string | null;
  tariff_id: string | null;
  started_at: string;
  ended_at: string | null;
  start_soc: number | null;
  end_soc: number | null;
  charge_limit_soc: number | null;
  battery_kwh_added: number | null;
  wall_kwh_estimated: number | null;
  wall_kwh_actual: number | null;
  avg_power_kw: number | null;
  max_power_kw: number | null;
  avg_voltage: number | null;
  phases: number | null;
  charge_efficiency: number | null;
  cost_estimated: number | null;
  cost_currency: string | null;
  grid_kwh: number | null;
  solar_kwh: number | null;
  powerwall_kwh: number | null;
  energy_source: string | null;
  has_gap: boolean;
  incomplete: boolean;
  invalid: boolean;
  invalid_reason: string | null;
  imported_from: string | null;
}

export interface ChargePlan {
  id: string;
  vehicle_id: string;
  created_at: string;
  current_soc: number;
  target_soc: number;
  departure_time: string | null;
  recommended_start: string | null;
  recommended_stop: string | null;
  expected_kwh: number | null;
  expected_cost: number | null;
  expected_cost_currency: string | null;
  actual_kwh: number | null;
  actual_cost: number | null;
  confidence: string;
  explanation: string[] | null;
}

export interface Tariff {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  config: Record<string, unknown>;
}
