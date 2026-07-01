"""Optimization utilities for heuristic and advisor-style ranking workflows."""
import copy

import numpy as np

from models import (
    AircoConfig,
    BatteryConfig,
    CandidateConfig,
    CandidateEvaluation,
    EconomicsConfig,
    EVConfig,
    HeatPumpConfig,
    HouseholdConfig,
    SolarConfig,
    SystemConfig,
    UserGoals,
)
from simulation import simulate


def _import_prices(cfg: SystemConfig) -> np.ndarray:
    from simulation import TOU_PRICES
    if cfg.economics.time_of_use:
        return TOU_PRICES * (cfg.economics.import_price / TOU_PRICES.mean())
    return np.full(24, cfg.economics.import_price)


def optimise(cfg: SystemConfig) -> SystemConfig:
    """
    Return a new SystemConfig with optimised settings applied.
    Heuristic strategy:
      1. If EV is flexible, shift charging to the cheapest solar hours.
      2. Battery: pre-charge to 20% SOC in cheapest off-peak hours
         (only when no solar is available) — a basic price-aware top-up.
    The optimised config is passed back into simulation.simulate() by the UI.
    """
    opt_cfg = copy.deepcopy(cfg)

    prices = _import_prices(opt_cfg)

    # ── EV optimisation ────────────────────────────────────────────────────────
    # If EV is flexible, mark it as flexible (simulation already handles this).
    # No extra change needed — flexible EV already charges during solar surplus.

    # ── Battery initial SOC optimisation ──────────────────────────────────────
    # If prices are flat (no TOU), default SOC is fine.
    # With TOU: pre-charge battery slightly in the cheapest night hours.
    if opt_cfg.economics.time_of_use and opt_cfg.battery.enabled and opt_cfg.battery.capacity_kwh > 0:
        # Find the cheapest 3 off-peak hours (no solar: hours 0-5 or 22-23)
        night_hours = list(range(0, 6)) + list(range(22, 24))
        night_prices = [(prices[h], h) for h in night_hours]
        night_prices.sort()
        cheapest_hours = [h for _, h in night_prices[:3]]
        # How much can we charge in those hours?
        charge_potential = len(cheapest_hours) * opt_cfg.battery.max_charge_kw
        target_soc_pct = min(
            80.0,
            opt_cfg.battery.initial_soc_pct + (charge_potential / opt_cfg.battery.capacity_kwh) * 100
        )
        opt_cfg.battery.initial_soc_pct = target_soc_pct

    return opt_cfg


def compute_payback(
    system_cost_eur: float,
    annual_savings_eur: float,
) -> float:
    """Simple payback period in years."""
    if annual_savings_eur <= 0:
        return float("inf")
    return system_cost_eur / annual_savings_eur


def generate_candidates(bounds: dict, step_sizes: dict) -> list[CandidateConfig]:
    solar_min, solar_max = bounds.get("solar_kwp", (0, 20))
    battery_min, battery_max = bounds.get("battery_kwh", (0, 20))
    max_pv_kwp = float(bounds.get("max_pv_kwp", 12.0))  # Constraint: default to realistic Dutch roof (~12 kWp)
    solar_max = min(solar_max, max_pv_kwp)  # Apply constraint
    solar_step = step_sizes.get("solar_kwp", 2)
    battery_step = step_sizes.get("battery_kwh", 2)

    hp_enabled = bool(bounds.get("heat_pump_enabled", True))
    ev_enabled = bool(bounds.get("ev_enabled", True))
    v2g_enabled = bool(bounds.get("v2g_enabled", False))
    strategies = bounds.get("charging_strategies", ["pv_optimized", "price_optimized"])

    out: list[CandidateConfig] = []
    for s in np.arange(solar_min, solar_max + 1e-9, solar_step):
        for b in np.arange(battery_min, battery_max + 1e-9, battery_step):
            for strat in strategies:
                out.append(
                    CandidateConfig(
                        solar_kwp=float(s),
                        battery_kwh=float(b),
                        heat_pump_enabled=hp_enabled,
                        ev_enabled=ev_enabled,
                        v2g_enabled=v2g_enabled,
                        charging_strategy=strat,
                    )
                )
    return out


def _build_system_for_candidate(candidate: CandidateConfig, context: dict) -> SystemConfig:
    import_price = float(context.get("import_price", 0.30))
    feedin_tariff = float(context.get("feedin_tariff", 0.08))
    household_kwh_day = float(context.get("household_kwh_day", 14.0))
    hp_kwh_day = float(context.get("heat_pump_kwh_day", 9.0))
    ev_weekly_kwh = float(context.get("ev_weekly_kwh", 60.0))
    ac_kwh_day = float(context.get("airco_kwh_day", 0.0))

    battery_enabled = candidate.battery_kwh > 0
    battery_pwr = max(0.5, candidate.battery_kwh / 3.0) if battery_enabled else 0.0
    use_tou = candidate.charging_strategy == "price_optimized"

    return SystemConfig(
        solar=SolarConfig(kwp=candidate.solar_kwp, efficiency=0.85),
        battery=BatteryConfig(
            capacity_kwh=candidate.battery_kwh,
            max_charge_kw=battery_pwr,
            max_discharge_kw=battery_pwr,
            initial_soc_pct=20,
            enabled=battery_enabled,
        ),
        ev=EVConfig(enabled=candidate.ev_enabled, weekly_kwh=ev_weekly_kwh, flexible=True),
        heat_pump=HeatPumpConfig(enabled=candidate.heat_pump_enabled, daily_kwh=hp_kwh_day),
        airco=AircoConfig(enabled=ac_kwh_day > 0, daily_kwh=ac_kwh_day, intensity=1.0),
        household=HouseholdConfig(base_kwh_day=household_kwh_day, peak_multiplier=2.0),
        economics=EconomicsConfig(import_price=import_price, feedin_tariff=feedin_tariff, time_of_use=use_tou),
    )


def evaluate_candidate(candidate: CandidateConfig, context: dict) -> CandidateEvaluation:
    cfg = _build_system_for_candidate(candidate, context)
    result = simulate(cfg)

    annual_savings = float(result["daily_savings"] * 365)
    p_solar = float(context.get("price_solar_per_kwp", 1250.0))
    p_batt = float(context.get("price_battery_per_kwh", 550.0))
    p_ev = float(context.get("price_ev_charger", 0.0 if not candidate.ev_enabled else 1300.0))
    p_hp = float(context.get("price_heat_pump", 0.0 if not candidate.heat_pump_enabled else 7000.0))

    capex = candidate.solar_kwp * p_solar + candidate.battery_kwh * p_batt + p_ev + p_hp
    payback = compute_payback(capex, annual_savings)

    # Efficiency-based score: rewards good ROI per euro invested (prevents oversizing)
    # Bonuses are minimal here; objective-specific scoring in rank_candidates handles them
    if capex > 0:
        score = annual_savings / capex * 1000.0  # Scale by 1000 for readability
    else:
        score = 0.0
    
    # Small bonuses for sustainability/independence (scaled down to not override efficiency)
    sustainability_bonus = float(result["solar_utilisation_pct"]) * 0.2  # Was 2.0, now 0.2
    independence_bonus = (100.0 - float(result["grid_dependency_pct"])) * 0.1  # Was 1.0, now 0.1
    score = score + sustainability_bonus + independence_bonus

    budget = context.get("budget_eur")
    constraints_ok = True if budget is None else (capex <= float(budget))

    evidence = {
        "annual_savings_eur": annual_savings,
        "daily_cost_with_system": float(result["daily_cost_with_system"]),
        "grid_dependency_pct": float(result["grid_dependency_pct"]),
        "self_consumption_pct": float(result["self_consumption_pct"]),
    }
    return CandidateEvaluation(
        candidate=candidate,
        annual_savings_eur=annual_savings,
        capex_eur=float(capex),
        payback_years=float(payback),
        score=float(score),
        constraints_ok=constraints_ok,
        evidence=evidence,
    )


def _objective_score(ev: CandidateEvaluation, goals: UserGoals) -> float:
    if goals.objective == "lowest_bill":
        return ev.annual_savings_eur
    if goals.objective == "highest_roi":
        return ev.score
    if goals.objective == "fastest_payback":
        return -ev.payback_years
    if goals.objective == "sustainability":
        return ev.score + goals.sustainability_weight * float(ev.evidence.get("self_consumption_pct", 0.0))
    if goals.objective == "grid_independence":
        return ev.score + goals.independence_weight * (100.0 - float(ev.evidence.get("grid_dependency_pct", 0.0)))
    return ev.score


def rank_candidates(evals: list[CandidateEvaluation], goals: UserGoals) -> list[CandidateEvaluation]:
    filtered = [e for e in evals if e.constraints_ok]
    if goals.budget_eur is not None:
        filtered = [e for e in filtered if e.capex_eur <= float(goals.budget_eur)]
    return sorted(filtered, key=lambda e: _objective_score(e, goals), reverse=True)


def pareto_front(evals: list[CandidateEvaluation]) -> list[CandidateEvaluation]:
    front: list[CandidateEvaluation] = []
    for p in evals:
        dominated = False
        for q in evals:
            better_or_equal_capex = q.capex_eur <= p.capex_eur
            better_or_equal_savings = q.annual_savings_eur >= p.annual_savings_eur
            strictly_better = (q.capex_eur < p.capex_eur) or (q.annual_savings_eur > p.annual_savings_eur)
            if better_or_equal_capex and better_or_equal_savings and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(p)
    return sorted(front, key=lambda e: e.capex_eur)
