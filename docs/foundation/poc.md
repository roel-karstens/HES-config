# PoC Plan

## Objective
Prove that the simulation model and UI interaction are coherent enough for decision support, even before advanced optimization.

## Hypotheses
- H1: Users understand the system faster with Basic Mode plus presets than with full control panels.
- H2: Users trust financial behavior more when a cumulative cost/revenue chart is visible.
- H3: AIRCO and temperature scenarios increase realism without harming interpretability.
- H4: A simple optimizer can reduce daily import cost in common setups.

## Minimal Experiments
1. Compare Basic Mode vs full controls for first-time interpretation speed.
2. Compare hourly-only charts vs hourly + cumulative chart for cost understanding.
3. Compare sunny/cloudy and 20C/0C scenarios with heat pump and AIRCO enabled.
4. Compare EV fixed vs flexible charging impact under same weekly demand.
5. TOU pricing enabled vs disabled for a battery-equipped home.

## Data to Capture (Manual for now)
- Daily cost with and without system.
- Savings percentage.
- Grid dependency percentage.
- Export revenue.
- Time to first meaningful configuration change.
- Whether user can explain cumulative net-cost trend correctly.
- Notes on chart interpretability.

## Acceptance Signals
- Cost and energy metrics move in expected directions when sliders change.
- No simulation anomalies under boundary values.
- Stakeholder can explain model behavior in plain language.
- Presets reduce setup time while preserving user confidence in outputs.

## Exit Criteria
- Team agrees the model is believable and stable enough for MVP expansion.
- Critical edge cases are documented.
- Priority backlog for next iteration is created.
