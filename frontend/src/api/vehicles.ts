import { api } from "./client";
import type { Vehicle, Snapshot, ProviderHealth } from "../types/vehicle";

export const vehiclesApi = {
  list: () => api.get<Vehicle[]>("/vehicles").then((r) => r.data),

  get: (id: string) => api.get<Vehicle>(`/vehicles/${id}`).then((r) => r.data),

  latestSnapshot: (id: string) =>
    api.get<Snapshot>(`/vehicles/${id}/snapshot/latest`).then((r) => r.data),

  snapshots: (id: string, limit = 288) =>
    api.get<Snapshot[]>(`/vehicles/${id}/snapshots`, { params: { limit } }).then((r) => r.data),

  health: (id: string) =>
    api.get<ProviderHealth>(`/vehicles/${id}/health`).then((r) => r.data),
};
