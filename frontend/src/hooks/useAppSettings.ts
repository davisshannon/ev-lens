import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { appSettingsApi } from "../api/appSettings";

export function useAppSettings() {
  return useQuery({
    queryKey: ["app-settings"],
    queryFn: appSettingsApi.list,
    staleTime: 30_000,
  });
}

export function useSetSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      appSettingsApi.set(key, value),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["app-settings"] });
    },
  });
}

export function useClearSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => appSettingsApi.clear(key),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["app-settings"] });
    },
  });
}
