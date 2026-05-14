import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { batteryApi } from "../api/battery";

export function useBatteryEstimates(vehicleId: string | undefined, limit = 30) {
  return useQuery({
    queryKey: ["battery-estimates", vehicleId, limit],
    queryFn: () => batteryApi.estimates(vehicleId!, limit),
    enabled: !!vehicleId,
    staleTime: 300_000,
  });
}

export function useLatestBatteryEstimate(vehicleId: string | undefined) {
  return useQuery({
    queryKey: ["battery-estimate-latest", vehicleId],
    queryFn: () => batteryApi.latestEstimate(vehicleId!),
    enabled: !!vehicleId,
    staleTime: 300_000,
    retry: false,
  });
}

export function useDrives(vehicleId: string | undefined, days = 30) {
  return useQuery({
    queryKey: ["drives", vehicleId, days],
    queryFn: () => batteryApi.drives(vehicleId!, days),
    enabled: !!vehicleId,
    staleTime: 120_000,
  });
}

export function useCosts(vehicleId: string | undefined, months = 6) {
  return useQuery({
    queryKey: ["costs", vehicleId, months],
    queryFn: () => batteryApi.costs(vehicleId!, months),
    enabled: !!vehicleId,
    staleTime: 120_000,
  });
}

export function useAlerts(vehicleId: string | undefined, includeResolved = false) {
  return useQuery({
    queryKey: ["alerts", vehicleId, includeResolved],
    queryFn: () => batteryApi.alerts(vehicleId!, includeResolved),
    enabled: !!vehicleId,
    staleTime: 60_000,
  });
}

export function useDismissAlert(vehicleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => batteryApi.dismissAlert(vehicleId, alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", vehicleId] });
    },
  });
}

export function useResolveAlert(vehicleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => batteryApi.resolveAlert(vehicleId, alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", vehicleId] });
    },
  });
}
