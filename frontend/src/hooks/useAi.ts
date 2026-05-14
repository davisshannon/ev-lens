import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../api/ai";
import type { AiExplainRequest } from "../types/ai";

export function useAiHistory(vehicleId: string | undefined, limit = 20) {
  return useQuery({
    queryKey: ["ai-history", vehicleId, limit],
    queryFn: () => aiApi.history(vehicleId!, limit),
    enabled: !!vehicleId,
    staleTime: 30_000,
  });
}

export function useAiExplain(vehicleId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AiExplainRequest) => aiApi.explain(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-history", vehicleId] });
    },
  });
}
