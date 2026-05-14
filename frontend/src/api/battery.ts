import { api } from "./client";
import type { Alert, BatteryEstimate, CostSummary, DriveSession } from "../types/battery";

export const batteryApi = {
  estimates: (vehicleId: string, limit = 30) =>
    api
      .get<BatteryEstimate[]>(`/battery/${vehicleId}/estimates`, { params: { limit } })
      .then((r) => r.data),

  latestEstimate: (vehicleId: string) =>
    api.get<BatteryEstimate>(`/battery/${vehicleId}/estimates/latest`).then((r) => r.data),

  drives: (vehicleId: string, days = 30) =>
    api
      .get<DriveSession[]>(`/battery/${vehicleId}/drives`, { params: { days } })
      .then((r) => r.data),

  costs: (vehicleId: string, months = 6) =>
    api
      .get<CostSummary[]>(`/charges/${vehicleId}/costs`, { params: { months } })
      .then((r) => r.data),

  alerts: (vehicleId: string, includeResolved = false) =>
    api
      .get<Alert[]>(`/alerts/${vehicleId}`, { params: { include_resolved: includeResolved } })
      .then((r) => r.data),

  dismissAlert: (vehicleId: string, alertId: string) =>
    api.patch<Alert>(`/alerts/${vehicleId}/${alertId}/dismiss`).then((r) => r.data),

  resolveAlert: (vehicleId: string, alertId: string) =>
    api.patch<Alert>(`/alerts/${vehicleId}/${alertId}/resolve`).then((r) => r.data),
};
