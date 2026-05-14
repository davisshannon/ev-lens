import { formatDistanceToNow } from "date-fns";
import { type ReactNode, useState } from "react";
import { useAiExplain, useAiHistory } from "../hooks/useAi";
import { useVehicles } from "../hooks/useVehicles";
import { useVehicleStore } from "../stores/vehicleStore";
import type { AiExplanation, QuestionType } from "../types/ai";

const QUESTION_TYPES: { value: QuestionType; label: string }[] = [
  { value: "general", label: "General" },
  { value: "vampire_drain", label: "Vampire drain" },
  { value: "battery_health", label: "Battery health" },
  { value: "charging_efficiency", label: "Charging efficiency" },
  { value: "costs", label: "Costs" },
];

const PLACEHOLDER_SUGGESTIONS = [
  "Why did my battery drain overnight?",
  "Was my last charge efficient?",
  "Explain my recent charging costs",
  "How is my battery health trending?",
  "What's causing my vampire drain?",
];

/** Minimal markdown renderer: bold (**text**), headings (##), bullet lists */
function SimpleMarkdown({ text }: { text: string }) {
  const paragraphs = text.split(/\n\n+/);

  return (
    <div className="space-y-3 text-sm text-gray-300 leading-relaxed">
      {paragraphs.map((para, pi) => {
        const lines = para.split("\n");

        // Heading: ## or ###
        if (/^#{2,3}\s/.test(lines[0])) {
          const heading = lines[0].replace(/^#{2,3}\s+/, "");
          return (
            <p key={pi} className="font-semibold text-gray-100 mt-1">
              {renderInline(heading)}
            </p>
          );
        }

        // Bullet list
        if (lines.every((l) => /^[-*]\s/.test(l.trim()) || l.trim() === "")) {
          return (
            <ul key={pi} className="space-y-1 pl-3">
              {lines
                .filter((l) => /^[-*]\s/.test(l.trim()))
                .map((l, li) => (
                  <li key={li} className="flex gap-2">
                    <span className="text-gray-600 flex-shrink-0">·</span>
                    <span>{renderInline(l.replace(/^[-*]\s+/, ""))}</span>
                  </li>
                ))}
            </ul>
          );
        }

        // Normal paragraph — render each line
        return (
          <p key={pi}>
            {lines.map((line, li) => (
              <span key={li}>
                {renderInline(line)}
                {li < lines.length - 1 && <br />}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function renderInline(text: string): ReactNode {
  // Split on **bold** markers
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="text-gray-100 font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function AssistantPage() {
  const { data: vehicles } = useVehicles();
  const { activeVehicleId } = useVehicleStore();
  const vehicleId = activeVehicleId ?? vehicles?.[0]?.id;

  const [question, setQuestion] = useState("");
  const [questionType, setQuestionType] = useState<QuestionType>("general");
  const [currentAnswer, setCurrentAnswer] = useState<AiExplanation | null>(null);

  const explain = useAiExplain(vehicleId);
  const { data: history } = useAiHistory(vehicleId, 5);

  if (!vehicleId) {
    return (
      <div className="text-center py-16 text-gray-500">
        No vehicle connected. Go to Settings to connect your Tesla.
      </div>
    );
  }

  async function handleAsk() {
    if (!question.trim() || !vehicleId) return;
    const result = await explain.mutateAsync({
      vehicle_id: vehicleId,
      question: question.trim(),
      question_type: questionType,
    });
    setCurrentAnswer(result);
    setQuestion("");
  }

  const noProviderError =
    currentAnswer?.error?.includes("No AI provider") ?? false;

  return (
    <div className="space-y-5 max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-100">AI Assistant</h1>

      {/* Ask card */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-3">
        {/* Question type selector */}
        <div className="flex flex-wrap gap-2">
          {QUESTION_TYPES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setQuestionType(value)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                questionType === value
                  ? "bg-brand-500 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Text area */}
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              void handleAsk();
            }
          }}
          placeholder={
            PLACEHOLDER_SUGGESTIONS[
              Math.floor(Math.random() * PLACEHOLDER_SUGGESTIONS.length)
            ]
          }
          rows={3}
          className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-brand-500 resize-none"
        />

        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-600">Cmd+Enter to send</p>
          <button
            onClick={() => void handleAsk()}
            disabled={explain.isPending || !question.trim()}
            className="px-4 py-2 rounded-lg bg-brand-500 text-white text-sm font-medium hover:bg-brand-500/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {explain.isPending ? "Thinking…" : "Ask"}
          </button>
        </div>
      </div>

      {/* Loading spinner */}
      {explain.isPending && (
        <div className="flex items-center justify-center py-8 text-gray-500 text-sm gap-2">
          <Spinner />
          <span>Generating answer…</span>
        </div>
      )}

      {/* Current answer */}
      {currentAnswer && !explain.isPending && (
        <AnswerCard explanation={currentAnswer} highlight />
      )}

      {/* No provider message */}
      {noProviderError && (
        <div className="rounded-xl bg-yellow-950 border border-yellow-800 p-4 space-y-2">
          <p className="text-sm font-medium text-yellow-400">AI provider not configured</p>
          <p className="text-xs text-yellow-300/70">
            To enable the AI assistant, add one of the following to your{" "}
            <code className="bg-yellow-900/50 px-1 rounded">.env</code> file and restart
            the server:
          </p>
          <ul className="text-xs text-yellow-300/70 space-y-1 pl-3">
            <li>· <code className="bg-yellow-900/50 px-1 rounded">ANTHROPIC_API_KEY=sk-ant-...</code></li>
            <li>· <code className="bg-yellow-900/50 px-1 rounded">OPENAI_API_KEY=sk-...</code></li>
            <li>· <code className="bg-yellow-900/50 px-1 rounded">XAI_API_KEY=xai-...</code></li>
            <li>· AWS credentials: <code className="bg-yellow-900/50 px-1 rounded">AWS_ACCESS_KEY_ID</code> + <code className="bg-yellow-900/50 px-1 rounded">AWS_SECRET_ACCESS_KEY</code></li>
          </ul>
        </div>
      )}

      {/* History */}
      {history && history.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Recent questions</p>
          {history
            .filter((h) => h.id !== currentAnswer?.id)
            .map((explanation) => (
              <AnswerCard key={explanation.id} explanation={explanation} />
            ))}
        </div>
      )}
    </div>
  );
}

function AnswerCard({
  explanation,
  highlight = false,
}: {
  explanation: AiExplanation;
  highlight?: boolean;
}) {
  const [expanded, setExpanded] = useState(highlight);

  return (
    <div
      className={`rounded-xl border p-4 space-y-2 ${
        highlight ? "border-brand-500/40 bg-gray-900" : "border-gray-800 bg-gray-900"
      }`}
    >
      {/* Question */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-200">{explanation.user_question}</p>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-gray-600 hover:text-gray-400 flex-shrink-0 transition-colors"
        >
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>

      {/* Metadata */}
      <p className="text-xs text-gray-600">
        {formatDistanceToNow(new Date(explanation.asked_at), { addSuffix: true })}
        {explanation.provider && (
          <span>
            {" "}· {explanation.provider}
            {explanation.model && ` (${explanation.model})`}
          </span>
        )}
        {explanation.confidence && (
          <span> · {explanation.confidence} confidence</span>
        )}
      </p>

      {/* Answer or error */}
      {expanded && (
        <div className="pt-2 border-t border-gray-800">
          {explanation.error ? (
            <p className="text-sm text-red-400">{explanation.error}</p>
          ) : explanation.answer_markdown ? (
            <SimpleMarkdown text={explanation.answer_markdown} />
          ) : (
            <p className="text-sm text-gray-500">No answer available.</p>
          )}
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 text-brand-500"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
