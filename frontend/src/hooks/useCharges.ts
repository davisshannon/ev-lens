import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chargesApi } from "../api/charges";

export function useChargeSessions(vehicleId: string | undefined) {
  return useQuery({
    queryKey: ["charge-sessions", vehicleId],
    queryFn: () => chargesApi.sessions(vehicleId!),
    enabled: !!vehicleId,
    staleTime: 60_000,
  });
}

export function useChargePlans(vehicleId: string | undefined) {
  return useQuery({
    queryKey: ["charge-plans", vehicleId],
    queryFn: () => chargesApi.plans(vehicleId!),
    enabled: !!vehicleId,
    staleTime: 30_000,
  });
}

export function useCreatePlan(vehicleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof chargesApi.createPlan>[1]) =>
      chargesApi.createPlan(vehicleId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["charge-plans", vehicleId] }),
  });
}

export function useTariffs() {
  return useQuery({
    queryKey: ["tariffs"],
    queryFn: chargesApi.tariffs,
    staleTime: 300_000,
  });
}
