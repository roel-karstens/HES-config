import numpy as np
import pandas as pd

from models import DispatchConfig, SimulationInputs, SimulationResult, SystemConfig


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


def _airco_profile(cfg: SystemConfig) -> np.ndarray:
    """kWh per hour for cooling load (AIRCO)."""
    if not cfg.airco.enabled:
        return np.zeros(24)
    daily = cfg.airco.daily_kwh * max(cfg.airco.intensity, 0.0)
    # Midday and early evening cooling demand.
    shape = np.zeros(24)
    shape[11:18] = 1.2
    shape[18:22] = 0.8
    shape[9:11] = 0.4
    shape = shape / shape.sum()
    return shape * daily


def _import_prices(cfg: SystemConfig) -> np.ndarray:
    if cfg.economics.time_of_use:
        # scale TOU so average ≈ flat rate
        return TOU_PRICES * (cfg.economics.import_price / TOU_PRICES.mean())
    return np.full(24, cfg.economics.import_price)


def heat_pump_cop(temp_c: np.ndarray, supply_temp_c: float = 35.0) -> np.ndarray:
    """Simple COP approximation for low-temperature heat pumps."""
    temp_c = np.asarray(temp_c, dtype=float)
    # A compact empirical curve: lower outdoor temperatures reduce COP.
    cop = 2.6 + 0.06 * temp_c - 0.002 * (supply_temp_c - 35.0)
    return np.clip(cop, 1.5, 5.0)


def heating_demand_multiplier(temp_c: np.ndarray, comfort_temp_c: float = 18.0) -> np.ndarray:
    temp_c = np.asarray(temp_c, dtype=float)
    return np.clip(1.0 + (comfort_temp_c - temp_c) * 0.03, 0.5, 2.2)


def battery_efficiency_by_temp(temp_c: np.ndarray) -> np.ndarray:
    temp_c = np.asarray(temp_c, dtype=float)
    eff = 0.94 - np.maximum(0.0, 10.0 - temp_c) * 0.003
    return np.clip(eff, 0.85, 0.96)


def compute_kpis(hourly_df: pd.DataFrame) -> dict:
    total_solar = float(hourly_df["solar"].sum())
    total_demand_val = float(hourly_df["total_demand"].sum())
    total_import = float(hourly_df["grid_import"].sum())
    total_export = float(hourly_df["grid_export"].sum())
    solar_consumed = total_solar - total_export

    self_consumption = (solar_consumed / total_solar * 100) if total_solar > 0 else 0.0
    solar_utilisation = (solar_consumed / total_demand_val * 100) if total_demand_val > 0 else 0.0
    grid_dependency = (total_import / total_demand_val * 100) if total_demand_val > 0 else 0.0

    return {
        "total_solar_kwh": total_solar,
        "total_demand_kwh": total_demand_val,
        "total_import_kwh": total_import,
        "total_export_kwh": total_export,
        "self_consumption_pct": self_consumption,
        "solar_utilisation_pct": solar_utilisation,
        "grid_dependency_pct": grid_dependency,
    }


def compute_economics(hourly_df: pd.DataFrame, capex: float = 0.0) -> dict:
    daily_import_cost = float((hourly_df["grid_import"] * hourly_df["import_price"]).sum())
    daily_export_revenue = float((hourly_df["grid_export"] * hourly_df["feedin_price"]).sum())
    daily_cost_with_system = daily_import_cost - daily_export_revenue

    baseline_cost = float((hourly_df["total_demand"] * hourly_df["import_price"]).sum())
    daily_savings = baseline_cost - daily_cost_with_system
    savings_pct = (daily_savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

    annual_savings = daily_savings * 365
    payback_years = float("inf") if annual_savings <= 0 else (capex / annual_savings)

    return {
        "daily_cost_with_system": daily_cost_with_system,
        "daily_cost_baseline": baseline_cost,
        "daily_savings": daily_savings,
        "savings_pct": savings_pct,
        "daily_export_revenue": daily_export_revenue,
        "monthly_cost": daily_cost_with_system * 30,
        "monthly_baseline": baseline_cost * 30,
        "monthly_savings": daily_savings * 30,
        "annual_savings": annual_savings,
        "payback_years": payback_years,
    }


def simulate_horizon(
    inputs: SimulationInputs,
    cfg: SystemConfig | None = None,
) -> SimulationResult:
    """Run a horizon simulation using explicit hourly profiles and prices."""
    if cfg is None:
        cfg = SystemConfig()

    dispatch = inputs.dispatch if inputs.dispatch is not None else DispatchConfig()

    solar = inputs.solar_profile.to_numpy(dtype=float)
    demand_profiles = inputs.demand_profiles.copy()
    if "total_demand" in demand_profiles.columns:
        total_demand = demand_profiles["total_demand"].to_numpy(dtype=float)
    else:
        total_demand = demand_profiles.sum(axis=1).to_numpy(dtype=float)

    import_prices = inputs.import_prices.to_numpy(dtype=float)
    feedin_prices = inputs.feedin_prices.to_numpy(dtype=float)
    outside_temp = inputs.outside_temp_c.to_numpy(dtype=float)
    batt_eff = battery_efficiency_by_temp(outside_temp)

    n = len(inputs.index)
    soc = cfg.battery.capacity_kwh * (cfg.battery.initial_soc_pct / 100.0) if cfg.battery.enabled else 0.0
    max_cap = cfg.battery.capacity_kwh if cfg.battery.enabled else 0.0
    max_chg = cfg.battery.max_charge_kw if cfg.battery.enabled else 0.0
    max_dis = cfg.battery.max_discharge_kw if cfg.battery.enabled else 0.0

    battery_charge = np.zeros(n)
    battery_discharge = np.zeros(n)
    battery_soc = np.zeros(n)
    grid_import = np.zeros(n)
    grid_export = np.zeros(n)

    # A basic price-aware dispatch mode that allows limited pre-charge from grid.
    low_price_threshold = float(np.quantile(import_prices, 0.25)) if len(import_prices) > 0 else 0.0

    for h in range(n):
        if dispatch.strategy == "price_optimized" and cfg.battery.enabled and import_prices[h] <= low_price_threshold:
            target = 0.30 * max_cap
            if soc < target and max_chg > 0:
                grid_charge = min(max_chg, target - soc)
                soc += grid_charge * batt_eff[h]
                battery_charge[h] += grid_charge
                grid_import[h] += grid_charge

        surplus = solar[h] - total_demand[h]

        if surplus >= 0:
            charge_possible = min(surplus, max_chg, max_cap - soc)
            effective_charge = charge_possible * batt_eff[h]
            soc += effective_charge
            battery_charge[h] += charge_possible
            grid_export[h] = surplus - charge_possible
        else:
            deficit = -surplus
            discharge_possible = min(deficit, max_dis, soc)
            soc -= discharge_possible
            effective_discharge = discharge_possible * batt_eff[h]
            battery_discharge[h] = effective_discharge
            grid_import[h] += max(deficit - effective_discharge, 0.0)

        battery_soc[h] = soc

    hourly = pd.DataFrame(
        {
            "solar": solar,
            "total_demand": total_demand,
            "battery_charge": battery_charge,
            "battery_discharge": battery_discharge,
            "battery_soc": battery_soc,
            "grid_import": grid_import,
            "grid_export": grid_export,
            "import_price": import_prices,
            "feedin_price": feedin_prices,
        },
        index=inputs.index,
    )

    for col in ["household", "ev", "heat_pump", "airco", "dhw"]:
        if col in demand_profiles.columns:
            hourly[col] = demand_profiles[col].to_numpy(dtype=float)

    kpis = compute_kpis(hourly)
    economics = compute_economics(hourly)
    return SimulationResult(hourly=hourly, kpis=kpis, economics=economics)


def simulate(cfg: SystemConfig) -> dict:
    """
    Run 24-hour energy simulation.
    Returns dict with hourly arrays and financial/metric summaries.
    """
    solar = _solar_profile(cfg)
    household = _household_profile(cfg)
    ev = _ev_profile(cfg)
    heat_pump = _heat_pump_profile(cfg)
    airco = _airco_profile(cfg)
    total_demand = household + ev + heat_pump + airco
    prices = _import_prices(cfg)

    index = pd.date_range("2025-01-01", periods=24, freq="h")
    demand_profiles = pd.DataFrame(
        {
            "household": household,
            "ev": ev,
            "heat_pump": heat_pump,
            "airco": airco,
            "total_demand": total_demand,
        },
        index=index,
    )

    sim_inputs = SimulationInputs(
        index=index,
        demand_profiles=demand_profiles,
        solar_profile=pd.Series(solar, index=index),
        import_prices=pd.Series(prices, index=index),
        feedin_prices=pd.Series(np.full(24, cfg.economics.feedin_tariff), index=index),
        outside_temp_c=pd.Series(np.full(24, 12.0), index=index),
        dispatch=DispatchConfig(strategy="pv_optimized"),
    )
    sim_res = simulate_horizon(sim_inputs, cfg=cfg)
    hourly = sim_res.hourly
    economics = sim_res.economics
    kpis = sim_res.kpis

    hours = list(range(24))

    return {
        "hours": hours,
        "solar": solar,
        "household": household,
        "ev": ev,
        "heat_pump": heat_pump,
        "airco": airco,
        "total_demand": total_demand,
        "battery_charge": hourly["battery_charge"].to_numpy(),
        "battery_discharge": hourly["battery_discharge"].to_numpy(),
        "battery_soc": hourly["battery_soc"].to_numpy(),
        "grid_import": hourly["grid_import"].to_numpy(),
        "grid_export": hourly["grid_export"].to_numpy(),
        "prices": prices,
        # financials
        "daily_cost_with_system": economics["daily_cost_with_system"],
        "daily_cost_baseline": economics["daily_cost_baseline"],
        "daily_savings": economics["daily_savings"],
        "savings_pct": economics["savings_pct"],
        "daily_export_revenue": economics["daily_export_revenue"],
        "monthly_cost": economics["monthly_cost"],
        "monthly_baseline": economics["monthly_baseline"],
        "monthly_savings": economics["monthly_savings"],
        # metrics
        "total_solar_kwh": kpis["total_solar_kwh"],
        "total_demand_kwh": kpis["total_demand_kwh"],
        "total_import_kwh": kpis["total_import_kwh"],
        "total_export_kwh": kpis["total_export_kwh"],
        "self_consumption_pct": kpis["self_consumption_pct"],
        "solar_utilisation_pct": kpis["solar_utilisation_pct"],
        "grid_dependency_pct": kpis["grid_dependency_pct"],
    }
