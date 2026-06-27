"""Pytest-discoverable simulation sanity checks.

Also runnable directly:
    python tests/test_sanity_checks.py
"""

from __future__ import annotations

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import SystemConfig
from simulation import simulate


def _assert_close(lhs: float, rhs: float, tol: float = 1e-6) -> None:
    if abs(lhs - rhs) > tol:
        raise AssertionError(f"Expected values to be close: {lhs} vs {rhs}")


def _validate_run(cfg: SystemConfig, label: str) -> None:
    result = simulate(cfg)

    demand = np.asarray(result["total_demand"], dtype=float)
    solar = np.asarray(result["solar"], dtype=float)
    import_kwh = np.asarray(result["grid_import"], dtype=float)
    export_kwh = np.asarray(result["grid_export"], dtype=float)
    bat_chg = np.asarray(result["battery_charge"], dtype=float)
    bat_dis = np.asarray(result["battery_discharge"], dtype=float)
    soc = np.asarray(result["battery_soc"], dtype=float)
    airco = np.asarray(result["airco"], dtype=float)

    assert len(demand) == 24, f"{label}: demand should have 24 samples"
    assert len(solar) == 24, f"{label}: solar should have 24 samples"
    assert len(airco) == 24, f"{label}: AIRCO should have 24 samples"

    assert np.all(import_kwh >= -1e-9), f"{label}: grid import contains negative values"
    assert np.all(export_kwh >= -1e-9), f"{label}: grid export contains negative values"
    assert np.all(bat_chg >= -1e-9), f"{label}: battery charge contains negative values"
    assert np.all(bat_dis >= -1e-9), f"{label}: battery discharge contains negative values"

    cap = cfg.battery.capacity_kwh if cfg.battery.enabled else 0.0
    assert np.all(soc >= -1e-9), f"{label}: SOC dropped below zero"
    assert np.all(soc <= cap + 1e-9), f"{label}: SOC exceeded capacity"

    lhs = demand + export_kwh + bat_chg
    rhs = solar + bat_dis + import_kwh
    if not np.allclose(lhs, rhs, atol=1e-6):
        max_err = float(np.max(np.abs(lhs - rhs)))
        raise AssertionError(f"{label}: hourly energy balance failed (max err {max_err:.3e})")

    _assert_close(float(import_kwh.sum()), float(result["total_import_kwh"]))
    _assert_close(float(export_kwh.sum()), float(result["total_export_kwh"]))

    if cfg.airco.enabled:
        assert float(airco.sum()) > 0.0, f"{label}: AIRCO enabled but no cooling demand generated"
    else:
        assert float(airco.sum()) == 0.0, f"{label}: AIRCO disabled but cooling demand generated"


def _scenario_cases() -> list[tuple[str, SystemConfig]]:
    scenarios = [
        ("default", SystemConfig()),
        ("no_battery", SystemConfig()),
        ("high_solar_high_load", SystemConfig()),
        ("edge_zero_battery_capacity", SystemConfig()),
        ("airco_enabled", SystemConfig()),
    ]

    scenarios[1][1].battery.enabled = False

    scenarios[2][1].solar.kwp = 16.0
    scenarios[2][1].household.base_kwh_day = 26.0
    scenarios[2][1].ev.enabled = True
    scenarios[2][1].ev.weekly_kwh = 140.0
    scenarios[2][1].heat_pump.enabled = True
    scenarios[2][1].heat_pump.daily_kwh = 14.0

    scenarios[3][1].battery.enabled = True
    scenarios[3][1].battery.capacity_kwh = 0.0
    scenarios[3][1].battery.max_charge_kw = 3.0
    scenarios[3][1].battery.max_discharge_kw = 3.0

    scenarios[4][1].airco.enabled = True
    scenarios[4][1].airco.daily_kwh = 9.0
    scenarios[4][1].airco.intensity = 1.4
    return scenarios


@pytest.mark.parametrize("label,cfg", _scenario_cases(), ids=[name for name, _ in _scenario_cases()])
def test_simulation_sanity_scenarios(label: str, cfg: SystemConfig) -> None:
    _validate_run(cfg, label)


if __name__ == "__main__":
    for name, cfg in _scenario_cases():
        _validate_run(cfg, name)
    print("All sanity checks passed.")
