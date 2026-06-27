import numpy as np
import pandas as pd
from models import SystemConfig


# ── Solar generation profile ──────────────────────────────────────────────────
SOLAR_SHAPE = np.array([
    0.00, 0.00, 0.00, 0.00, 0.00, 0.02,
    0.06, 0.12, 0.20, 0.28, 0.35, 0.38,
    0.38, 0.35, 0.28, 0.20, 0.12, 0.06,
    0.02, 0.00, 0.00, 0.00, 0.00, 0.00,
])  # sums to ~2.92 → normalise to peak kWp output

# ── Household load shape (relative weights) ───────────────────────────────────
BASE_LOAD_SHAPE = np.array([
    0.5, 0.4, 0.4, 0.4, 0.5, 0.7,
    1.0, 1.1, 1.0, 0.8, 0.7, 0.7,
    0.8, 0.8, 0.7, 0.7, 0.8, 1.2,
    1.5, 1.8, 1.6, 1.3, 1.0, 0.7,
])

# ── Time-of-use electricity prices (€/kWh) ────────────────────────────────────
TOU_PRICES = np.array([
    0.18, 0.18, 0.18, 0.18, 0.18, 0.20,
    0.25, 0.28, 0.30, 0.28, 0.26, 0.24,
    0.24, 0.24, 0.24, 0.26, 0.28, 0.32,
    0.38, 0.40, 0.36, 0.30, 0.24, 0.20,
])  # peak evening pricing


def _solar_profile(cfg: SystemConfig) -> np.ndarray:
    """kWh per hour from solar array."""
    peak_per_hour = cfg.solar.kwp * cfg.solar.efficiency
    shape = SOLAR_SHAPE / SOLAR_SHAPE.max()  # normalise to 1 at peak
    return shape * peak_per_hour


def _household_profile(cfg: SystemConfig) -> np.ndarray:
    """kWh per hour for household base load."""
    daily_total = cfg.household.base_kwh_day
    # apply peak multiplier to evening hours 17-21
    shape = BASE_LOAD_SHAPE.copy().astype(float)
    shape[17:22] *= cfg.household.peak_multiplier
    shape = shape / shape.sum()  # normalise so it sums to 1
    return shape * daily_total


def _ev_profile(cfg: SystemConfig) -> np.ndarray:
    """kWh per hour for EV charging."""
    if not cfg.ev.enabled:
        return np.zeros(24)
    daily_kwh = cfg.ev.weekly_kwh / 7.0
    if cfg.ev.flexible:
        # charge during typical solar hours proportional to solar shape
        weights = SOLAR_SHAPE.copy()
        if weights.sum() == 0:
            weights[:] = 1 / 24
        else:
            weights /= weights.sum()
        return weights * daily_kwh
    else:
        # fixed evening charge 18-22
        profile = np.zeros(24)
        profile[18:22] = daily_kwh / 4.0
        return profile


def _heat_pump_profile(cfg: SystemConfig) -> np.ndarray:
    """kWh per hour for heat pump."""
    if not cfg.heat_pump.enabled:
        return np.zeros(24)
    daily = cfg.heat_pump.daily_kwh
    # morning + evening comfort runs
    shape = np.zeros(24)
    shape[6:9] = 1.2
    shape[17:21] = 1.5
    shape[9:17] = 0.4
    shape[21:24] = 0.2
    shape = shape / shape.sum()
    return shape * daily


def _import_prices(cfg: SystemConfig) -> np.ndarray:
    if cfg.economics.time_of_use:
        # scale TOU so average ≈ flat rate
        return TOU_PRICES * (cfg.economics.import_price / TOU_PRICES.mean())
    return np.full(24, cfg.economics.import_price)


def simulate(cfg: SystemConfig) -> dict:
    """
    Run 24-hour energy simulation.
    Returns dict with hourly arrays and financial/metric summaries.
    """
    solar = _solar_profile(cfg)
    household = _household_profile(cfg)
    ev = _ev_profile(cfg)
    heat_pump = _heat_pump_profile(cfg)
    total_demand = household + ev + heat_pump
    prices = _import_prices(cfg)

    # battery state
    soc = cfg.battery.capacity_kwh * (cfg.battery.initial_soc_pct / 100.0) if cfg.battery.enabled else 0.0
    max_cap = cfg.battery.capacity_kwh if cfg.battery.enabled else 0.0
    max_chg = cfg.battery.max_charge_kw if cfg.battery.enabled else 0.0
    max_dis = cfg.battery.max_discharge_kw if cfg.battery.enabled else 0.0

    # hourly output arrays
    battery_charge = np.zeros(24)
    battery_discharge = np.zeros(24)
    battery_soc = np.zeros(24)
    grid_import = np.zeros(24)
    grid_export = np.zeros(24)

    for h in range(24):
        surplus = solar[h] - total_demand[h]  # positive = excess solar

        if surplus >= 0:
            # solar covers demand — charge battery with surplus
            charge_possible = min(surplus, max_chg, max_cap - soc)
            soc += charge_possible
            battery_charge[h] = charge_possible
            remaining_surplus = surplus - charge_possible
            grid_export[h] = remaining_surplus  # export leftover
        else:
            deficit = -surplus  # how much we still need
            # discharge battery first
            discharge_possible = min(deficit, max_dis, soc)
            soc -= discharge_possible
            battery_discharge[h] = discharge_possible
            remaining_deficit = deficit - discharge_possible
            grid_import[h] = remaining_deficit

        battery_soc[h] = soc

    # ── Financial calculations ─────────────────────────────────────────────────
    daily_import_cost = float(np.sum(grid_import * prices))
    daily_export_revenue = float(np.sum(grid_export * cfg.economics.feedin_tariff))
    daily_cost_with_system = daily_import_cost - daily_export_revenue

    # baseline: no solar/battery, pure import
    baseline_cost = float(np.sum(total_demand * prices))

    daily_savings = baseline_cost - daily_cost_with_system
    savings_pct = (daily_savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

    # ── Energy metrics ─────────────────────────────────────────────────────────
    total_solar = float(solar.sum())
    total_demand_val = float(total_demand.sum())
    total_import = float(grid_import.sum())
    total_export = float(grid_export.sum())
    solar_consumed = total_solar - total_export  # solar used on-site

    self_consumption = (solar_consumed / total_solar * 100) if total_solar > 0 else 0.0
    solar_utilisation = (solar_consumed / total_demand_val * 100) if total_demand_val > 0 else 0.0
    grid_dependency = (total_import / total_demand_val * 100) if total_demand_val > 0 else 0.0

    # monthly extrapolation (×30)
    monthly_cost = daily_cost_with_system * 30
    monthly_baseline = baseline_cost * 30
    monthly_savings = daily_savings * 30

    hours = list(range(24))

    return {
        "hours": hours,
        "solar": solar,
        "household": household,
        "ev": ev,
        "heat_pump": heat_pump,
        "total_demand": total_demand,
        "battery_charge": battery_charge,
        "battery_discharge": battery_discharge,
        "battery_soc": battery_soc,
        "grid_import": grid_import,
        "grid_export": grid_export,
        "prices": prices,
        # financials
        "daily_cost_with_system": daily_cost_with_system,
        "daily_cost_baseline": baseline_cost,
        "daily_savings": daily_savings,
        "savings_pct": savings_pct,
        "daily_export_revenue": daily_export_revenue,
        "monthly_cost": monthly_cost,
        "monthly_baseline": monthly_baseline,
        "monthly_savings": monthly_savings,
        # metrics
        "total_solar_kwh": total_solar,
        "total_demand_kwh": total_demand_val,
        "total_import_kwh": total_import,
        "total_export_kwh": total_export,
        "self_consumption_pct": self_consumption,
        "solar_utilisation_pct": solar_utilisation,
        "grid_dependency_pct": grid_dependency,
    }
