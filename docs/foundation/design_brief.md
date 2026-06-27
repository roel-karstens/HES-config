# Design Brief

## Product
Home Energy System Configurator & Optimizer

## Purpose
Build an interactive web app that helps a homeowner understand how different energy system components affect daily energy flows, electricity cost, and savings.

## Primary Outcomes
- Configure a home energy setup in seconds.
- See immediate impact on energy and cost metrics.
- Provide a believable, deterministic simulation that is easy to explain.
- Create a stable base for optimization and scenario comparison.

## Users
- Homeowners evaluating solar and battery options.
- Installers or consultants preparing first-pass proposals.
- Product/design/engineering team members validating simulation UX.

## Core Experience
- Simple-first UI with progressive disclosure.
- Real-time simulation updates with no page clutter.
- Clear KPI cards for cost and energy performance.
- One primary chart and one secondary cumulative chart.

## UI Simplicity Principles
- Default to Basic Mode and hide advanced controls behind an expander.
- Keep one primary question per panel: where energy came from, what it cost.
- Use plain labels: "Power from grid" and "Solar coverage".
- Add delta chips showing what changed after input updates.

## Recommended Core Visuals
- Primary: hourly grid exchange and demand/supply context.
- Secondary: cumulative import cost, cumulative export revenue, and cumulative net cost over time.
- Optional: keep battery detail in a separate tab so the default view remains simple.

## Scope for MVP
- 24-hour simulation at hourly resolution.
- Configurable: solar, battery, EV, heat pump, airco, household load, economics.
- Deterministic dispatch rules and transparent assumptions.
- Financial summary and key energy metrics.
- Heuristic optimization toggle.

## Presets and Scenarios (MVP+)
- System templates via dropdown.
- Day scenarios via dropdown.
- Occupancy and car-presence modifiers.

### System Templates
- All-electric full system (solar + battery + EV + heat pump + airco).
- All-electric no battery.
- All-electric no battery, no EV.
- All-electric no battery, no EV, no heat pump.
- Grid-only baseline (no solar, no battery, no EV, no heat pump, no airco).

### Day Scenarios
- Sunny 20C day.
- Cloudy 20C day.
- Sunny 0C day.
- Cloudy 0C day.
- Car home.
- No car home.

## Non-goals for MVP
- Utility bill-grade accuracy.
- External weather APIs.
- Account system or persistence layer.
- Production hardening and multi-tenant architecture.

## AI Development Quality Principles
- Keep assumptions explicit and inspectable in code.
- Prefer deterministic logic over hidden heuristics.
- Validate with quick invariants (energy balance, SOC bounds).
- Use small, reviewable commits and short feedback loops.
- Preserve explainability in both code and UI.

## Success Criteria
- User can move sliders and see stable updates under 250 ms perceived latency.
- KPI outputs remain numerically consistent with hourly charts.
- Simulation never violates battery or energy balance constraints.
- README and planning docs allow a new contributor to start in under 10 minutes.

## Risks
- Metric naming confusion (solar utilization vs solar coverage).
- Baseline comparison assumptions can bias savings interpretation.
- Over-styling can reduce readability and maintainability.
- Too many controls in one screen can overwhelm first-time users.

## Mitigations
- Keep metric definitions in one section and link in UI help text.
- Document baseline assumptions clearly.
- Add lightweight tests for simulation sanity.
- Keep Basic Mode as default with presets before fine-grained sliders.
