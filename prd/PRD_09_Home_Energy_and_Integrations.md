# PRD 9: Home Energy and Integrations

## 9.1 Objective

Connect EV charging behaviour to home energy context.

## 9.2 Integrations

MVP:

- manual tariff configuration;
- Home Assistant webhook/API import;
- MQTT output.

v0.2:

- Tesla Wall Connector local telemetry where available;
- Fronius inverter data;
- solar production;
- home load;
- Powerwall, if applicable;
- OCPP chargers.

## 9.3 Requirements

### Home Assistant

- Pull or receive entities:
  - solar generation;
  - grid import/export;
  - home load;
  - charger power;
  - charger current;
  - vehicle presence;
  - tariff sensor if available.
- Allow mapping HA entity IDs to EV Lens fields.

### MQTT

Publish:

```text
evlens/{vehicle_id}/state
evlens/{vehicle_id}/charging
evlens/{vehicle_id}/battery
evlens/{vehicle_id}/alerts
evlens/{vehicle_id}/charge_plan
```

Subscribe later:

```text
evlens/{vehicle_id}/target_soc
evlens/{vehicle_id}/departure_time
```

### Wall Connector

If supported:

- read connected status;
- session energy;
- current;
- voltage;
- phase data;
- charger temperature/status if available.

## 9.4 Data Model

### home_energy_samples

```sql
CREATE TABLE home_energy_samples (
  id BIGSERIAL PRIMARY KEY,
  observed_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  solar_kw DOUBLE PRECISION,
  grid_import_kw DOUBLE PRECISION,
  grid_export_kw DOUBLE PRECISION,
  home_load_kw DOUBLE PRECISION,
  charger_kw DOUBLE PRECISION,
  raw JSONB
);
```

### integrations

```sql
CREATE TABLE integrations (
  id UUID PRIMARY KEY,
  integration_type TEXT NOT NULL,
  name TEXT NOT NULL,
  config JSONB NOT NULL,
  enabled BOOLEAN DEFAULT true,
  last_success_at TIMESTAMPTZ,
  last_error TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## 9.5 Acceptance Criteria

- User can configure Home Assistant integration.
- User can map HA entities to energy fields.
- System stores home energy samples.
- Charge reports can include wall/home energy where available.
- MQTT publishes current state and alerts.
- Integration failures are visible.

## 9.6 Claude/Codex Build Prompt

```text
Build the EV Lens home energy integration module.

Implement integration records, Home Assistant entity mapping, home_energy_samples storage, and MQTT publishing for vehicle state, charging, battery, alerts, and charge plans. Add APIs and UI settings for configuring Home Assistant URL/token and entity mappings. Include tests for sample ingestion, invalid mappings, MQTT payload generation, and integration error reporting.
```

---
