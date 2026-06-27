import math

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
from optimizer import optimise
from simulation import simulate


def _default_ui() -> dict:
    return {
        "sun_hours": 8,
        "ambient_temp_c": 20,
        "solar_kwp": 4.0,
        "bat_cap": 10.0,
        "ev_weekly": 60.0,
        "hp_daily": 8.0,
        "ac_daily": 4.0,
        "hh_base": 15.0,
        "import_price": 0.28,
        "feedin_tariff": 0.08,
    }


def _build_cfg_from_ui(ui: dict) -> SystemConfig:
    sun_factor = ui["sun_hours"] / 8.0

    solar_kwp = ui["solar_kwp"]
    bat_cap = ui["bat_cap"]
    ev_weekly = ui["ev_weekly"]
    hp_daily = ui["hp_daily"]
    ac_daily = ui["ac_daily"]

    solar_enabled = solar_kwp > 0
    bat_enabled = bat_cap > 0
    ev_enabled = ev_weekly > 0
    hp_enabled = hp_daily > 0
    ac_enabled = ac_daily > 0

    solar_kwp_effective = solar_kwp
    solar_eff_effective = max(0.0, min(2.2, 0.85 * sun_factor))

    hp_temp_mult = max(0.5, min(2.2, 1.0 + (18 - ui["ambient_temp_c"]) * 0.03))
    ac_temp_mult = max(0.3, min(2.5, 1.0 + (ui["ambient_temp_c"] - 22) * 0.04))
    hp_daily_effective = hp_daily * hp_temp_mult
    ac_daily_effective = ac_daily * ac_temp_mult

    ev_flex_effective = ui["sun_hours"] >= 8
    bat_pwr = max(0.5, min(10.0, bat_cap / 3.0)) if bat_enabled else 0.0

    return SystemConfig(
        solar=SolarConfig(kwp=solar_kwp_effective, efficiency=solar_eff_effective),
        battery=BatteryConfig(
            capacity_kwh=bat_cap,
            max_charge_kw=bat_pwr,
            max_discharge_kw=bat_pwr,
            initial_soc_pct=20,
            enabled=bat_enabled,
        ),
        ev=EVConfig(enabled=ev_enabled, weekly_kwh=ev_weekly, flexible=ev_flex_effective),
        heat_pump=HeatPumpConfig(enabled=hp_enabled, daily_kwh=hp_daily_effective),
        airco=AircoConfig(enabled=ac_enabled, daily_kwh=ac_daily_effective, intensity=1.0),
        household=HouseholdConfig(base_kwh_day=ui["hh_base"], peak_multiplier=2.0),
        economics=EconomicsConfig(
            import_price=ui["import_price"],
            feedin_tariff=ui["feedin_tariff"],
            time_of_use=False,
        ),
    )


def _simulate_ui(overrides: dict | None = None, smart: bool = False) -> dict:
    ui = _default_ui()
    if overrides:
        ui.update(overrides)
    cfg = _build_cfg_from_ui(ui)
    if smart:
        cfg = optimise(cfg)
    return simulate(cfg)


def test_sun_hours_increases_solar_and_reduces_import():
    low_sun = _simulate_ui({"sun_hours": 0})
    high_sun = _simulate_ui({"sun_hours": 16})

    assert high_sun["total_solar_kwh"] > low_sun["total_solar_kwh"]
    assert high_sun["total_import_kwh"] <= low_sun["total_import_kwh"] + 1e-6


def test_temperature_shifts_heat_and_cooling_in_expected_directions():
    cold = _simulate_ui({"ambient_temp_c": 0, "hp_daily": 10.0, "ac_daily": 10.0})
    hot = _simulate_ui({"ambient_temp_c": 30, "hp_daily": 10.0, "ac_daily": 10.0})

    assert float(cold["heat_pump"].sum()) > float(hot["heat_pump"].sum())
    assert float(hot["airco"].sum()) > float(cold["airco"].sum())


def test_household_slider_increases_total_demand_and_cost():
    low = _simulate_ui({"hh_base": 8.0})
    high = _simulate_ui({"hh_base": 22.0})

    assert high["total_demand_kwh"] > low["total_demand_kwh"]
    assert high["daily_cost_with_system"] > low["daily_cost_with_system"]


def test_solar_slider_reduces_grid_import():
    no_solar = _simulate_ui({"solar_kwp": 0.0})
    high_solar = _simulate_ui({"solar_kwp": 12.0})

    assert high_solar["total_solar_kwh"] > no_solar["total_solar_kwh"]
    assert high_solar["total_import_kwh"] <= no_solar["total_import_kwh"] + 1e-6


def test_battery_slider_reduces_evening_import_in_solar_case():
    base = {
        "sun_hours": 16,
        "solar_kwp": 10.0,
        "hh_base": 12.0,
        "ev_weekly": 0.0,
        "hp_daily": 6.0,
        "ac_daily": 0.0,
    }
    no_battery = _simulate_ui({**base, "bat_cap": 0.0})
    with_battery = _simulate_ui({**base, "bat_cap": 20.0})

    assert with_battery["total_import_kwh"] <= no_battery["total_import_kwh"] + 1e-6


def test_ev_slider_increases_ev_demand_and_cost():
    no_ev = _simulate_ui({"ev_weekly": 0.0})
    high_ev = _simulate_ui({"ev_weekly": 140.0})

    assert float(high_ev["ev"].sum()) > float(no_ev["ev"].sum())
    assert high_ev["daily_cost_with_system"] > no_ev["daily_cost_with_system"]


def test_heat_pump_slider_increases_heat_pump_demand():
    off = _simulate_ui({"hp_daily": 0.0})
    high = _simulate_ui({"hp_daily": 18.0})

    assert float(high["heat_pump"].sum()) > float(off["heat_pump"].sum())


def test_airco_slider_increases_airco_demand():
    off = _simulate_ui({"ac_daily": 0.0, "ambient_temp_c": 30})
    high = _simulate_ui({"ac_daily": 12.0, "ambient_temp_c": 30})

    assert float(high["airco"].sum()) > float(off["airco"].sum())


def test_import_price_changes_cost_not_energy_flows():
    cheap = _simulate_ui({"import_price": 0.15})
    expensive = _simulate_ui({"import_price": 0.45})

    assert math.isclose(
        cheap["total_import_kwh"],
        expensive["total_import_kwh"],
        rel_tol=0,
        abs_tol=1e-6,
    )
    assert expensive["daily_cost_with_system"] > cheap["daily_cost_with_system"]


def test_feedin_tariff_changes_revenue_not_flows():
    base = {"sun_hours": 16, "solar_kwp": 12.0}
    low_tariff = _simulate_ui({**base, "feedin_tariff": 0.0})
    high_tariff = _simulate_ui({**base, "feedin_tariff": 0.2})

    assert math.isclose(
        low_tariff["total_export_kwh"],
        high_tariff["total_export_kwh"],
        rel_tol=0,
        abs_tol=1e-6,
    )
    assert high_tariff["daily_export_revenue"] > low_tariff["daily_export_revenue"]
