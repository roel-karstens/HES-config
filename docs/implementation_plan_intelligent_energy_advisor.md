# Intelligent Energy Advisor - Implementation Plan

## Purpose
Transform the current Home Energy System Configurator from a single-configuration simulator into an advisor that evaluates alternatives, ranks them by user goals, and explains recommendations in plain language.

This plan is implementation-focused and aligned with the current codebase:
- `app.py`
- `simulation.py`
- `optimizer.py`
- `models.py`
- `notebooks/energy_advisor_validation.ipynb`

## Product Outcomes
The feature is complete when the application can reliably answer:
- How many solar panels should I install?
- What battery size is optimal?
- Is a battery financially worth it?
- Is V2G attractive for my situation?
- Should I invest in larger PV or battery?

And each answer includes:
- expected savings
- required investment
- payback
- confidence
- explanation of why

## Current Baseline
What already exists:
- Deterministic hourly simulation for one day (`simulation.py`).
- TOU-aware import price option (`simulation.py`, `models.py`).
- Heuristic optimization helper (`optimizer.py`).
- Grid sweep UI and Pareto-style view in app (`app.py`).
- Validation notebook with profile/pricing/optimization exploration (`notebooks/energy_advisor_validation.ipynb`).

Key gap:
- Logic remains mostly single-day and technical; advice generation and explainability are not first-class modules.

## Scope and Non-Goals
In scope:
- Modular pricing engine (fixed, TOU, dynamic hourly).
- Hourly profile engine for major loads and behavior-driven EV patterns.
- Temperature-aware heating/cooling dynamics.
- Automatic design optimization and ranked recommendations.
- Explainable recommendation output.
- Advisor-first UI flow with progressive disclosure.

Out of scope for initial release:
- Real utility API integrations (use synthetic and imported files first).
- Full stochastic Monte Carlo uncertainty model.
- Full battery degradation physics for all chemistries (simple model first).

## Architecture Plan

### 1) Pricing Engine
Create new module: `pricing.py`

Responsibilities:
- Normalize price inputs to an hourly horizon.
- Support fixed, TOU, dynamic contracts.
- Provide default dummy dynamic yearly series when data is missing.

Proposed interfaces:

```python
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd

class ContractType(str, Enum):
    FIXED = "fixed"
    TOU = "tou"
    DYNAMIC = "dynamic"

@dataclass
class PricingInput:
    contract_type: ContractType
    flat_import_price: float
    feedin_price_flat: float
    tou_import_24h: np.ndarray | None = None
    dynamic_import_hourly: pd.Series | None = None
    dynamic_feedin_hourly: pd.Series | None = None

def generate_dummy_dynamic_prices(year: int = 2025, seed: int = 42, base_eur_per_kwh: float = 0.28) -> pd.Series: ...
def expand_hourly_series(raw: np.ndarray, horizon_hours: int) -> np.ndarray: ...
def resolve_import_prices(pricing: PricingInput, horizon_index: pd.DatetimeIndex) -> np.ndarray: ...
def resolve_feedin_prices(pricing: PricingInput, horizon_index: pd.DatetimeIndex) -> np.ndarray: ...
```

Decision rule for fallback:
- 24 values -> repeat daily.
- 168 values -> repeat weekly.
- 8760 values -> use as-is.
- Missing dynamic input -> generate dummy 8760 series.

### 2) Hourly Profile Engine
Create new module: `profiles.py`

Responsibilities:
- Build hourly demand and production profiles from user behavior.
- Keep assumptions explicit and inspectable.
- Return normalized, testable series.

Proposed interfaces:

```python
from dataclasses import dataclass
import pandas as pd

@dataclass
class OccupancyInputs:
    wfh_days_per_week: int
    weekend_behavior_factor: float

@dataclass
class EVBehaviorInputs:
    arrival_hour: int
    departure_hour: int
    target_kwh_by_departure: float
    smart_charging: bool

@dataclass
class ThermalInputs:
    heat_pump_kwh_day_nominal: float
    dhw_kwh_day_nominal: float
    indoor_setpoint_c: float

@dataclass
class ProfileInputs:
    household_kwh_day: float
    occupancy: OccupancyInputs
    ev: EVBehaviorInputs
    thermal: ThermalInputs

def build_household_profile(index: pd.DatetimeIndex, inputs: ProfileInputs) -> pd.Series: ...
def build_ev_profile(index: pd.DatetimeIndex, inputs: ProfileInputs, prices: pd.Series | None = None) -> pd.Series: ...
def build_heat_pump_profile(index: pd.DatetimeIndex, inputs: ProfileInputs, outside_temp_c: pd.Series) -> pd.Series: ...
def build_dhw_profile(index: pd.DatetimeIndex, inputs: ProfileInputs) -> pd.Series: ...
def build_solar_profile(index: pd.DatetimeIndex, pv_kwp: float, irradiance_norm: pd.Series, outside_temp_c: pd.Series) -> pd.Series: ...
def build_all_profiles(...) -> pd.DataFrame: ...
```

### 3) Temperature-aware Energy Model
Extend `simulation.py` and optionally split helper formulas into `physics.py`.

Responsibilities:
- Make outside temperature influence HP demand/COP.
- Optionally adjust battery efficiency by temperature.
- Keep deterministic and fast for optimization loops.

Proposed interfaces:

```python
import numpy as np

def heat_pump_cop(temp_c: np.ndarray, supply_temp_c: float = 35.0) -> np.ndarray: ...
def heating_demand_multiplier(temp_c: np.ndarray, comfort_temp_c: float = 18.0) -> np.ndarray: ...
def battery_efficiency_by_temp(temp_c: np.ndarray) -> np.ndarray: ...
```

### 4) Simulation Contract Upgrade
Enhance `simulation.py` with horizon-based simulation entry point while preserving existing 24h compatibility.

Proposed interfaces:

```python
from dataclasses import dataclass
import pandas as pd

@dataclass
class DispatchConfig:
    strategy: str  # immediate | pv_optimized | price_optimized
    peak_shaving_kw: float | None = None

@dataclass
class SimulationInputs:
    index: pd.DatetimeIndex
    demand_profiles: pd.DataFrame
    solar_profile: pd.Series
    import_prices: pd.Series
    feedin_prices: pd.Series
    outside_temp_c: pd.Series
    dispatch: DispatchConfig

@dataclass
class SimulationResult:
    hourly: pd.DataFrame
    kpis: dict
    economics: dict

def simulate_horizon(inputs: SimulationInputs) -> SimulationResult: ...
def compute_kpis(hourly_df: pd.DataFrame) -> dict: ...
def compute_economics(hourly_df: pd.DataFrame, capex: float) -> dict: ...
```

Backward compatibility requirement:
- Keep existing `simulate(cfg: SystemConfig) -> dict` operational for current UI.
- Internally route to horizon engine for 24h synthetic horizon where possible.

### 5) Optimization Engine
Refactor optimizer logic into candidate generation, evaluation, and ranking.

Primary location: `optimizer.py` (or split into `optimizer.py` and `recommendation.py`).

Proposed interfaces:

```python
from dataclasses import dataclass
from typing import Literal

Objective = Literal["lowest_bill", "highest_roi", "fastest_payback", "sustainability", "grid_independence"]

@dataclass
class UserGoals:
    objective: Objective
    budget_eur: float | None
    sustainability_weight: float = 0.0
    independence_weight: float = 0.0

@dataclass
class CandidateConfig:
    solar_kwp: float
    battery_kwh: float
    heat_pump_enabled: bool
    ev_enabled: bool
    v2g_enabled: bool
    charging_strategy: str

@dataclass
class CandidateEvaluation:
    candidate: CandidateConfig
    annual_savings_eur: float
    capex_eur: float
    payback_years: float
    score: float
    constraints_ok: bool
    evidence: dict

def generate_candidates(bounds: dict, step_sizes: dict) -> list[CandidateConfig]: ...
def evaluate_candidate(candidate: CandidateConfig, context: dict) -> CandidateEvaluation: ...
def rank_candidates(evals: list[CandidateEvaluation], goals: UserGoals) -> list[CandidateEvaluation]: ...
def pareto_front(evals: list[CandidateEvaluation]) -> list[CandidateEvaluation]: ...
```

Algorithm strategy:
- Stage A: coarse sweep across design space.
- Stage B: local refinement around top N candidates.
- Ranking by selected objective with budget and feasibility constraints.

### 6) Recommendation and Explainability Engine
Create module: `recommendation.py`

Responsibilities:
- Convert ranked evaluations into user-facing recommendations.
- Include rationale and confidence.
- Support direct answers to user questions.

Proposed interfaces:

```python
from dataclasses import dataclass

@dataclass
class Recommendation:
    title: str
    action: str
    why: list[str]
    expected_savings_eur_year: float
    investment_eur: float
    payback_years: float
    confidence: str  # low | medium | high
    evidence: dict

def recommend_top_configuration(ranked: list, top_n: int = 3) -> list[Recommendation]: ...
def explain_tradeoff(best: dict, alternatives: list[dict]) -> list[str]: ...
def answer_user_question(question: str, ranked: list, context: dict) -> Recommendation: ...
```

Confidence guideline:
- High: stable winner under sensitivity checks.
- Medium: winner changes under one major assumption.
- Low: highly sensitive to price/profile assumptions.

### 7) Advisor-first UI Flow
Update `app.py` from technical control surface to guided flow.

Target flow:
1. Goal priority.
2. Budget.
3. Home situation and behavior.
4. Recommended configuration with before/after impact.

UI principles:
- Progressive disclosure.
- Plain language over technical jargon.
- Impact cards with deltas and reasons.
- Advanced mode for power users.

## Data Model Changes
Extend `models.py` with new dataclasses while preserving existing config classes:
- `PricingInput`
- `ProfileInputs` and nested behavior inputs
- `SimulationInputs` and `SimulationResult`
- `UserGoals`, `CandidateConfig`, `CandidateEvaluation`
- `Recommendation`

Migration requirement:
- Existing app sliders and tests must continue to pass with default values.

## Testing Plan

### Unit Tests
Add tests under `tests/`:
- `test_pricing_fallbacks.py`
- `test_profiles_generation.py`
- `test_temperature_effects.py`
- `test_optimizer_ranking.py`
- `test_recommendation_explainability.py`

Core assertions:
- 24h/168h/8760 expansion correctness.
- Profile totals equal configured daily energy.
- Colder weather increases HP electric demand.
- Objective choice changes ranking appropriately.
- Recommendation includes all required fields.

### Regression Tests
Keep and extend existing tests:
- `test_sidebar_slider_behaviour.py`
- `test_kpi_formula_consistency.py`
- `test_sanity_checks.py`

### Notebook-based Validation
Use `notebooks/energy_advisor_validation.ipynb` as a validation harness for:
- profile visual sanity
- dynamic pricing behavior
- optimization trade-offs
- explainability examples

## Delivery Phases

### Phase 1 - Pricing and Profiles (MVP foundation)
Deliverables:
- `pricing.py` with fallback logic and dummy dynamic generator.
- `profiles.py` with hourly profile builders.
- Unit tests for pricing/profile correctness.

Exit criteria:
- Can generate hourly import/feed-in arrays for fixed/TOU/dynamic.
- Can generate inspectable weekly/yearly demand profiles from behavior inputs.

### Phase 2 - Temperature-aware Simulation
Deliverables:
- Temperature effects integrated into simulation horizon logic.
- Backward compatibility retained for existing 24h simulate function.
- Unit tests for temperature sensitivity.

Exit criteria:
- Cold vs mild scenarios produce expected HP and cost differences.

### Phase 3 - Optimizer Refactor and Ranking
Deliverables:
- Candidate generation/evaluation/ranking pipeline.
- Multi-objective support and budget constraints.
- Pareto extraction utility.

Exit criteria:
- App can produce top ranked candidates for each user objective.

### Phase 4 - Recommendation Engine
Deliverables:
- Recommendation object and explanation renderer.
- Question-answer mapping to simulation evidence.

Exit criteria:
- App can answer battery/PV/V2G value questions with transparent rationale.

### Phase 5 - Advisor UI
Deliverables:
- Step-by-step guided flow in `app.py`.
- Recommendation cards and before/after summaries.
- Advanced controls retained under expandable section.

Exit criteria:
- Non-technical user can complete flow and understand recommendation rationale.

## Performance and Runtime Targets
- Candidate evaluation must remain interactive for medium sweeps.
- Target under 2s for small design sweeps, under 10s for medium sweeps on local machine.
- Apply caching where deterministic functions are reused.

## Risks and Mitigations
Risk: False precision in recommendations.
Mitigation: Confidence score + assumption disclosure + sensitivity checks.

Risk: Scope growth from adding too many physical details early.
Mitigation: Keep deterministic model simple first, add complexity incrementally.

Risk: UI complexity remains high.
Mitigation: Advisor flow first, advanced controls hidden by default.

## Definition of Done
Feature is considered complete when:
- Pricing, profiles, and simulation support advisor-grade hourly modeling.
- Optimizer ranks candidate systems by explicit user goals.
- Recommendation engine outputs clear, explainable advice.
- UI delivers guided recommendation flow.
- Test suite covers pricing/profile/simulation/optimizer/recommendation pathways.
- Validation notebook demonstrates the end-to-end logic and assumptions.
