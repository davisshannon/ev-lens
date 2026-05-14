export interface AiExplanation {
  id: string;
  vehicle_id: string | null;
  asked_at: string;
  user_question: string;
  answer_markdown: string | null;
  confidence: string | null;
  provider: string | null;
  model: string | null;
  error: string | null;
}

export interface AiExplainRequest {
  vehicle_id: string;
  question: string;
  question_type: string;
}

export type QuestionType =
  | "general"
  | "vampire_drain"
  | "battery_health"
  | "charging_efficiency"
  | "costs";
