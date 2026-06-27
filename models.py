from dataclasses import dataclass, field


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


@dataclass
class SystemConfig:
    solar: SolarConfig = field(default_factory=SolarConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)
    ev: EVConfig = field(default_factory=EVConfig)
    heat_pump: HeatPumpConfig = field(default_factory=HeatPumpConfig)
    airco: AircoConfig = field(default_factory=AircoConfig)
    household: HouseholdConfig = field(default_factory=HouseholdConfig)
    economics: EconomicsConfig = field(default_factory=EconomicsConfig)
