import numpy as np
import pandas as pd

from models import ProfileInputs


SOLAR_SHAPE = np.array([
    0.00, 0.00, 0.00, 0.00, 0.00, 0.02,
    0.06, 0.12, 0.20, 0.28, 0.35, 0.38,
    0.38, 0.35, 0.28, 0.20, 0.12, 0.06,
    0.02, 0.00, 0.00, 0.00, 0.00, 0.00,
])


def _normalize_shape(shape: np.ndarray) -> np.ndarray:
    shape = np.asarray(shape, dtype=float)
    total = shape.sum()
    if total <= 0:
        return np.full_like(shape, 1.0 / len(shape), dtype=float)
    return shape / total


def build_household_profile(index: pd.DatetimeIndex, inputs: ProfileInputs) -> pd.Series:
    base_shape = _normalize_shape(np.array([
        0.6, 0.5, 0.45, 0.45, 0.5, 0.7,
        1.0, 1.1, 0.95, 0.8, 0.75, 0.75,
        0.8, 0.85, 0.8, 0.85, 1.0, 1.3,
        1.6, 1.8, 1.7, 1.4, 1.1, 0.8,
    ]))

    out = np.zeros(len(index), dtype=float)
    wfh_days = set(range(0, min(max(inputs.occupancy.wfh_days_per_week, 0), 5)))

    for day in range(7):
        mask = index.dayofweek == day
        is_weekend = day >= 5
        uplift = 1.10 if day in wfh_days else 1.0
        weekend_factor = inputs.occupancy.weekend_behavior_factor if is_weekend else 1.0
        out[mask] = inputs.household_kwh_day * uplift * weekend_factor * base_shape

    return pd.Series(out, index=index, name="household")


def build_ev_profile(index: pd.DatetimeIndex, inputs: ProfileInputs, prices: pd.Series | None = None) -> pd.Series:
    ev = inputs.ev
    availability = np.zeros(len(index), dtype=float)

    for i, ts in enumerate(index):
        h = ts.hour
        at_home = (h >= ev.arrival_hour) or (h < ev.departure_hour)
        if at_home:
            availability[i] = 1.0

    if not ev.smart_charging or prices is None:
        day_weights = _normalize_shape(availability[:24])
        out = np.tile(day_weights * ev.target_kwh_by_departure, len(index) // 24)
    else:
        out = np.zeros(len(index), dtype=float)
        pvals = prices.to_numpy(dtype=float)
        for d in range(len(index) // 24):
            lo = d * 24
            hi = lo + 24
            day_avail = availability[lo:hi]
            eligible_hours = np.where(day_avail > 0)[0]
            if len(eligible_hours) == 0:
                continue
            inv_prices = 1.0 / np.maximum(pvals[lo:hi][eligible_hours], 1e-4)
            weights = inv_prices / inv_prices.sum()
            out[lo:hi][eligible_hours] = weights * ev.target_kwh_by_departure

    return pd.Series(out, index=index, name="ev")


def build_heat_pump_profile(index: pd.DatetimeIndex, inputs: ProfileInputs, outside_temp_c: pd.Series) -> pd.Series:
    shape = np.zeros(24)
    shape[6:9] = 1.2
    shape[9:17] = 0.4
    shape[17:21] = 1.5
    shape[21:24] = 0.2
    shape = _normalize_shape(shape)

    temp = outside_temp_c.to_numpy(dtype=float)
    temp_mult = np.clip(1.0 + (18.0 - temp) * 0.03, 0.5, 2.2)

    out = np.zeros(len(index), dtype=float)
    daily_nominal = float(inputs.thermal.heat_pump_kwh_day_nominal)
    for d in range(len(index) // 24):
        lo = d * 24
        hi = lo + 24
        day_mult = float(np.mean(temp_mult[lo:hi]))
        out[lo:hi] = daily_nominal * day_mult * shape

    return pd.Series(out, index=index, name="heat_pump")


def build_dhw_profile(index: pd.DatetimeIndex, inputs: ProfileInputs) -> pd.Series:
    shape = np.zeros(24)
    shape[6:9] = 1.4
    shape[18:22] = 1.6
    shape = _normalize_shape(shape)
    day = inputs.thermal.dhw_kwh_day_nominal * shape
    out = np.tile(day, len(index) // 24)
    return pd.Series(out, index=index, name="dhw")


def build_solar_profile(
    index: pd.DatetimeIndex,
    pv_kwp: float,
    irradiance_norm: pd.Series,
    outside_temp_c: pd.Series,
) -> pd.Series:
    base = _normalize_shape(SOLAR_SHAPE)
    out = np.zeros(len(index), dtype=float)
    temp = outside_temp_c.to_numpy(dtype=float)
    temp_derate = np.clip(1.0 - np.maximum(temp - 25.0, 0.0) * 0.004, 0.85, 1.05)

    irrad = irradiance_norm.to_numpy(dtype=float)
    for d in range(len(index) // 24):
        lo = d * 24
        hi = lo + 24
        day_scale = max(float(np.mean(irrad[lo:hi])), 0.05)
        out[lo:hi] = pv_kwp * day_scale * base * temp_derate[lo:hi]

    return pd.Series(out, index=index, name="solar")


def build_all_profiles(
    index: pd.DatetimeIndex,
    inputs: ProfileInputs,
    outside_temp_c: pd.Series,
    irradiance_norm: pd.Series,
    pv_kwp: float,
    prices: pd.Series | None = None,
) -> pd.DataFrame:
    household = build_household_profile(index, inputs)
    ev = build_ev_profile(index, inputs, prices=prices)
    heat_pump = build_heat_pump_profile(index, inputs, outside_temp_c)
    dhw = build_dhw_profile(index, inputs)
    solar = build_solar_profile(index, pv_kwp, irradiance_norm, outside_temp_c)

    df = pd.DataFrame(
        {
            "household": household,
            "ev": ev,
            "heat_pump": heat_pump,
            "dhw": dhw,
            "solar": solar,
        },
        index=index,
    )
    df["total_demand"] = df[["household", "ev", "heat_pump", "dhw"]].sum(axis=1)
    return df
