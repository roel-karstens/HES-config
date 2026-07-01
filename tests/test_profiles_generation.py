import numpy as np
import pandas as pd

from models import EVBehaviorInputs, OccupancyInputs, ProfileInputs, ThermalInputs
from profiles import build_all_profiles


def _make_inputs() -> ProfileInputs:
    return ProfileInputs(
        household_kwh_day=15.0,
        occupancy=OccupancyInputs(wfh_days_per_week=2, weekend_behavior_factor=1.08),
        ev=EVBehaviorInputs(arrival_hour=18, departure_hour=7, target_kwh_by_departure=8.0, smart_charging=False),
        thermal=ThermalInputs(heat_pump_kwh_day_nominal=8.0, dhw_kwh_day_nominal=2.0, indoor_setpoint_c=20.0),
    )


def test_profile_totals_match_expected_order_of_magnitude():
    idx = pd.date_range("2025-01-06", periods=24 * 7, freq="h")
    temp = pd.Series(np.full(len(idx), 10.0), index=idx)
    irrad = pd.Series(np.full(len(idx), 1.0), index=idx)
    prices = pd.Series(np.full(len(idx), 0.30), index=idx)

    profiles = build_all_profiles(idx, _make_inputs(), temp, irrad, pv_kwp=8.0, prices=prices)

    assert set(["household", "ev", "heat_pump", "dhw", "solar", "total_demand"]).issubset(profiles.columns)
    assert float(profiles["household"].sum()) > 0
    assert float(profiles["solar"].sum()) > 0

    daily_demand = profiles["total_demand"].sum() / 7.0
    assert 20.0 <= float(daily_demand) <= 40.0
