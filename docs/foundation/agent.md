# Agent Workflow Guide

## Purpose
Define a practical AI-assisted workflow for fast, safe iteration on this codebase.

## Working Agreement
- Keep changes modular and scoped to one intent per edit.
- Prefer deterministic logic and explicit assumptions.
- Do not mix feature work with broad refactors.
- Run quick verification after each change set.

## Prompting Pattern
Use this pattern for coding sessions:
1. Goal: one sentence outcome.
2. Constraints: what must not change.
3. Files: expected touchpoints.
4. Verification: how to confirm behavior.

Example:
- Goal: Add scenario comparison tab with A/B configs.
- Constraints: Keep existing simulation API stable.
- Files: app.py, models.py, simulation.py.
- Verification: chart and KPI deltas for both scenarios render correctly.

## Quality Gates per Iteration
- Gate 1: No runtime/editor errors in changed files.
- Gate 2: Simulation invariants still hold.
- Gate 3: README or docs updated if behavior changes.
- Gate 4: Commit message reflects user-facing impact.

## AI Safety and Reliability Practices
- Prefer transparent rules over opaque generated formulas.
- Avoid introducing hidden network dependencies.
- Record assumptions and limitations near affected logic.
- Keep numeric units consistent and visible.

## Coding Session Cadence (Evening MVP Sprint)
1. Plan 3-5 tasks max.
2. Implement smallest valuable slice.
3. Verify immediately.
4. Update docs and backlog.
5. Repeat.

## UI-First Delivery Rule
- Deliver simple interpretation before adding new controls.
- Keep Basic Mode stable while adding features in Advanced Mode.
- Each UI addition must answer one user question clearly.

## Suggested Backlog Order
1. Basic Mode layout with reduced visible controls.
2. System templates dropdown and day scenarios dropdown.
3. AIRCO component (model + simulation + UI).
4. Cumulative cost/revenue/net chart.
5. Baseline fairness and metric wording cleanup.
6. Scenario A/B comparison.
7. LP optimizer as optional mode.
