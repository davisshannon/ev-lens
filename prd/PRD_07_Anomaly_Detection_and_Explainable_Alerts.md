# PRD 7: Anomaly Detection and Explainable Alerts

## 7.1 Objective

Detect unusual EV behaviour and explain it using telemetry evidence.

## 7.2 Anomaly Types

MVP:

- unusual overnight/vampire drain;
- unexpected wakeups;
- charging efficiency drop;
- charging current derating;
- interrupted charging;
- unusually poor drive efficiency;
- provider/API data gaps.

Later:

- post-software-update behavioural shifts;
- tyre/pressure efficiency drift;
- HVAC-heavy consumption;
- location-specific charging issues;
- home electrical/load warning patterns.

## 7.3 Detection Philosophy

Use deterministic/statistical baselines first. AI may explain results, but it must not be the source of truth for detection.

Pattern:

```text
baseline → current observation → deviation → confidence → evidence → recommendation
```

## 7.4 Alert Object

```json
{
  "type": "charging_efficiency_drop",
  "severity": "medium",
  "confidence": "moderate",
  "title": "Charging efficiency was unusually low",
  "summary": "Last night's charging efficiency was 78%, compared with your normal home baseline of 91-94%.",
  "evidence": [
    "Session started at 00:12 and ended at 04:44.",
    "Estimated wall energy was 31.2 kWh.",
    "Battery energy added was 24.4 kWh.",
    "No comparable low-efficiency session was seen in the prior 30 days."
  ],
  "possible_causes": [
    "battery conditioning",
    "voltage sag",
    "charger derating",
    "measurement mismatch",
    "cold weather"
  ],
  "recommended_actions": [
    "Check whether HVAC or battery preconditioning was active.",
    "Review wall connector current and voltage during the session.",
    "Watch the next two home sessions before changing hardware assumptions."
  ]
}
```

## 7.5 Data Model

### alerts

```sql
CREATE TABLE alerts (
  id UUID PRIMARY KEY,
  vehicle_id UUID REFERENCES vehicles(id),
  alert_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  confidence TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence JSONB NOT NULL,
  possible_causes JSONB,
  recommended_actions JSONB,
  status TEXT DEFAULT 'open',
  created_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);
```

## 7.6 Detection Rules

### Vampire Drain

Inputs:

- parked duration;
- SoC start/end;
- sentry mode;
- cabin overheat protection;
- climate state;
- wake/sleep events;
- software update events if available.

Alert if:

- drain exceeds user baseline by threshold;
- or drain exceeds fixed absolute threshold where no baseline exists.

### Charging Efficiency Drop

Inputs:

- wall kWh;
- battery kWh;
- session location;
- temperature;
- charger current/voltage;
- prior home sessions.

Alert if:

- efficiency falls below baseline by configurable threshold.

### Derating

Inputs:

- expected charger power;
- observed power;
- current limit;
- voltage;
- interruptions.

Alert if:

- observed power persistently below configured expected power without user-selected amperage reduction.

## 7.7 Acceptance Criteria

- Alerts are generated deterministically from telemetry.
- Alerts include evidence and confidence.
- User can dismiss/resolve alerts.
- Same alert is not spammed repeatedly.
- Alerts link back to relevant session/snapshot.
- Tests cover normal, anomalous, and insufficient-baseline cases.

## 7.8 Claude/Codex Build Prompt

```text
Build the EV Lens anomaly detection and alerting module.

Implement deterministic detectors for vampire drain, charging efficiency drop, charging derating, interrupted charging, poor drive efficiency, and provider data gaps. Store alerts with severity, confidence, evidence, possible causes, and recommended actions. Add APIs to list, resolve, and inspect alerts. Make detectors baseline-aware and avoid spamming duplicate alerts. Include tests for normal behaviour, anomalous behaviour, and insufficient-baseline behaviour.
```

---
