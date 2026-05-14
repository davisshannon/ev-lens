# PRD 1: Platform Vision and Product Scope

## 1.1 Problem

EV owners who care about cost, battery health, charging behaviour, and home energy context have to choose between:

- self-hosted telemetry tools with strong data ownership but weak UX;
- polished cloud apps with weaker privacy/control;
- smart home integrations that are powerful but fragmented;
- manual spreadsheet-style reasoning for tariff, solar, charging current, and departure-time decisions.

The market gap is not another Tesla dashboard. The gap is a **modern EV intelligence layer** that turns telemetry into decisions and explanations.

## 1.2 Product Thesis

Build a local-first EV telemetry and charging intelligence platform that gives owners:

- self-hosted control similar to TeslaMate;
- polished consumer UX similar to Tessie/TeslaFi-style apps;
- smart charging recommendations based on tariffs, solar, home load, and departure time;
- explainable battery health estimates with confidence scoring;
- anomaly detection for vampire drain, charge derating, poor efficiency, and unusual behaviour;
- optional AI-assisted explanations grounded strictly in telemetry;
- extensibility through MQTT, Home Assistant, REST, webhooks, and future provider plugins.

## 1.3 Non-goals

Do not build these in the first phase:

- social leaderboards;
- insurance scoring;
- public fleet comparison;
- trip-planner clone;
- aggressive remote vehicle-control feature set;
- FSD/safety scoring claims;
- Tesla-only naming/branding;
- mobile-native apps before the PWA proves value;
- full commercial fleet management in MVP.

## 1.4 Target Users

### Primary Persona: Technical EV Owner

- Owns a Tesla or comparable connected EV.
- May already use TeslaMate, Home Assistant, solar monitoring, or smart energy tools.
- Wants local data ownership.
- Wants better answers than Grafana charts.
- Is willing to run Docker but expects a guided setup.

### Secondary Persona: Solar/TOU Optimiser

- Has solar, time-of-use electricity pricing, or EV night tariffs.
- Wants the cheapest and smartest charge plan.
- Does not care about raw telemetry unless it improves decisions.

### Later Persona: Small Fleet / Family Fleet

- Multiple vehicles.
- Wants cost allocation, charge reports, and anomaly alerts.
- Needs a hosted or managed deployment option.

## 1.5 Core User Promise

"Know what your EV is doing, what it costs, how the battery is aging, when to charge, and whether anything looks wrong, without surrendering your data by default."

## 1.6 Success Criteria

The MVP is successful if a user can:

1. Connect one Tesla.
2. Collect telemetry and charge sessions reliably for at least 14 days.
3. View current vehicle state, drives, charge sessions, and cost history in a modern UI.
4. Configure their tariff and home charger.
5. Receive a recommended charge plan for a target SoC and departure time.
6. Compare the completed charge against the plan.
7. Get at least basic battery health estimation with a confidence rating.
8. Export data and/or migrate from TeslaMate.
9. Use the system without exposing ports directly to the public internet.

---
