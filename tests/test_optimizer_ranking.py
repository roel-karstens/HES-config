from models import UserGoals
from optimizer import evaluate_candidate, generate_candidates, rank_candidates


def test_rank_candidates_respects_budget_and_objective():
    bounds = {
        "solar_kwp": (0, 8),
        "battery_kwh": (0, 8),
        "heat_pump_enabled": True,
        "ev_enabled": True,
        "v2g_enabled": False,
        "charging_strategies": ["pv_optimized"],
    }
    steps = {"solar_kwp": 4, "battery_kwh": 4}

    context = {
        "import_price": 0.30,
        "feedin_tariff": 0.08,
        "household_kwh_day": 14.0,
        "heat_pump_kwh_day": 8.0,
        "ev_weekly_kwh": 60.0,
        "price_solar_per_kwp": 1250.0,
        "price_battery_per_kwh": 550.0,
        "budget_eur": 12000.0,
    }

    candidates = generate_candidates(bounds, steps)
    evals = [evaluate_candidate(c, context) for c in candidates]

    ranked = rank_candidates(evals, UserGoals(objective="highest_roi", budget_eur=12000.0))
    assert len(ranked) > 0
    assert all(r.capex_eur <= 12000.0 for r in ranked)

    ranked_payback = rank_candidates(evals, UserGoals(objective="fastest_payback", budget_eur=12000.0))
    assert len(ranked_payback) > 0
