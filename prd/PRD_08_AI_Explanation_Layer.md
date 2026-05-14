# PRD 8: AI Explanation Layer

## 8.1 Objective

Add natural-language explanations grounded in telemetry and alerts.

This is not a generic chatbot. It is an evidence renderer and reasoning assistant over structured data.

## 8.2 Core Principle

The model may explain, summarise, and compare. It must not invent telemetry or issue vehicle commands.

## 8.3 MVP Questions

Support these question types:

```text
Why did my Tesla lose battery overnight?
Why did charging take longer than expected?
Why did charging speed drop?
Was last night's charge cheaper than usual?
Is my battery health estimate reliable?
Was that drive inefficient?
What should I change before tonight's charge?
```

## 8.4 Retrieval Context

For each question, backend should collect relevant structured context before calling an LLM:

- latest vehicle state;
- relevant charge sessions;
- relevant drive sessions;
- alerts;
- tariff;
- weather, optional;
- home energy, optional;
- battery estimate;
- confidence values.

## 8.5 Response Format

```markdown
### Answer
Brief answer.

### Evidence
- Specific telemetry point
- Specific session
- Specific comparison against baseline

### Confidence
High / Moderate / Low

### What to do next
- Action 1
- Action 2
```

## 8.6 Guardrails

- No remote vehicle commands.
- No unsupported safety claims.
- No medical/legal/insurance claims.
- Do not infer location-sensitive details unless already visible to the user.
- If data is insufficient, say so.
- Every answer must cite internal telemetry objects by ID or timestamp.
- LLM output should be validated to ensure it includes evidence and confidence.

## 8.7 Data Model

### ai_explanations

```sql
CREATE TABLE ai_explanations (
  id UUID PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  user_question TEXT NOT NULL,
  context_summary JSONB NOT NULL,
  answer_markdown TEXT NOT NULL,
  confidence TEXT NOT NULL,
  model TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## 8.8 Acceptance Criteria

- User can ask supported telemetry questions.
- Backend retrieves relevant context deterministically.
- Response includes answer, evidence, confidence, and next steps.
- If insufficient data exists, response says so.
- LLM is not allowed to issue commands.
- Tests validate output structure.

## 8.9 Claude/Codex Build Prompt

```text
Build the EV Lens AI explanation layer.

Create a backend service that answers natural-language questions about vehicle telemetry using deterministic retrieval over charge sessions, drive sessions, alerts, battery estimates, and tariff data. The LLM should only explain provided context. It must not invent data or issue vehicle commands. Responses must include Answer, Evidence, Confidence, and What to do next. Store explanations in ai_explanations. Include schema validation for model output and tests for insufficient-data, charging-delay, vampire-drain, and battery-confidence questions.
```

---
