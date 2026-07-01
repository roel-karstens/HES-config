# Feature Spec: Lock-and-Optimize ROI Workflow

## Goal
Add an advisor-like optimization workflow that lets users:
1. start from current/default slider values,
2. lock selected sizing inputs,
3. run ROI optimization,
4. automatically apply best sizing to unlocked sliders,
5. immediately see KPI and donut chart updates.

This feature reduces manual trial-and-error and turns the configurator into a guided decision tool.

## User Story
As a homeowner using the configurator,
I want to lock settings I already know,
then click one button to optimize the remaining system sizing for ROI,
so I can quickly see the best configuration and its impact.

## UX Flow
1. User opens app and sees default slider values.
2. User sets/keeps desired values in System Sizing.
3. User locks one or more sizing fields.
4. User clicks `Optimize for ROI`.
5. App evaluates candidate combinations over unlocked dimensions only.
6. App writes best values back to unlocked sliders.
7. Existing simulation refreshes automatically.
8. KPI cards and donut charts reflect optimized configuration.
9. App shows a short optimization summary (what changed and why).

## Scope
In scope:
- Lock controls next to System Sizing sliders.
- ROI optimization trigger button.
- Slider state update with best candidate values.
- KPI + donut refresh through existing simulation pipeline.
- Optimization summary message.

Out of scope (future):
- Multi-objective switching in this specific flow (lowest bill, sustainability, etc.).
- Full undo history stack.
- Animated slider transitions.

## Settings Included in Lock-and-Optimize
Primary System Sizing fields:
- Household load (`hh_base`)
- Solar size (`solar_kwp`)
- Battery size (`bat_cap`)
- EV energy (`ev_daily`)
- Heat pump demand (`hp_daily`)
- AIRCO demand (`ac_daily`)

## Lock Behavior Rules
1. Locked slider values are strict constraints.
2. Unlocked sliders are decision variables.
3. If all sizing sliders are locked, optimization is disabled with clear feedback.
4. If no feasible candidate is found, slider state remains unchanged and warning is shown.
5. Locked values are never modified by optimizer.

## Optimization Behavior
### Objective
Primary objective: maximize ROI-oriented score.

Default score formula for this flow:
`score = annual_savings_eur - alpha * capex_eur`

Where:
- `alpha` defaults to `0.10` (configurable internally)
- constraints must be satisfied before ranking

### Tie-breakers
Apply in this order:
1. Lower payback years
2. Lower capex
3. Lower grid dependency

### Candidate Space
- Vary only unlocked dimensions
- Keep locked values fixed
- Use existing candidate generation + evaluation pipeline from optimizer module

## UI Components
### In Sidebar (System Sizing section)
For each sizing slider, add a lock toggle:
- Example label: `Lock Solar size`
- State key convention: `lock_<slider_key>`

### Action Control
- Button: `Optimize for ROI`
- Disabled when no variables are unlocked

### Optimization Summary Block
Show after run:
- Number of candidates evaluated
- Best found objective score
- Changed fields (`old -> new`)
- Estimated annual savings
- Estimated payback
- Confidence level (if available)

## State Management
Add session-state keys:
- `lock_hh_base`
- `lock_solar_kwp`
- `lock_bat_cap`
- `lock_ev_daily`
- `lock_hp_daily`
- `lock_ac_daily`
- `last_optimization_result`
- `last_optimization_applied_at`

Single source of truth remains slider session-state values.

## Integration Notes
Target integration file:
- `app.py`

Supporting modules already available:
- `optimizer.py` (candidate generation/evaluation/ranking)
- `recommendation.py` (optional summary text)
- `simulation.py` (KPI/flows refresh automatically after state update)

## Technical Sequence
1. Add lock toggles in sidebar near sizing sliders.
2. Build a mapping of locked/unlocked dimensions from session state.
3. On button click, build constrained bounds + context.
4. Run optimizer and rank candidates for ROI.
5. Apply best candidate values to unlocked sliders.
6. Trigger rerun (or rely on Streamlit state update flow).
7. Render optimization summary below controls or in main panel.

## Validation and Test Cases
### Functional
1. Optimizer changes only unlocked sliders.
2. Locked sliders remain unchanged.
3. KPI cards update after optimization.
4. Donut charts update after optimization.
5. `Optimize for ROI` disabled when all sliders locked.
6. No-feasible-solution path shows warning and preserves values.

### Regression
1. Existing slider behavior tests remain valid.
2. Existing simulation and KPI consistency tests remain valid.

## Acceptance Criteria
Feature is accepted when:
1. User can lock any subset of sizing sliders.
2. User can click `Optimize for ROI` and get new sizing values applied.
3. Applied values appear directly in sliders.
4. KPI and donut sections visibly reflect optimized configuration.
5. Feature behaves safely for all-locked and no-feasible cases.

## Future Enhancements
1. Add objective selector (`ROI`, `Lowest Bill`, `Fastest Payback`, `Grid Independence`).
2. Add `Preview recommendation` before apply.
3. Add one-click `Undo optimization`.
4. Add confidence computation based on sensitivity runs.
5. Add staged optimization (`coarse -> local refinement`) for larger spaces.
