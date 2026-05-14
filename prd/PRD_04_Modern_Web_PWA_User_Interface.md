# PRD 4: Modern Web/PWA User Interface

## 4.1 Objective

Replace Grafana-first UX with a modern web app that answers ownership questions directly.

## 4.2 Navigation

Primary navigation:

```text
Today
Charging
Battery
Drives
Costs
Alerts
Settings
```

Later:

```text
Home Energy
Garage
Automations
Ask
```

## 4.3 Screens

### Today

Purpose: daily summary.

Cards:

- current SoC;
- location;
- plugged-in status;
- target/departure;
- recommended charge start;
- latest drive efficiency;
- last 24h drain;
- active alerts.

Example copy:

```text
Current SoC: 63%
Target: 80% by 7:00am
Recommended start: 12:35am at 32A
Expected cost: $2.84
Confidence: High
```

### Charging

Features:

- current charging status;
- charge plan form;
- tariff selector;
- amperage selector;
- recent charge sessions;
- planned vs actual chart;
- efficiency trend.

### Battery

Features:

- estimated usable capacity;
- degradation trend;
- confidence score;
- calibration quality;
- charge habits;
- high-SoC dwell time;
- battery-friendly recommendations.

### Drives

Features:

- drive list;
- efficiency;
- distance;
- energy;
- elevation if available;
- map optional;
- compare against baseline.

### Costs

Features:

- monthly charge cost;
- home vs away;
- tariff breakdown;
- solar vs grid if integrated;
- cost per 100 km;
- export CSV.

### Alerts

Features:

- unusual drain;
- charger derating;
- interrupted charge;
- unusually poor efficiency;
- provider/API issues;
- battery-estimate confidence degradation.

### Settings

Features:

- vehicle provider;
- tariff;
- home charger;
- home location;
- privacy/export;
- backup;
- integrations;
- telemetry polling mode.

## 4.4 Design Requirements

- Mobile-first.
- Responsive desktop layout.
- Light/dark mode.
- No Grafana dependency for primary user workflows.
- Grafana can remain optional/export-only later.
- Use plain explanations, not raw telemetry field names.
- Every recommendation must show "why".

## 4.5 Suggested Frontend Stack

- React + Vite or Next.js
- TypeScript
- Tailwind
- Recharts
- TanStack Query
- Zustand or Redux Toolkit only if needed
- PWA support

## 4.6 API Contracts

Frontend should consume REST APIs from backend.

Example charge-plan response:

```json
{
  "vehicle_id": "uuid",
  "current_soc_pct": 63,
  "target_soc_pct": 80,
  "departure_time": "2026-05-15T07:00:00+10:00",
  "recommended_start_time": "2026-05-15T00:35:00+10:00",
  "recommended_stop_time": "2026-05-15T03:12:00+10:00",
  "recommended_amps": 32,
  "expected_wall_kwh": 19.8,
  "expected_cost": 1.58,
  "confidence": "high",
  "explanation": [
    "Off-peak pricing is available from 00:00 to 06:00.",
    "32A charging provides enough energy in approximately 2h 37m.",
    "Starting at 00:35 completes well before departure while avoiding unnecessary time at high SoC."
  ]
}
```

## 4.7 Acceptance Criteria

- User can complete onboarding from empty state.
- User can see current vehicle summary.
- User can generate a charge plan on mobile.
- User can view recent charge sessions.
- User can understand why a recommendation was made.
- UI handles provider disconnected/error state gracefully.
- PWA install works on mobile browser.
- No page requires Grafana.

## 4.8 Claude/Codex Build Prompt

```text
Build the EV Lens frontend as a modern TypeScript React PWA.

Implement Today, Charging, Battery, Drives, Costs, Alerts, and Settings screens. Use Tailwind, TanStack Query, and Recharts. Consume the backend REST APIs. Focus on mobile-first layouts and clear explanations. Include empty states, loading states, error states, and mocked API fixtures for local frontend development. Do not depend on Grafana for any primary user workflow.
```

---
