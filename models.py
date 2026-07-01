from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import numpy as np
import pandas as pd


@dataclass
class SolarConfig:
    kwp: float = 5.0
    efficiency: float = 0.85


@dataclass
class BatteryConfig:
    capacity_kwh: float = 10.0
    max_charge_kw: float = 3.0
    max_discharge_kw: float = 3.0
    initial_soc_pct: float = 20.0
    enabled: bool = True


@dataclass
class EVConfig:
    enabled: bool = False
    weekly_kwh: float = 70.0
    flexible: bool = True  # True = charge during solar surplus; False = fixed evening


@dataclass
class HeatPumpConfig:
    enabled: bool = False
    daily_kwh: float = 8.0


@dataclass
class AircoConfig:
    enabled: bool = False
    daily_kwh: float = 4.0
    intensity: float = 1.0


@dataclass
class HouseholdConfig:
    base_kwh_day: float = 10.0
    peak_multiplier: float = 2.0  # evening factor


@dataclass
class EconomicsConfig:
    import_price: float = 0.28  # €/kWh
    feedin_tariff: float = 0.08  # €/kWh
    time_of_use: bool = False


class ContractType(str, Enum):
    FIXED = "fixed"
    TOU = "tou"
    DYNAMIC = "dynamic"


@dataclass
class PricingInput:
    contract_type: ContractType = ContractType.FIXED
    flat_import_price: float = 0.28
    feedin_price_flat: float = 0.08
    tou_import_24h: np.ndarray | None = None
    dynamic_import_hourly: pd.Series | None = None
    dynamic_feedin_hourly: pd.Series | None = None


@dataclass
class OccupancyInputs:
    wfh_days_per_week: int = 2
    weekend_behavior_factor: float = 1.08


@dataclass
class EVBehaviorInputs:
    arrival_hour: int = 18
    departure_hour: int = 7
    target_kwh_by_departure: float = 8.5
    smart_charging: bool = True


@dataclass
class ThermalInputs:
    heat_pump_kwh_day_nominal: float = 8.0
    dhw_kwh_day_nominal: float = 2.0
    indoor_setpoint_c: float = 20.0


@dataclass
class ProfileInputs:
    household_kwh_day: float = 15.0
    occupancy: OccupancyInputs = field(default_factory=OccupancyInputs)
    ev: EVBehaviorInputs = field(default_factory=EVBehaviorInputs)
    thermal: ThermalInputs = field(default_factory=ThermalInputs)


@dataclass
class DispatchConfig:
    strategy: str = "immediate"  # immediate | pv_optimized | price_optimized
    peak_shaving_kw: float | None = None


@dataclass
class SimulationInputs:
    index: pd.DatetimeIndex
    demand_profiles: pd.DataFrame
    solar_profile: pd.Series
    import_prices: pd.Series
    feedin_prices: pd.Series
    outside_temp_c: pd.Series
    dispatch: DispatchConfig = field(default_factory=DispatchConfig)


@dataclass
class SimulationResult:
    hourly: pd.DataFrame
    kpis: dict
    economics: dict


Objective = Literal[
    "lowest_bill",
    "highest_roi",
    "fastest_payback",
    "sustainability",
    "grid_independence",
]


@dataclass
class UserGoals:
    objective: Objective = "highest_roi"
    budget_eur: float | None = None
    sustainability_weight: float = 0.0
    independence_weight: float = 0.0


@dataclass
class CandidateConfig:
    solar_kwp: float
    battery_kwh: float
    heat_pump_enabled: bool
    ev_enabled: bool
    v2g_enabled: bool
    charging_strategy: str


@dataclass
class CandidateEvaluation:
    candidate: CandidateConfig
    annual_savings_eur: float
    capex_eur: float
    payback_years: float
    score: float
    constraints_ok: bool
    evidence: dict


@dataclass
class Recommendation:
    title: str
    action: str
    why: list[str]
    expected_savings_eur_year: float
    investment_eur: float
    payback_years: float
    confidence: str  # low | medium | high
    evidence: dict


@dataclass
class SystemConfig:
    solar: SolarConfig = field(default_factory=SolarConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)
    ev: EVConfig = field(default_factory=EVConfig)
    heat_pump: HeatPumpConfig = field(default_factory=HeatPumpConfig)
    airco: AircoConfig = field(default_factory=AircoConfig)
    household: HouseholdConfig = field(default_factory=HouseholdConfig)
    economics: EconomicsConfig = field(default_factory=EconomicsConfig)
