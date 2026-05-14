import { useQuery } from "@tanstack/react-query";
import { vehiclesApi } from "../api/vehicles";

export function useVehicles() {
  return useQuery({
    queryKey: ["vehicles"],
    queryFn: vehiclesApi.list,
    staleTime: 60_000,
  });
}

export function useLatestSnapshot(vehicleId: string | undefined) {
  return useQuery({
    queryKey: ["snapshot", "latest", vehicleId],
    queryFn: () => vehiclesApi.latestSnapshot(vehicleId!),
    enabled: !!vehicleId,
    refetchInterval: 60_000, // refresh every 60s
  });
}

export function useSnapshots(vehicleId: string | undefined, limit = 288) {
  return useQuery({
    queryKey: ["snapshots", vehicleId, limit],
    queryFn: () => vehiclesApi.snapshots(vehicleId!, limit),
    enabled: !!vehicleId,
    staleTime: 60_000,
  });
}

export function useProviderHealth(vehicleId: string | undefined) {
  return useQuery({
    queryKey: ["provider-health", vehicleId],
    queryFn: () => vehiclesApi.health(vehicleId!),
    enabled: !!vehicleId,
    refetchInterval: 120_000,
  });
}
