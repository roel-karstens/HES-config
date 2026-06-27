import math

from models import SystemConfig
from simulation import simulate


def _assert_close(a: float, b: float, tol: float = 1e-6) -> None:
    assert math.isclose(a, b, rel_tol=0.0, abs_tol=tol), f"Expected {a} ~= {b}"


def test_cost_kpis_match_hourly_series() -> None:
    result = simulate(SystemConfig())

    import_cost = float((result["grid_import"] * result["prices"]).sum())
    export_revenue = float((result["grid_export"] * SystemConfig().economics.feedin_tariff).sum())
    expected_daily_with = import_cost - export_revenue

    _assert_close(import_cost, expected_daily_with + result["daily_export_revenue"])
    _assert_close(export_revenue, result["daily_export_revenue"])
    _assert_close(expected_daily_with, result["daily_cost_with_system"])

    expected_baseline = float((result["total_demand"] * result["prices"]).sum())
    _assert_close(expected_baseline, result["daily_cost_baseline"])

    expected_savings = expected_baseline - expected_daily_with
    _assert_close(expected_savings, result["daily_savings"])

    if expected_baseline > 0:
        expected_savings_pct = expected_savings / expected_baseline * 100.0
        _assert_close(expected_savings_pct, result["savings_pct"])


def test_energy_kpis_match_hourly_series() -> None:
    result = simulate(SystemConfig())

    total_solar = float(result["solar"].sum())
    total_demand = float(result["total_demand"].sum())
    total_import = float(result["grid_import"].sum())
    total_export = float(result["grid_export"].sum())

    _assert_close(total_solar, result["total_solar_kwh"])
    _assert_close(total_demand, result["total_demand_kwh"])
    _assert_close(total_import, result["total_import_kwh"])
    _assert_close(total_export, result["total_export_kwh"])

    solar_consumed = total_solar - total_export

    expected_self_consumption = (solar_consumed / total_solar * 100.0) if total_solar > 0 else 0.0
    expected_solar_util = (solar_consumed / total_demand * 100.0) if total_demand > 0 else 0.0
    expected_grid_dependency = (total_import / total_demand * 100.0) if total_demand > 0 else 0.0

    _assert_close(expected_self_consumption, result["self_consumption_pct"])
    _assert_close(expected_solar_util, result["solar_utilisation_pct"])
    _assert_close(expected_grid_dependency, result["grid_dependency_pct"])


def test_monthly_kpis_are_daily_times_30() -> None:
    result = simulate(SystemConfig())

    _assert_close(result["monthly_cost"], result["daily_cost_with_system"] * 30.0)
    _assert_close(result["monthly_baseline"], result["daily_cost_baseline"] * 30.0)
    _assert_close(result["monthly_savings"], result["daily_savings"] * 30.0)
