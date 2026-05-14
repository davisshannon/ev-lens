import { api } from "./client";
import type { AiExplanation, AiExplainRequest } from "../types/ai";

export const aiApi = {
  explain: (body: AiExplainRequest) =>
    api.post<AiExplanation>("/ai/explain", body).then((r) => r.data),

  history: (vehicleId: string, limit = 20) =>
    api
      .get<AiExplanation[]>(`/ai/history/${vehicleId}`, { params: { limit } })
      .then((r) => r.data),
};
