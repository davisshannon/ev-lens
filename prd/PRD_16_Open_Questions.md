# PRD 16: Open Questions

These should be resolved before implementation beyond MVP skeleton:

1. Will the first implementation use official Tesla Fleet API from day one, or start with stubs/import while credentials/API registration are handled separately?
2. Should the product be self-hosted-only initially, or designed for hosted/hybrid from day one?
3. Is Home Assistant integration mandatory for v0.1 or v0.2?
4. Should Fronius support be direct, via Home Assistant, or both?
5. Should Wall Connector telemetry be treated as best-effort because local access is not a formal stable product API?
6. Is the first user only one vehicle, or should multi-vehicle be part of the initial data model? This PRD assumes multi-vehicle schema but one-vehicle UI.
7. Should AI explanations use local models, hosted APIs, or pluggable provider configuration?
8. What is the product name? Avoid Tesla-specific names.

---

# Final Product Definition

EV Lens is not a TeslaMate clone.

It is a local-first EV intelligence platform that uses vehicle telemetry, charge sessions, tariff data, home energy context, and explainable anomaly detection to answer practical ownership questions.

The first product should win on one question:

**What is the smartest, cheapest, safest way to charge my car tonight, and did it actually work?**
