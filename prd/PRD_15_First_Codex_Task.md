# PRD 15: First Codex Task

```text
Implement the deterministic charge planning engine.

Inputs:
- current_soc_pct
- target_soc_pct
- usable_capacity_kwh
- departure_time
- now
- voltage
- amps
- phases
- expected_efficiency_pct
- tariff windows
- user mode: cheapest | fastest | battery_friendly | load_safe

Outputs:
- required_battery_kwh
- required_wall_kwh
- recommended_start_time
- recommended_stop_time
- recommended_amps
- expected_cost
- confidence
- explanation[]

Rules:
- Validate target_soc > current_soc.
- Validate departure_time > now.
- Calculate required kWh.
- Calculate charging power.
- Prefer cheapest tariff windows before departure.
- If battery_friendly or load_safe mode can succeed at lower amps, recommend lower amps.
- If insufficient time exists, return a structured insufficient_time result.
- Always include explanation strings.
- Add unit tests for flat tariff, TOU tariff, insufficient time, lower-amp success, and multi-window scheduling.
```

---
