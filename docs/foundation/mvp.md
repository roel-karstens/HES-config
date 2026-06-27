# MVP Plan

## MVP Goal
Deliver a reliable, explainable Streamlit app that simulates a home's 24-hour energy behavior and reports clear financial impact.

## Definition of Done
- Sidebar includes required basic configuration inputs with an Advanced section.
- Simulation returns hourly arrays for generation, demand, storage, and grid exchange.
- Dashboard shows financial summary and energy metrics.
- Main energy flow visualization reflects battery charge and discharge.
- Cumulative cost/revenue chart is available in default dashboard view.
- System templates and day scenarios are selectable from dropdowns.
- App launches with a single command.
- Core logic has at least basic sanity tests.

## Functional Checklist
- Solar settings: size and efficiency.
- Battery settings: capacity, power, initial SOC, enabled toggle.
- EV settings: enabled, weekly demand, fixed/flexible mode.
- Heat pump settings: enabled, daily demand.
- AIRCO settings: enabled, daily demand, cooling intensity.
- Household settings: base daily load, peak multiplier.
- Economics: import price, feed-in tariff, TOU toggle.
- Optimization toggle: heuristic mode.
- System template dropdown with one-click load.
- Day scenario dropdown (sun/temperature and occupancy modifiers).

## Technical Checklist
- Keep simulation logic in one module.
- Keep UI and business logic separated.
- Keep config in dataclasses.
- Add predictable helper functions for profiles.
- Keep dependencies minimal.
- Preserve backward-compatible defaults when new controls are added.

## Test Checklist
- Battery SOC remains within [0, capacity].
- Grid import/export never negative in their own channels.
- Hourly conservation checks are plausible and stable.
- Savings calculation is consistent with cost outputs.
- AIRCO profile contributes correctly when enabled.
- Preset selection updates all intended controls deterministically.

## MVP Milestones (Evening Build)
1. Introduce Basic Mode defaults with reduced cognitive load.
2. Add template and day scenario dropdowns.
3. Add AIRCO component to model and simulation.
4. Add cumulative cost/revenue/net chart.
5. Expand sanity tests for AIRCO and preset consistency.
6. Polish README and usage examples.

## Stretch After MVP
- Scenario comparison A vs B.
- Improved cost optimizer with LP.
- ROI assumptions editor.
