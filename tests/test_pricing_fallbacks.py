import numpy as np
import pandas as pd

from models import ContractType, PricingInput
from pricing import expand_hourly_series, generate_dummy_dynamic_prices, resolve_import_prices


def test_expand_hourly_series_repeats_input_pattern():
    raw = np.array([1.0, 2.0, 3.0])
    out = expand_hourly_series(raw, 8)
    assert len(out) == 8
    assert np.allclose(out, np.array([1.0, 2.0, 3.0, 1.0, 2.0, 3.0, 1.0, 2.0]))


def test_resolve_import_prices_handles_fixed_tou_dynamic():
    idx = pd.date_range("2025-01-01", periods=48, freq="h")

    fixed = resolve_import_prices(
        PricingInput(contract_type=ContractType.FIXED, flat_import_price=0.31, feedin_price_flat=0.08),
        idx,
    )
    assert np.allclose(fixed, 0.31)

    tou = resolve_import_prices(
        PricingInput(contract_type=ContractType.TOU, flat_import_price=0.30, feedin_price_flat=0.08),
        idx,
    )
    assert len(tou) == 48
    assert tou.min() > 0

    dyn = resolve_import_prices(
        PricingInput(contract_type=ContractType.DYNAMIC, flat_import_price=0.30, feedin_price_flat=0.08),
        idx,
    )
    assert len(dyn) == 48
    assert dyn.min() >= 0.05


def test_generate_dummy_dynamic_prices_returns_8760_non_constant_values():
    s = generate_dummy_dynamic_prices(year=2025, seed=1)
    assert len(s) == 365 * 24
    assert float(s.std()) > 0.0
