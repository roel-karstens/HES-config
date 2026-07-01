import numpy as np

from models import (
    AircoConfig,
    BatteryConfig,
    EVConfig,
    EconomicsConfig,
    HeatPumpConfig,
    HouseholdConfig,
    SolarConfig,
    SystemConfig,
)
from simulation import heat_pump_cop, simulate


def _cfg(hp_daily: float) -> SystemConfig:
    return SystemConfig(
        solar=SolarConfig(kwp=6.0, efficiency=0.85),
        battery=BatteryConfig(capacity_kwh=8.0, max_charge_kw=3.0, max_discharge_kw=3.0, initial_soc_pct=20, enabled=True),
        ev=EVConfig(enabled=False, weekly_kwh=0.0, flexible=True),
        heat_pump=HeatPumpConfig(enabled=True, daily_kwh=hp_daily),
        airco=AircoConfig(enabled=False, daily_kwh=0.0, intensity=1.0),
        household=HouseholdConfig(base_kwh_day=12.0, peak_multiplier=2.0),
        economics=EconomicsConfig(import_price=0.30, feedin_tariff=0.08, time_of_use=False),
    )


def test_heat_pump_cop_increases_with_temperature():
    cold = heat_pump_cop(np.array([-5.0]))[0]
    mild = heat_pump_cop(np.array([10.0]))[0]
    warm = heat_pump_cop(np.array([20.0]))[0]

    assert cold < mild < warm


def test_more_heat_pump_daily_kwh_increases_energy_demand_and_cost():
    low = simulate(_cfg(4.0))
    high = simulate(_cfg(14.0))

    assert float(high["heat_pump"].sum()) > float(low["heat_pump"].sum())
    assert high["daily_cost_with_system"] > low["daily_cost_with_system"]
