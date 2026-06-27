# Tonight Sprint Plan

## Target
Reach a stable and convincing MVP by the end of this coding session.

## Timebox
- Total: 3 to 4 hours
- Cadence: 35 to 45 minute focus blocks + 5 minute review breaks

## Priority Plan
1. Simple-first UX foundation
- Add Basic Mode with minimal controls.
- Move detailed controls into Advanced Mode expander.

2. Presets and scenarios
- Add system template dropdown (including AIRCO variants).
- Add day scenario dropdown (sun/temperature + car presence).

3. Model feature addition
- Add AIRCO config and profile to the simulation.
- Verify KPI consistency after AIRCO integration.

4. Interpretation clarity
- Add cumulative import cost, export revenue, and net cost chart.
- Keep one primary hourly chart as default.

5. Reliability guardrails
- Run tests/sanity_checks.py after each meaningful change.
- Add scenario-based checks for presets and AIRCO toggles.

## Definition of Done Tonight
- App launches cleanly from a fresh environment.
- Sanity checks pass.
- Metrics and charts are consistent and explainable in Basic Mode.
- Preset and scenario dropdowns work predictably.
- AIRCO can be enabled and reflected in outputs.
- README reflects current behavior and launch steps.
- Known limitations and next steps are documented.

## Quick Operating Checklist
- Start app with streamlit run app.py.
- Keep one terminal for app logs and one for checks.
- After each major change:
  - run python tests/sanity_checks.py
  - manually check at least one baseline and one high-load scenario

## Exit Notes Template
When ending the session, capture:
- What changed.
- What is verified.
- What is deferred to next session.
- First task for next session.
