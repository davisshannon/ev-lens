import { api } from "./client";
import type { ChargePlan, ChargeSession, Tariff } from "../types/charge";

export const chargesApi = {
  sessions: (vehicleId: string, limit = 50) =>
    api.get<ChargeSession[]>(`/charges/${vehicleId}/sessions`, { params: { limit } }).then((r) => r.data),

  plans: (vehicleId: string) =>
    api.get<ChargePlan[]>(`/charges/${vehicleId}/plans`).then((r) => r.data),

  createPlan: (vehicleId: string, body: {
    vehicle_id: string;
    current_soc: number;
    target_soc: number;
    tariff_id?: string;
    departure_time?: string;
  }) => api.post<ChargePlan>(`/charges/${vehicleId}/plan`, body).then((r) => r.data),

  postChargeReport: (vehicleId: string, planId: string) =>
    api.get(`/charges/${vehicleId}/plans/${planId}/report`).then((r) => r.data),

  tariffs: () => api.get<Tariff[]>("/tariffs").then((r) => r.data),

  createTariff: (body: Omit<Tariff, "id">) =>
    api.post<Tariff>("/tariffs", body).then((r) => r.data),

  updateTariff: (tariffId: string, body: Omit<Tariff, "id">) =>
    api.put<Tariff>(`/tariffs/${tariffId}`, body).then((r) => r.data),

  deleteTariff: (tariffId: string) => api.delete(`/tariffs/${tariffId}`),

  assignTariff: (tariffId: string, vehicleId: string) =>
    api.post(`/tariffs/${tariffId}/assign/${vehicleId}`).then((r) => r.data),
};
