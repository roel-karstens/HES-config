# Home Energy System Configurator & Optimizer

Interactive Streamlit app to configure a home energy system and instantly simulate:
- energy flows (solar, load, battery, grid)
- daily and monthly electricity costs
- savings versus a baseline setup
- simple heuristic optimization behavior

Design direction for this MVP is simple interpretation first: one primary hourly chart, one cumulative financial chart, and presets before advanced tuning.

## Quick Summary

This project provides a deterministic 24-hour simulation (hourly resolution) for a residential energy setup with:
- solar PV
- battery storage
- EV charging
- heat pump demand
- airco demand
- household consumption profile

The app focuses on fast interactivity, clear metrics, and believable behavior for product exploration.

## Launch Locally

### 1) Create and activate a virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the app

```bash
streamlit run app.py
```

Open the local URL shown in the terminal (usually http://localhost:8501).

## Project Structure

- app.py: Streamlit UI, controls, dashboard, and Plotly charts.
- simulation.py: deterministic hourly energy model and KPI calculations.
- optimizer.py: heuristic optimization helpers and payback function.
- models.py: dataclasses for system configuration.
- docs/foundation/agent.md: AI-assisted development workflow and quality gates.
- docs/foundation/design_brief.md: product intent, scope, and success criteria.
- docs/foundation/mvp.md: definition of done, checks, and sprint milestones.
- docs/foundation/poc.md: proof-of-concept hypotheses and validation plan.

## What the App Computes

Per hour:
- solar generation
- household, EV, heat pump, and airco demand
- battery charge/discharge and state of charge
- grid import/export

Financial outputs:
- daily cost with system
- baseline daily cost without system
- daily savings and savings percentage
- export revenue
- monthly extrapolation

Energy metrics:
- self-consumption rate
- solar coverage/utilization
- grid dependency

## UI Strategy (Simple First)

- Basic Mode defaults with limited controls.
- Advanced Mode for detailed sliders and expert tuning.
- Presets for fast setup before manual fine-tuning.
- Cumulative financial chart for easier interpretation of cost timing.

### Planned System Templates
- All-electric full system (solar + battery + EV + heat pump + airco).
- All-electric no battery.
- All-electric no battery, no EV.
- All-electric no battery, no EV, no heat pump.
- Grid-only baseline (no solar, no battery, no EV, no heat pump, no airco).

### Planned Day Scenarios
- Sunny 20C.
- Cloudy 20C.
- Sunny 0C.
- Cloudy 0C.
- Car home.
- No car home.

## Current Boundaries

- 24-hour deterministic model (not utility-bill-grade physics).
- No external APIs and no database.
- Optimization is heuristic (not LP) by default.

## Recommended Next Session (MVP Sprint)

1. Improve baseline fairness assumptions and UI copy clarity.
2. Add scenario comparison (A vs B) with side-by-side KPI deltas.
3. Add dynamic day profiles for weather and occupancy.
4. Add optional LP optimizer mode behind a feature toggle.
5. Add chart export and preset persistence.

## Notes for AI-Assisted Development

Use the docs in docs/foundation as working references during coding:
- design_brief.md for scope guardrails
- mvp.md for done criteria
- poc.md for validation experiments
- agent.md for iteration cadence and quality gates
