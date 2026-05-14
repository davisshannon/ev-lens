export interface Vehicle {
  id: string;
  provider: string;
  provider_vehicle_id: string;
  vin: string | null;
  display_name: string | null;
  model: string | null;
  year: number | null;
  timezone: string;
  nominal_battery_kwh: number | null;
  created_at: string;
  updated_at: string;
}

export interface Snapshot {
  id: number;
  vehicle_id: string;
  observed_at: string;
  battery_level: number | null;
  usable_battery_level: number | null;
  battery_range_km: number | null;
  est_battery_range_km: number | null;
  charging_state: string | null;
  charge_limit_soc: number | null;
  charger_power_kw: number | null;
  charger_voltage: number | null;
  charger_actual_current: number | null;
  charger_phases: number | null;
  plugged_in: boolean | null;
  latitude: number | null;
  longitude: number | null;
  speed_kmh: number | null;
  odometer_km: number | null;
  vehicle_state: string | null;
  inside_temp_c: number | null;
  outside_temp_c: number | null;
  climate_on: boolean | null;
  sentry_mode: boolean | null;
  locked: boolean | null;
}

export interface ProviderHealth {
  healthy: boolean;
  last_success_at: string | null;
  last_error: string | null;
  recent_errors: number;
}
