import numpy as np
import pandas as pd

from models import ContractType, PricingInput
from simulation import TOU_PRICES


def generate_dummy_dynamic_prices(
    year: int = 2025,
    seed: int = 42,
    base_eur_per_kwh: float = 0.28,
) -> pd.Series:
    """Create a synthetic hourly import price curve for a full year."""
    index = pd.date_range(f"{year}-01-01", f"{year+1}-01-01", freq="h", inclusive="left")
    rng = np.random.default_rng(seed)

    hour = index.hour.to_numpy()
    day_of_year = index.dayofyear.to_numpy()
    day_of_week = index.dayofweek.to_numpy()

    morning_peak = np.exp(-0.5 * ((hour - 8) / 2.0) ** 2)
    evening_peak = np.exp(-0.5 * ((hour - 19) / 2.5) ** 2)
    daily_shape = 0.05 * morning_peak + 0.10 * evening_peak

    seasonal_shape = 0.06 * np.cos(2 * np.pi * (day_of_year - 15) / 365.0)
    weekend_discount = np.where(day_of_week >= 5, -0.015, 0.0)
    noise = rng.normal(0.0, 0.012, size=len(index))

    prices = base_eur_per_kwh + daily_shape + seasonal_shape + weekend_discount + noise
    prices = np.clip(prices, 0.05, 0.70)
    return pd.Series(prices, index=index, name="import_price_eur_per_kwh")


def expand_hourly_series(raw: np.ndarray, horizon_hours: int) -> np.ndarray:
    raw = np.asarray(raw, dtype=float)
    if raw.ndim != 1 or len(raw) == 0:
        raise ValueError("Price input must be a non-empty 1D array")
    reps = int(np.ceil(horizon_hours / len(raw)))
    return np.tile(raw, reps)[:horizon_hours]


def _resolve_dynamic_or_dummy(dynamic_series: pd.Series | None, horizon_index: pd.DatetimeIndex) -> np.ndarray:
    if dynamic_series is None:
        source = generate_dummy_dynamic_prices(year=int(horizon_index[0].year)).to_numpy()
    else:
        source = dynamic_series.to_numpy(dtype=float)
    return expand_hourly_series(source, len(horizon_index))


def resolve_import_prices(pricing: PricingInput, horizon_index: pd.DatetimeIndex) -> np.ndarray:
    contract = pricing.contract_type
    n_hours = len(horizon_index)

    if contract == ContractType.FIXED:
        return np.full(n_hours, float(pricing.flat_import_price), dtype=float)

    if contract == ContractType.TOU:
        source = TOU_PRICES if pricing.tou_import_24h is None else np.asarray(pricing.tou_import_24h, dtype=float)
        # Keep TOU average aligned with configured flat price for fair comparisons.
        if source.mean() > 0:
            source = source * (float(pricing.flat_import_price) / float(source.mean()))
        return expand_hourly_series(source, n_hours)

    if contract == ContractType.DYNAMIC:
        return _resolve_dynamic_or_dummy(pricing.dynamic_import_hourly, horizon_index)

    raise ValueError(f"Unsupported contract type: {contract}")


def resolve_feedin_prices(pricing: PricingInput, horizon_index: pd.DatetimeIndex) -> np.ndarray:
    n_hours = len(horizon_index)

    if pricing.dynamic_feedin_hourly is not None:
        return expand_hourly_series(pricing.dynamic_feedin_hourly.to_numpy(dtype=float), n_hours)

    return np.full(n_hours, float(pricing.feedin_price_flat), dtype=float)
