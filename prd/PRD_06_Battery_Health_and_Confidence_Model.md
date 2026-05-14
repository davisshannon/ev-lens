# PRD 6: Battery Health and Confidence Model

## 6.1 Objective

Provide battery health insight without pretending noisy estimates are exact.

## 6.2 Problem

Most EV battery estimates are too confident. Vehicle-reported range, SoC, temperature, calibration state, charging window, and BMS behaviour can distort estimates.

The product should make uncertainty visible.

## 6.3 Core Features

- estimated usable battery capacity;
- degradation from nominal/new estimate;
- trend over time;
- calibration quality;
- confidence score;
- explanation of evidence quality;
- charge-habit insights.

## 6.4 Confidence Inputs

Confidence should consider:

- number of charge sessions;
- size of charge sessions in kWh;
- SoC range covered;
- sessions ending above 80%;
- sessions starting below 20–30%;
- temperature range;
- consistency of estimated capacity;
- recentness of data;
- odometer coverage;
- data gaps.

## 6.5 Confidence Levels

```text
Unknown: insufficient data
Low: noisy or sparse data
Moderate: enough data for directional estimate
High: repeated high-quality sessions with consistent estimates
```

## 6.6 Output Example

```json
{
  "estimated_usable_capacity_kwh": 76.4,
  "nominal_capacity_kwh": 79.0,
  "estimated_degradation_pct": 3.3,
  "confidence": "moderate",
  "evidence": {
    "charge_sessions_used": 18,
    "large_sessions_used": 6,
    "soc_span_quality": "medium",
    "temperature_adjusted": false,
    "recentness": "good"
  },
  "explanation": [
    "Estimate is based on 18 sessions, but only 6 added more than 20 kWh.",
    "Few low-to-high SoC sessions are available, so confidence is moderate rather than high.",
    "The latest estimate is consistent with the prior 30-day trend."
  ]
}
```

## 6.7 Data Model

### battery_estimates

```sql
CREATE TABLE battery_estimates (
  id UUID PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  calculated_at TIMESTAMPTZ DEFAULT now(),
  estimated_usable_capacity_kwh DOUBLE PRECISION,
  nominal_capacity_kwh DOUBLE PRECISION,
  estimated_degradation_pct DOUBLE PRECISION,
  confidence TEXT NOT NULL,
  evidence JSONB NOT NULL,
  explanation JSONB NOT NULL
);
```

## 6.8 Acceptance Criteria

- System produces "unknown" until enough data exists.
- System produces a confidence-scored capacity estimate after enough charge sessions.
- UI explains why confidence is low/moderate/high.
- System does not present degradation as overly precise.
- Battery estimate is recalculated after new qualifying charge sessions.
- Tests cover insufficient data, noisy data, and stable data.

## 6.9 Claude/Codex Build Prompt

```text
Build the EV Lens battery health module.

Implement a battery capacity estimation service using charge session data. Add confidence scoring based on data quantity, session size, SoC span, consistency, and recentness. Store estimates in battery_estimates. Expose API endpoints for latest estimate and historical estimates. The UI/API must never present battery degradation without a confidence level and evidence summary. Include tests for insufficient, noisy, moderate, and high-confidence data cases.
```

---
