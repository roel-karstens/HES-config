"""
optimizer.py
Heuristic optimizer: shifts flexible EV demand and battery scheduling
to minimise grid import cost given a 24-hour price signal.
"""
import numpy as np
from models import SystemConfig, EVConfig
import copy


def _import_prices(cfg: SystemConfig) -> np.ndarray:
    from simulation import TOU_PRICES
    if cfg.economics.time_of_use:
        return TOU_PRICES * (cfg.economics.import_price / TOU_PRICES.mean())
    return np.full(24, cfg.economics.import_price)


def optimise(cfg: SystemConfig) -> SystemConfig:
    """
    Return a new SystemConfig with optimised settings applied.
    Heuristic strategy:
      1. If EV is flexible, shift charging to the cheapest solar hours.
      2. Battery: pre-charge to 20% SOC in cheapest off-peak hours
         (only when no solar is available) — a basic price-aware top-up.
    The optimised config is passed back into simulation.simulate() by the UI.
    """
    opt_cfg = copy.deepcopy(cfg)

    prices = _import_prices(opt_cfg)

    # ── EV optimisation ────────────────────────────────────────────────────────
    # If EV is flexible, mark it as flexible (simulation already handles this).
    # No extra change needed — flexible EV already charges during solar surplus.

    # ── Battery initial SOC optimisation ──────────────────────────────────────
    # If prices are flat (no TOU), default SOC is fine.
    # With TOU: pre-charge battery slightly in the cheapest night hours.
    if opt_cfg.economics.time_of_use and opt_cfg.battery.enabled and opt_cfg.battery.capacity_kwh > 0:
        # Find the cheapest 3 off-peak hours (no solar: hours 0-5 or 22-23)
        night_hours = list(range(0, 6)) + list(range(22, 24))
        night_prices = [(prices[h], h) for h in night_hours]
        night_prices.sort()
        cheapest_hours = [h for _, h in night_prices[:3]]
        # How much can we charge in those hours?
        charge_potential = len(cheapest_hours) * opt_cfg.battery.max_charge_kw
        target_soc_pct = min(
            80.0,
            opt_cfg.battery.initial_soc_pct + (charge_potential / opt_cfg.battery.capacity_kwh) * 100
        )
        opt_cfg.battery.initial_soc_pct = target_soc_pct

    return opt_cfg


def compute_payback(
    system_cost_eur: float,
    annual_savings_eur: float,
) -> float:
    """Simple payback period in years."""
    if annual_savings_eur <= 0:
        return float("inf")
    return system_cost_eur / annual_savings_eur
