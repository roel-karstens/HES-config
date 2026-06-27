"""
app.py – Home Energy System Configurator & Optimizer
Run with: streamlit run app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models import (
    SystemConfig, SolarConfig, BatteryConfig, EVConfig,
    HeatPumpConfig, AircoConfig, HouseholdConfig, EconomicsConfig,
)
from simulation import simulate
from optimizer import optimise, compute_payback

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Energy Configurator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens ─────────────────────────────────────────────────────────────
DARK_BG      = "#0D1117"
PANEL_BG     = "#161B22"
BORDER       = "#21262D"
ACCENT       = "#00E5A0"    # electric mint-green
ACCENT2      = "#7C3AED"    # violet
SOLAR_COL    = "#FFD60A"
LOAD_COL     = "#FF6B6B"
BATTERY_COL  = "#00E5A0"
GRID_IMP_COL = "#EF4444"
GRID_EXP_COL = "#34D399"
EV_COL       = "#818CF8"
HP_COL       = "#FB923C"
AC_COL       = "#22D3EE"
TEXT_MUTED   = "#8B949E"
TEXT_MAIN    = "#E6EDF3"

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  html, body, [class*="css"] {{
            font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
      background-color: {DARK_BG};
      color: {TEXT_MAIN};
  }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{
      background-color: {PANEL_BG};
      border-right: 1px solid {BORDER};
  }}
  section[data-testid="stSidebar"] .stMarkdown h3 {{
      color: {ACCENT};
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-top: 1.4rem;
      margin-bottom: 0.2rem;
  }}

  /* Metric cards */
  .metric-card {{
      background: {PANEL_BG};
      border: 1px solid {BORDER};
      border-radius: 10px;
      padding: 1.1rem 1.2rem 0.9rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
  }}
  .metric-label {{
      font-size: 0.68rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: {TEXT_MUTED};
  }}
  .metric-value {{
      font-family: 'Consolas', 'Courier New', monospace;
      font-size: 1.75rem;
      font-weight: 500;
      color: {TEXT_MAIN};
      line-height: 1.1;
  }}
  .metric-sub {{
      font-size: 0.72rem;
      color: {TEXT_MUTED};
      margin-top: 0.1rem;
  }}
  .metric-value.good  {{ color: {ACCENT}; }}
  .metric-value.warn  {{ color: {SOLAR_COL}; }}
  .metric-value.bad   {{ color: {LOAD_COL}; }}

  /* Section headers */
  .section-header {{
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: {TEXT_MUTED};
      border-bottom: 1px solid {BORDER};
      padding-bottom: 0.4rem;
      margin-bottom: 1rem;
      margin-top: 0.5rem;
  }}

  /* Chart containers */
  .chart-panel {{
      background: {PANEL_BG};
      border: 1px solid {BORDER};
      border-radius: 10px;
      padding: 0.6rem;
  }}

  /* Optimiser badge */
  .opt-badge {{
      display: inline-block;
      background: {ACCENT2}22;
      border: 1px solid {ACCENT2}55;
      color: {ACCENT2};
      font-size: 0.65rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 0.18rem 0.55rem;
      border-radius: 99px;
  }}

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: {DARK_BG}; }}
  ::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}

  /* Streamlit overrides */
  .stSlider [data-baseweb="slider"] {{ margin-top: -0.3rem; }}
  div[data-testid="stMetric"] {{ display: none; }}
  .stTabs [data-baseweb="tab-list"] {{ background: {PANEL_BG}; border-radius: 8px; padding: 3px; gap: 2px; }}
  .stTabs [data-baseweb="tab"] {{ background: transparent; color: {TEXT_MUTED}; border-radius: 6px; font-size: 0.8rem; font-weight: 500; }}
  .stTabs [aria-selected="true"] {{ background: {ACCENT}18; color: {ACCENT}; }}
  hr {{ border-color: {BORDER}; }}
  .stCheckbox label {{ color: {TEXT_MUTED}; font-size: 0.82rem; }}
  .stSelectbox label, .stSlider label {{ color: {TEXT_MUTED}; font-size: 0.78rem; font-weight: 500; }}
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Segoe UI", color=TEXT_MUTED, size=11),
    margin=dict(l=0, r=10, t=36, b=60),
    legend=dict(
        orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0,
        bgcolor="rgba(0,0,0,0)", font=dict(size=10),
    ),
    xaxis=dict(
        showgrid=True, gridcolor=BORDER, gridwidth=1,
        zeroline=False, tickfont=dict(size=10),
    ),
    yaxis=dict(
        showgrid=True, gridcolor=BORDER, gridwidth=1,
        zeroline=False, tickfont=dict(size=10),
    ),
    hovermode="x unified",
)

HOUR_LABELS = [f"{h:02d}:00" for h in range(24)]

SOLAR_PRICE_PER_KWP = 1250
BATTERY_PRICE_PER_KWH = 550
EV_CHARGER_PRICE_PER_KW = 120
HEAT_PUMP_PRICE_PER_KW = 900
AIRCO_PRICE_PER_KW = 420

GAS_BASELINE_M3_YEAR = 1200  # typical NL household gas for heating+hot water

DEFAULT_STATE = {
    "sun_hours": 8,
    "ambient_temp_c": 20,
    "solar_kwp": 4.0,
    "bat_cap": 10.0,
    "ev_daily": 8.5,
    "hp_daily": 8.0,
    "ac_daily": 4.0,
    "hh_base": 15.0,
    "import_price": 0.30,
    "feedin_tariff": 0.09,
    "gas_price": 1.25,
    "feedin_fixed_cost": 150,
    "grid_fixed_elec": 534,
    "grid_fixed_gas": 404,
    "price_solar": SOLAR_PRICE_PER_KWP,
    "price_battery": BATTERY_PRICE_PER_KWH,
    "price_ev": int(11.0 * EV_CHARGER_PRICE_PER_KW),
    "price_hp": HEAT_PUMP_PRICE_PER_KW,
    "price_ac": AIRCO_PRICE_PER_KW,
}


def _init_sidebar_state() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def metric_card(label: str, value: str, sub: str = "", cls: str = "") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {cls}">{value}</div>
        {'<div class="metric-sub">' + sub + '</div>' if sub else ''}
    </div>"""


def section_header(title: str) -> None:
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def fmt_eur(v: float) -> str:
    return f"€{v:,.2f}"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def fmt_kwh(v: float) -> str:
    return f"{v:.2f} kWh"


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


@st.cache_data(show_spinner=False)
def compute_design_space(
    solar_eff: float,
    household_base: float,
    hh_peak_mult: float,
    ev_enabled: bool,
    ev_weekly_kwh: float,
    ev_flexible: bool,
    hp_enabled: bool,
    hp_daily_kwh: float,
    ac_enabled: bool,
    ac_daily_kwh: float,
    ac_intensity_val: float,
    import_price_val: float,
    feedin_tariff_val: float,
    use_optimizer: bool,
    p_solar: float = SOLAR_PRICE_PER_KWP,
    p_battery: float = BATTERY_PRICE_PER_KWH,
    p_ev: float = 0.0,
    p_hp: float = HEAT_PUMP_PRICE_PER_KW,
    p_ac: float = AIRCO_PRICE_PER_KW,
    gas_savings_yr: float = 0.0,
    fixed_savings_yr: float = 0.0,
) -> dict:
    solar_sizes = np.arange(0.0, 20.0 + 1e-9, 1.0)
    battery_sizes = np.arange(0.0, 30.0 + 1e-9, 1.0)

    fixed_capex = 0.0
    if ev_enabled:
        fixed_capex += p_ev
    if hp_enabled:
        fixed_capex += (hp_daily_kwh / 1.5) * p_hp
    if ac_enabled:
        fixed_capex += (ac_daily_kwh / 1.5) * p_ac

    annual_savings_grid = np.zeros((len(battery_sizes), len(solar_sizes)))
    payback_grid = np.full((len(battery_sizes), len(solar_sizes)), np.nan)
    optimization_grid = np.zeros((len(battery_sizes), len(solar_sizes)))

    points = []

    for bi, battery_kwh in enumerate(battery_sizes):
        for si, solar_kwp_val in enumerate(solar_sizes):
            bat_enabled_val = battery_kwh > 0
            bat_pwr_val = float(np.clip(battery_kwh / 3.0, 0.5, 10.0)) if bat_enabled_val else 0.0

            cfg_space = SystemConfig(
                solar=SolarConfig(kwp=float(solar_kwp_val), efficiency=solar_eff),
                battery=BatteryConfig(
                    capacity_kwh=float(battery_kwh),
                    max_charge_kw=bat_pwr_val,
                    max_discharge_kw=bat_pwr_val,
                    initial_soc_pct=20,
                    enabled=bat_enabled_val,
                ),
                ev=EVConfig(enabled=ev_enabled, weekly_kwh=ev_weekly_kwh, flexible=ev_flexible),
                heat_pump=HeatPumpConfig(enabled=hp_enabled, daily_kwh=hp_daily_kwh),
                airco=AircoConfig(enabled=ac_enabled, daily_kwh=ac_daily_kwh, intensity=ac_intensity_val),
                household=HouseholdConfig(base_kwh_day=household_base, peak_multiplier=hh_peak_mult),
                economics=EconomicsConfig(
                    import_price=import_price_val,
                    feedin_tariff=feedin_tariff_val,
                    time_of_use=False,
                ),
            )

            if use_optimizer:
                cfg_space = optimise(cfg_space)

            res = simulate(cfg_space)
            elec_savings = float(res["daily_savings"] * 365)
            annual_savings = elec_savings + gas_savings_yr + fixed_savings_yr
            capex = float(fixed_capex + solar_kwp_val * p_solar + battery_kwh * p_battery)
            payback = compute_payback(capex, annual_savings)
            optimization_score = annual_savings - capex

            annual_savings_grid[bi, si] = annual_savings
            payback_grid[bi, si] = payback if np.isfinite(payback) else np.nan
            optimization_grid[bi, si] = optimization_score
            points.append(
                {
                    "solar": float(solar_kwp_val),
                    "battery": float(battery_kwh),
                    "capex": capex,
                    "annual_savings": annual_savings,
                    "payback": payback,
                    "score": optimization_score,
                }
            )

    return {
        "solar_sizes": solar_sizes,
        "battery_sizes": battery_sizes,
        "annual_savings_grid": annual_savings_grid,
        "payback_grid": payback_grid,
        "optimization_grid": optimization_grid,
        "points": points,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — controls
# ─────────────────────────────────────────────────────────────────────────────

_init_sidebar_state()

with st.sidebar:
    st.markdown("""
    <div style="padding: 0.8rem 0 1.2rem;">
        <div style="font-size:1.25rem; font-weight:700; color:#E6EDF3; letter-spacing:-0.01em;">
            ⚡ Energy Configurator
        </div>
        <div style="font-size:0.72rem; color:#8B949E; margin-top:0.25rem;">
            Home system optimizer
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📅 Day Scenario")
    st.slider("Sun hours", min_value=0, max_value=16, step=1, key="sun_hours")
    st.slider("Temperature (C)", min_value=-10, max_value=35, step=1, key="ambient_temp_c")

    st.markdown("### ⚙️ System Sizing")
    st.slider("Household load (kWh/day)", min_value=0.0, max_value=40.0, step=0.5, key="hh_base")
    st.slider("Solar size (kWp)", min_value=0.0, max_value=20.0, step=0.5, key="solar_kwp")
    st.slider("Battery size (kWh)", min_value=0.0, max_value=30.0, step=0.5, key="bat_cap")
    st.slider("EV energy (kWh/day)", min_value=0.0, max_value=30.0, step=0.5, key="ev_daily")
    st.slider("Heat pump demand (kWh/day)", min_value=0.0, max_value=30.0, step=0.5, key="hp_daily")
    st.slider("AIRCO demand (kWh/day)", min_value=0.0, max_value=20.0, step=0.5, key="ac_daily")

    st.markdown("### 🏷️ System Prices")
    st.slider("Solar (€/kWp)", min_value=0, max_value=3000, step=50, key="price_solar")
    st.slider("Battery (€/kWh)", min_value=0, max_value=1500, step=50, key="price_battery")
    st.slider("EV charger (€ total)", min_value=0, max_value=5000, step=100, key="price_ev")
    st.slider("Heat pump (€/kW)", min_value=0, max_value=2000, step=50, key="price_hp")
    st.slider("AIRCO (€/kW)", min_value=0, max_value=1000, step=50, key="price_ac")

    # ── Economics ─────────────────────────────────────────────────────────
    st.markdown("### 💰 Energy Economics")
    st.slider("Stroom import (€/kWh)", min_value=0.10, max_value=0.60, step=0.01, key="import_price")
    st.slider("Gas import (€/m³)", min_value=0.50, max_value=3.00, step=0.05, key="gas_price")
    st.slider("Exportvergoeding (€/kWh)", min_value=0.00, max_value=0.30, step=0.01, key="feedin_tariff")
    st.slider("Terugleverkosten (€/jaar)", min_value=0, max_value=500, step=10, key="feedin_fixed_cost")
    st.slider("Vastrecht elektra (€/jaar)", min_value=0, max_value=1000, step=10, key="grid_fixed_elec")
    st.slider("Vastrecht gas (€/jaar)", min_value=0, max_value=800, step=10, key="grid_fixed_gas")

solar_kwp = st.session_state["solar_kwp"]
bat_cap = st.session_state["bat_cap"]
ev_daily = st.session_state["ev_daily"]
ev_weekly = ev_daily * 7.0
hp_daily = st.session_state["hp_daily"]
ac_daily = st.session_state["ac_daily"]
hh_base = st.session_state["hh_base"]
import_price = st.session_state["import_price"]
feedin_tariff = st.session_state["feedin_tariff"]
gas_price = st.session_state["gas_price"]
feedin_fixed_cost = st.session_state["feedin_fixed_cost"]
grid_fixed_elec = st.session_state["grid_fixed_elec"]
grid_fixed_gas = st.session_state["grid_fixed_gas"]
run_optimizer = False
sun_hours = st.session_state["sun_hours"]
ambient_temp_c = st.session_state["ambient_temp_c"]

price_solar = st.session_state["price_solar"]
price_battery = st.session_state["price_battery"]
price_ev = st.session_state["price_ev"]
price_hp = st.session_state["price_hp"]
price_ac = st.session_state["price_ac"]

solar_capex = solar_kwp * price_solar
battery_capex = bat_cap * price_battery
ev_capex = float(price_ev) if ev_weekly > 0 else 0.0
hp_capex = (hp_daily / 1.5) * price_hp
ac_capex = (ac_daily / 1.5) * price_ac
system_cost = float(solar_capex + battery_capex + ev_capex + hp_capex + ac_capex)

# ── Gas & fixed-cost economics ────────────────────────────────────────────
# HP coverage: at 8+ kWh/day the heat pump fully replaces gas heating
hp_coverage = float(np.clip(hp_daily / 8.0, 0.0, 1.0))
gas_baseline_year = GAS_BASELINE_M3_YEAR * gas_price  # annual gas cost without HP
gas_with_system_year = gas_baseline_year * (1.0 - hp_coverage)

# Fixed costs that change with system choices
has_export = solar_kwp > 0  # solar can export
still_needs_gas = hp_coverage < 1.0  # still partially on gas

fixed_baseline_year = float(grid_fixed_elec + grid_fixed_gas)
fixed_with_system_year = float(
    grid_fixed_elec
    + (grid_fixed_gas if still_needs_gas else 0)
    + (feedin_fixed_cost if has_export else 0)
)

# Annual all-in savings including gas + fixed cost deltas
gas_savings_year = gas_baseline_year - gas_with_system_year
fixed_savings_year = fixed_baseline_year - fixed_with_system_year

# Scenario transforms for a simpler day model.
sun_factor = sun_hours / 8.0
solar_enabled = solar_kwp > 0
bat_enabled = bat_cap > 0
ev_enabled = ev_weekly > 0
hp_enabled = hp_daily > 0
ac_enabled = ac_daily > 0

solar_kwp_effective = solar_kwp
solar_eff_effective = float(np.clip(0.85 * sun_factor, 0.0, 2.2))

hp_temp_mult = float(np.clip(1.0 + (18 - ambient_temp_c) * 0.03, 0.5, 2.2))
ac_temp_mult = float(np.clip(1.0 + (ambient_temp_c - 22) * 0.04, 0.3, 2.5))
hp_daily_effective = hp_daily * hp_temp_mult
ac_daily_effective = ac_daily * ac_temp_mult

ev_enabled_effective = ev_enabled
ev_flex_effective = sun_hours >= 8

household_base_effective = hh_base
hh_peak = 2.0
bat_pwr = float(np.clip(bat_cap / 3.0, 0.5, 10.0)) if bat_enabled else 0.0
bat_soc = 20
ac_intensity = 1.0
tou_toggle = False


# ─────────────────────────────────────────────────────────────────────────────
# Build config & run simulation
# ─────────────────────────────────────────────────────────────────────────────

cfg = SystemConfig(
    solar=SolarConfig(kwp=solar_kwp_effective, efficiency=solar_eff_effective),
    battery=BatteryConfig(
        capacity_kwh=bat_cap,
        max_charge_kw=bat_pwr,
        max_discharge_kw=bat_pwr,
        initial_soc_pct=bat_soc,
        enabled=bat_enabled,
    ),
    ev=EVConfig(enabled=ev_enabled_effective, weekly_kwh=ev_weekly, flexible=ev_flex_effective),
    heat_pump=HeatPumpConfig(enabled=hp_enabled, daily_kwh=hp_daily_effective),
    airco=AircoConfig(enabled=ac_enabled, daily_kwh=ac_daily_effective, intensity=ac_intensity),
    household=HouseholdConfig(base_kwh_day=household_base_effective, peak_multiplier=hh_peak),
    economics=EconomicsConfig(
        import_price=import_price,
        feedin_tariff=feedin_tariff,
        time_of_use=tou_toggle,
    ),
)

if run_optimizer:
    cfg = optimise(cfg)

result = simulate(cfg)

# baseline (no generation/storage) — same demand model, no solar/battery
cfg_base = SystemConfig(
    solar=SolarConfig(kwp=0.0),
    battery=BatteryConfig(enabled=False),
    ev=EVConfig(enabled=ev_enabled_effective, weekly_kwh=ev_weekly, flexible=False),
    heat_pump=HeatPumpConfig(enabled=hp_enabled, daily_kwh=hp_daily_effective),
    airco=AircoConfig(enabled=ac_enabled, daily_kwh=ac_daily_effective, intensity=ac_intensity),
    household=HouseholdConfig(base_kwh_day=household_base_effective, peak_multiplier=hh_peak),
    economics=EconomicsConfig(import_price=import_price, feedin_tariff=feedin_tariff, time_of_use=tou_toggle),
)
baseline = simulate(cfg_base)


# ─────────────────────────────────────────────────────────────────────────────
# Main dashboard
# ─────────────────────────────────────────────────────────────────────────────

# ── Hero bar ──────────────────────────────────────────────────────────────────
col_title = st.columns([1])[0]
with col_title:
    st.markdown("""
    <div style="padding: 0.4rem 0 0.2rem;">
        <span style="font-size:1.5rem; font-weight:700; letter-spacing:-0.02em;">
            Home Energy Dashboard
        </span>
        <span style="font-size:0.75rem; color:#8B949E; margin-left:0.8rem;">
            24-hour simulation · today
        </span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Energy Usage Timeline", "🔋 Battery", "💰 Cost Analysis", "📈 ROI", "🧭 System Optimizer"])

hours = HOUR_LABELS

# ── Tab 1: Energy flows stacked area ─────────────────────────────────────────
with tab1:
    top_a, top_b = st.columns([3, 1])
    with top_a:
        focus_mode = st.radio(
            "Quick focus",
            ["All", "Battery + Grid", "Grid only", "Battery only", "Demand only", "Custom"],
            horizontal=True,
            key="energy_focus_mode",
        )
    with top_b:
        lock_energy_y = st.toggle("Lock Y-axis", key="lock_energy_y")

    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)

    fig = go.Figure()

    # Supply-side traces
    fig.add_trace(go.Scatter(
        x=hours, y=result["solar"],
        name="☀️ Solar", stackgroup="supply", fill="tonexty",
        fillcolor=hex_to_rgba(SOLAR_COL, 0.30), line=dict(color=SOLAR_COL, width=2),
        hovertemplate="%{y:.2f} kWh<extra>Solar</extra>",
    ))

    fig.add_trace(go.Scatter(
        x=hours, y=result["battery_discharge"],
        name="🔋 Battery discharge", stackgroup="supply", fill="tonexty",
        fillcolor=hex_to_rgba(BATTERY_COL, 0.25), line=dict(color=BATTERY_COL, width=1.5),
        hovertemplate="%{y:.2f} kWh<extra>Battery discharge</extra>",
    ))

    # Demand-side traces
    fig.add_trace(go.Scatter(
        x=hours, y=result["household"],
        name="🏠 Household", stackgroup="demand", fill="tonexty",
        fillcolor=hex_to_rgba(LOAD_COL, 0.22), line=dict(color=LOAD_COL, width=1.5, dash="dot"),
        hovertemplate="%{y:.2f} kWh<extra>Household</extra>",
    ))

    fig.add_trace(go.Scatter(
        x=hours, y=result["ev"],
        name="🚗 EV", stackgroup="demand", fill="tonexty",
        fillcolor=hex_to_rgba(EV_COL, 0.22), line=dict(color=EV_COL, width=1.5),
        hovertemplate="%{y:.2f} kWh<extra>EV</extra>",
    ))

    fig.add_trace(go.Scatter(
        x=hours, y=result["heat_pump"],
        name="♨️ Heat pump", stackgroup="demand", fill="tonexty",
        fillcolor=hex_to_rgba(HP_COL, 0.22), line=dict(color=HP_COL, width=1.5),
        hovertemplate="%{y:.2f} kWh<extra>Heat pump</extra>",
    ))

    fig.add_trace(go.Scatter(
        x=hours, y=result["airco"],
        name="❄️ AIRCO", stackgroup="demand", fill="tonexty",
        fillcolor=hex_to_rgba(AC_COL, 0.22), line=dict(color=AC_COL, width=1.5),
        hovertemplate="%{y:.2f} kWh<extra>AIRCO</extra>",
    ))

    fig.add_trace(go.Scatter(
        x=hours, y=[-v for v in result["battery_charge"]],
        name="🔋 Battery charge",
        mode="lines",
        line=dict(color=BATTERY_COL, width=1.5, dash="dash"),
        hovertemplate="%{y:.2f} kWh<extra>Battery charge</extra>",
    ))

    # Grid import (bars)
    fig.add_trace(go.Bar(
        x=hours, y=result["grid_import"],
        name="⬇️ Grid import", marker_color=hex_to_rgba(GRID_IMP_COL, 0.50),
        hovertemplate="%{y:.2f} kWh<extra>Grid import</extra>",
    ))

    # Grid export (bars, negative = inverted)
    fig.add_trace(go.Bar(
        x=hours, y=[-v for v in result["grid_export"]],
        name="⬆️ Grid export", marker_color=hex_to_rgba(GRID_EXP_COL, 0.50),
        hovertemplate="%{y:.2f} kWh<extra>Grid export</extra>",
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="24-Hour Energy Usage Timeline", font=dict(size=13, color=TEXT_MAIN), x=0),
        barmode="overlay",
        height=340,
        yaxis_title="kWh/hour",
        uirevision=f"energy-flows-{focus_mode}-{lock_energy_y}",
    )

    if focus_mode != "Custom":
        focus_visibility = {
            "All": {
                "☀️ Solar", "🔋 Battery discharge", "🏠 Household", "🚗 EV", "♨️ Heat pump", "❄️ AIRCO",
                "🔋 Battery charge", "⬇️ Grid import", "⬆️ Grid export",
            },
            "Battery + Grid": {"🔋 Battery discharge", "🔋 Battery charge", "⬇️ Grid import", "⬆️ Grid export"},
            "Grid only": {"⬇️ Grid import", "⬆️ Grid export"},
            "Battery only": {"🔋 Battery discharge", "🔋 Battery charge"},
            "Demand only": {"🏠 Household", "🚗 EV", "♨️ Heat pump", "❄️ AIRCO"},
        }
        active_names = focus_visibility.get(focus_mode, set())
        for trace in fig.data:
            trace.visible = True if trace.name in active_names else "legendonly"

    if lock_energy_y:
        y_series = [
            result["solar"],
            result["battery_discharge"],
            result["household"],
            result["ev"],
            result["heat_pump"],
            result["airco"],
            result["grid_import"],
            result["grid_export"],
            result["battery_charge"],
        ]
        y_max = max(float(np.max(np.abs(np.asarray(s, dtype=float)))) for s in y_series)
        y_lim = max(1.0, y_max * 1.2)
        fig.update_yaxes(range=[-y_lim, y_lim])

    st.plotly_chart(fig, width="stretch", key="energy_flows_chart")
    st.markdown('</div>', unsafe_allow_html=True)

    # Demand breakdown donut
    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        demand_labels = ["Household", "EV", "Heat pump", "AIRCO"]
        demand_vals   = [
            float(result["household"].sum()),
            float(result["ev"].sum()),
            float(result["heat_pump"].sum()),
            float(result["airco"].sum()),
        ]
        demand_colors = [LOAD_COL, EV_COL, HP_COL, AC_COL]
        # filter out zeros
        filtered = [(l, v, c) for l, v, c in zip(demand_labels, demand_vals, demand_colors) if v > 0]
        if filtered:
            fl, fv, fc = zip(*filtered)
            fig_pie = go.Figure(go.Pie(
                labels=fl, values=fv, hole=0.55,
                marker=dict(colors=fc, line=dict(color=PANEL_BG, width=2)),
                textfont=dict(size=10, color=TEXT_MAIN),
            ))
            fig_pie.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="Demand Breakdown", font=dict(size=13, color=TEXT_MAIN), x=0),
                height=240,
                showlegend=True,
            )
            st.plotly_chart(fig_pie, width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        supply_labels = ["Solar (direct)", "Battery", "Grid"]
        solar_direct  = float(result["solar"].sum()) - float(result["grid_export"].sum()) - float(result["battery_charge"].sum())
        solar_direct  = max(solar_direct, 0)
        supply_vals   = [
            solar_direct,
            float(result["battery_discharge"].sum()),
            float(result["grid_import"].sum()),
        ]
        supply_colors = [SOLAR_COL, BATTERY_COL, GRID_IMP_COL]
        filtered_s = [(l, v, c) for l, v, c in zip(supply_labels, supply_vals, supply_colors) if v > 0]
        if filtered_s:
            sl, sv, sc = zip(*filtered_s)
            fig_pie2 = go.Figure(go.Pie(
                labels=sl, values=sv, hole=0.55,
                marker=dict(colors=sc, line=dict(color=PANEL_BG, width=2)),
                textfont=dict(size=10, color=TEXT_MAIN),
            ))
            fig_pie2.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="Energy Supply Sources", font=dict(size=13, color=TEXT_MAIN), x=0),
                height=240,
                showlegend=True,
            )
            st.plotly_chart(fig_pie2, width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)


# ── Tab 2: Battery ────────────────────────────────────────────────────────────
with tab2:
    if not bat_enabled:
        st.info("Enable battery storage in the sidebar to see this view.")
    else:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        fig_bat = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.45, 0.55],
            vertical_spacing=0.06,
        )

        # SOC curve
        soc_pct = [v / bat_cap * 100 if bat_cap > 0 else 0 for v in result["battery_soc"]]
        fig_bat.add_trace(go.Scatter(
            x=hours, y=soc_pct,
            name="State of charge (%)", fill="tozeroy",
            fillcolor=hex_to_rgba(BATTERY_COL, 0.25), line=dict(color=BATTERY_COL, width=2),
            hovertemplate="%{y:.1f}%<extra>SOC</extra>",
        ), row=1, col=1)

        # Charge / discharge bars
        fig_bat.add_trace(go.Bar(
            x=hours, y=result["battery_charge"],
            name="Charging", marker_color=hex_to_rgba(BATTERY_COL, 0.45),
            hovertemplate="%{y:.2f} kWh<extra>Charging</extra>",
        ), row=2, col=1)
        fig_bat.add_trace(go.Bar(
            x=hours, y=[-v for v in result["battery_discharge"]],
            name="Discharging", marker_color=hex_to_rgba(SOLAR_COL, 0.50),
            hovertemplate="%{y:.2f} kWh<extra>Discharging</extra>",
        ), row=2, col=1)

        fig_bat.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Battery State & Activity", font=dict(size=13, color=TEXT_MAIN), x=0),
            height=380,
            barmode="overlay",
        )
        fig_bat.update_yaxes(title_text="SOC (%)", row=1, col=1, tickfont=dict(size=10))
        fig_bat.update_yaxes(title_text="kWh", row=2, col=1, tickfont=dict(size=10))
        st.plotly_chart(fig_bat, width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)


# ── Tab 3: Cost analysis ──────────────────────────────────────────────────────
with tab3:
    col_ca, col_cb = st.columns(2)

    with col_ca:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        # Hourly import cost
        hourly_cost_with    = result["grid_import"] * result["prices"]
        hourly_cost_without = result["total_demand"] * result["prices"]
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Scatter(
            x=hours, y=hourly_cost_without,
            name="Without system", fill="tozeroy",
            fillcolor=hex_to_rgba(LOAD_COL, 0.25), line=dict(color=LOAD_COL, width=2),
            hovertemplate="€%{y:.3f}<extra>No system</extra>",
        ))
        fig_cost.add_trace(go.Scatter(
            x=hours, y=hourly_cost_with,
            name="With system", fill="tozeroy",
            fillcolor=hex_to_rgba(ACCENT, 0.25), line=dict(color=ACCENT, width=2),
            hovertemplate="€%{y:.3f}<extra>With system</extra>",
        ))
        fig_cost.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Hourly Electricity Cost", font=dict(size=13, color=TEXT_MAIN), x=0),
            height=280,
            yaxis_title="€",
        )
        st.plotly_chart(fig_cost, width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_cb:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        if tou_toggle:
            # Show dynamic price curve
            fig_tou = go.Figure(go.Scatter(
                x=hours, y=result["prices"],
                name="Import price", fill="tozeroy",
                fillcolor=hex_to_rgba(ACCENT2, 0.25), line=dict(color=ACCENT2, width=2),
                hovertemplate="€%{y:.3f}/kWh<extra>Price</extra>",
            ))
            fig_tou.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="Time-of-Use Price Signal", font=dict(size=13, color=TEXT_MAIN), x=0),
                height=280,
                yaxis_title="€/kWh",
            )
            st.plotly_chart(fig_tou, width="stretch")
        else:
            # Monthly savings comparison bar
            cats = ["Monthly baseline", "Monthly with system", "Monthly savings"]
            vals = [result["monthly_baseline"], result["monthly_cost"], result["monthly_savings"]]
            cols = [LOAD_COL, ACCENT, SOLAR_COL]
            fig_bar = go.Figure(go.Bar(
                x=cats, y=vals,
                marker_color=cols,
                text=[fmt_eur(v) for v in vals],
                textposition="outside",
                textfont=dict(size=10, color=TEXT_MAIN),
            ))
            fig_bar.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="Monthly Cost Comparison", font=dict(size=13, color=TEXT_MAIN), x=0),
                height=280,
                yaxis_title="€",
                showlegend=False,
            )
            st.plotly_chart(fig_bar, width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    # Grid import/export summary
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    fig_grid = go.Figure()
    fig_grid.add_trace(go.Bar(
        x=hours, y=result["grid_import"],
        name="Grid import", marker_color=hex_to_rgba(GRID_IMP_COL, 0.50),
        hovertemplate="%{y:.2f} kWh<extra>Import</extra>",
    ))
    fig_grid.add_trace(go.Bar(
        x=hours, y=result["grid_export"],
        name="Grid export", marker_color=hex_to_rgba(GRID_EXP_COL, 0.50),
        hovertemplate="%{y:.2f} kWh<extra>Export</extra>",
    ))
    fig_grid.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Grid Interaction (import / export)", font=dict(size=13, color=TEXT_MAIN), x=0),
        barmode="group",
        height=240,
        yaxis_title="kWh/hour",
    )
    st.plotly_chart(fig_grid, width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    cum_import_cost = np.cumsum(result["grid_import"] * result["prices"])
    cum_export_revenue = np.cumsum(result["grid_export"] * feedin_tariff)
    cum_net_cost = cum_import_cost - cum_export_revenue

    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(
        x=hours, y=cum_import_cost,
        name="Cumulative import cost",
        line=dict(color=LOAD_COL, width=2),
        hovertemplate="€%{y:.2f}<extra>Import cost</extra>",
    ))
    fig_cum.add_trace(go.Scatter(
        x=hours, y=cum_export_revenue,
        name="Cumulative export revenue",
        line=dict(color=GRID_EXP_COL, width=2),
        hovertemplate="€%{y:.2f}<extra>Export revenue</extra>",
    ))
    fig_cum.add_trace(go.Scatter(
        x=hours, y=cum_net_cost,
        name="Cumulative net cost",
        line=dict(color=ACCENT, width=2.5),
        hovertemplate="€%{y:.2f}<extra>Net cost</extra>",
    ))
    fig_cum.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Cumulative Cost and Revenue", font=dict(size=13, color=TEXT_MAIN), x=0),
        height=280,
        yaxis_title="€",
    )
    st.plotly_chart(fig_cum, width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)


# ── Tab 4: ROI ────────────────────────────────────────────────────────────────
with tab4:
    elec_savings_year = result["daily_savings"] * 365
    annual_savings = elec_savings_year + gas_savings_year + fixed_savings_year
    payback_years  = compute_payback(system_cost, annual_savings)
    payback_months = payback_years * 12

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.markdown(metric_card(
            "Annual all-in savings",
            fmt_eur(annual_savings),
            f"Elec {fmt_eur(elec_savings_year)} + Gas {fmt_eur(gas_savings_year)} + Fixed {fmt_eur(fixed_savings_year)}",
            cls="good" if annual_savings >= 0 else "bad",
        ), unsafe_allow_html=True)
    with col_r2:
        pb_str = f"{payback_years:.1f} years" if payback_years < 100 else "N/A"
        st.markdown(metric_card(
            "Simple payback",
            pb_str,
            f"System cost: {fmt_eur(system_cost)}",
        ), unsafe_allow_html=True)
    with col_r3:
        val_25y = annual_savings * 25 - system_cost
        st.markdown(metric_card(
            "25-year net value",
            fmt_eur(val_25y),
            "Cumulative savings − install cost",
            cls="good" if val_25y >= 0 else "bad",
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Cumulative savings curve
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    years_range = list(range(0, 26))
    cum_savings = [annual_savings * y - system_cost for y in years_range]

    fig_roi = go.Figure()
    # Shade negative region
    neg_vals = [min(v, 0) for v in cum_savings]
    pos_vals = [max(v, 0) for v in cum_savings]

    fig_roi.add_trace(go.Scatter(
        x=years_range, y=neg_vals,
        name="In debt", fill="tozeroy",
        fillcolor=hex_to_rgba(LOAD_COL, 0.20), line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
    ))
    fig_roi.add_trace(go.Scatter(
        x=years_range, y=pos_vals,
        name="In profit", fill="tozeroy",
        fillcolor=hex_to_rgba(ACCENT, 0.20), line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
    ))
    fig_roi.add_trace(go.Scatter(
        x=years_range, y=cum_savings,
        name="Net value", line=dict(color=ACCENT, width=2.5),
        hovertemplate="Year %{x}: €%{y:,.0f}<extra></extra>",
    ))
    # Breakeven line
    fig_roi.add_hline(y=0, line=dict(color=TEXT_MUTED, dash="dash", width=1))
    if payback_years < 25:
        fig_roi.add_vline(
            x=payback_years,
            line=dict(color=SOLAR_COL, dash="dot", width=1.5),
            annotation_text=f"Breakeven ~{payback_years:.1f}y",
            annotation_font=dict(color=SOLAR_COL, size=10),
        )
    fig_roi.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Cumulative Net Value Over 25 Years", font=dict(size=13, color=TEXT_MAIN), x=0),
        height=320,
        xaxis_title="Year",
        yaxis_title="Net value (€)",
    )
    st.plotly_chart(fig_roi, width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)


# ── Tab 5: System optimizer ─────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.caption("Sweep of solar and battery sizes while keeping all other current sidebar settings fixed.")

    design = compute_design_space(
        solar_eff=solar_eff_effective,
        household_base=household_base_effective,
        hh_peak_mult=hh_peak,
        ev_enabled=ev_enabled_effective,
        ev_weekly_kwh=ev_weekly,
        ev_flexible=ev_flex_effective,
        hp_enabled=hp_enabled,
        hp_daily_kwh=hp_daily_effective,
        ac_enabled=ac_enabled,
        ac_daily_kwh=ac_daily_effective,
        ac_intensity_val=ac_intensity,
        import_price_val=import_price,
        feedin_tariff_val=feedin_tariff,
        use_optimizer=run_optimizer,
        p_solar=float(price_solar),
        p_battery=float(price_battery),
        p_ev=float(price_ev),
        p_hp=float(price_hp),
        p_ac=float(price_ac),
        gas_savings_yr=gas_savings_year,
        fixed_savings_yr=fixed_savings_year,
    )

    solar_sizes = design["solar_sizes"]
    battery_sizes = design["battery_sizes"]
    savings_grid = design["annual_savings_grid"]
    optimization_grid = design["optimization_grid"]
    points = design["points"]

    best_savings_idx = np.unravel_index(np.argmax(savings_grid), savings_grid.shape)
    best_savings_battery = float(battery_sizes[best_savings_idx[0]])
    best_savings_solar = float(solar_sizes[best_savings_idx[1]])
    best_savings = float(savings_grid[best_savings_idx])

    best_score_idx = np.unravel_index(np.argmax(optimization_grid), optimization_grid.shape)
    best_score_battery = float(battery_sizes[best_score_idx[0]])
    best_score_solar = float(solar_sizes[best_score_idx[1]])
    best_score = float(optimization_grid[best_score_idx])

    c_opt1, c_opt2, c_opt3 = st.columns(3)
    with c_opt1:
        st.markdown(metric_card("Best annual savings", fmt_eur(best_savings), f"Solar {best_savings_solar:.0f} kWp · Battery {best_savings_battery:.0f} kWh", cls="good"), unsafe_allow_html=True)
    with c_opt2:
        st.markdown(metric_card("Best optimization score", fmt_eur(best_score), "Annual savings − capex", cls="warn"), unsafe_allow_html=True)
    with c_opt3:
        st.markdown(metric_card("Best score sizing", f"{best_score_solar:.0f} / {best_score_battery:.0f}", "Solar kWp / Battery kWh"), unsafe_allow_html=True)

    st.caption("Heatmap values are annual savings in € per year. Green means higher savings; red means lower or negative savings.")
    fig_heat = go.Figure(
        data=go.Heatmap(
            x=solar_sizes,
            y=battery_sizes,
            z=savings_grid,
            colorscale="RdYlGn",
            zmid=0,
            xgap=1,
            ygap=1,
            colorbar=dict(title="Annual savings (€/year)", tickprefix="€"),
            hovertemplate=(
                "Solar: %{x:.0f} kWp<br>"
                "Battery: %{y:.0f} kWh<br>"
                "Annual savings: €%{z:,.0f}<extra></extra>"
            ),
        )
    )
    fig_heat.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Annual Savings Heatmap (Solar vs Battery)", font=dict(size=13, color=TEXT_MAIN), x=0),
        height=380,
        xaxis_title="Solar size (kWp)",
        yaxis_title="Battery size (kWh)",
    )
    fig_heat.add_trace(go.Scatter(
        x=[best_savings_solar],
        y=[best_savings_battery],
        mode="markers",
        name="Best annual savings",
        marker=dict(symbol="x", size=12, color=TEXT_MAIN, line=dict(width=1, color=PANEL_BG)),
        hovertemplate=(
            f"Best annual savings point<br>Solar: {best_savings_solar:.0f} kWp<br>"
            f"Battery: {best_savings_battery:.0f} kWh<br>Annual savings: {fmt_eur(best_savings)}"
            "<extra></extra>"
        ),
    ))
    st.plotly_chart(fig_heat, width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)

    pareto_flags = []
    for p in points:
        dominated = False
        for q in points:
            if (
                (q["capex"] <= p["capex"]) and
                (q["annual_savings"] >= p["annual_savings"]) and
                ((q["capex"] < p["capex"]) or (q["annual_savings"] > p["annual_savings"]))
            ):
                dominated = True
                break
        pareto_flags.append(not dominated)

    pareto_points = [p for p, keep in zip(points, pareto_flags) if keep]
    other_points = [p for p, keep in zip(points, pareto_flags) if not keep]

    fig_pf = go.Figure()
    if other_points:
        fig_pf.add_trace(go.Scatter(
            x=[p["capex"] for p in other_points],
            y=[p["annual_savings"] for p in other_points],
            mode="markers",
            name="Other designs",
            marker=dict(
                size=5,
                color=[p["score"] for p in other_points],
                colorscale="RdYlGn",
                cmin=float(np.min(optimization_grid)),
                cmax=float(np.max(optimization_grid)),
                opacity=0.45,
                colorbar=dict(title="Score (€/year)", tickprefix="€"),
            ),
            customdata=np.array([[p["solar"], p["battery"], p["score"]] for p in other_points]),
            hovertemplate=(
                "Solar: %{customdata[0]:.0f} kWp<br>"
                "Battery: %{customdata[1]:.0f} kWh<br>"
                "Capex: €%{x:,.0f}<br>"
                "Annual savings: €%{y:,.0f}<br>"
                "Score (savings - capex): €%{customdata[2]:,.0f}<extra>Other</extra>"
            ),
        ))
    if pareto_points:
        pareto_sorted = sorted(pareto_points, key=lambda p: p["capex"])
        fig_pf.add_trace(go.Scatter(
            x=[p["capex"] for p in pareto_sorted],
            y=[p["annual_savings"] for p in pareto_sorted],
            mode="markers+lines",
            name="Pareto frontier",
            marker=dict(size=8, color=ACCENT),
            line=dict(color=ACCENT, width=2),
            customdata=np.array([[p["solar"], p["battery"], p["score"]] for p in pareto_sorted]),
            hovertemplate=(
                "Solar: %{customdata[0]:.0f} kWp<br>"
                "Battery: %{customdata[1]:.0f} kWh<br>"
                "Capex: €%{x:,.0f}<br>"
                "Annual savings: €%{y:,.0f}<br>"
                "Score (savings - capex): €%{customdata[2]:,.0f}<extra>Pareto</extra>"
            ),
        ))

    fig_pf.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Pareto Trade-off (Capex vs Annual Savings)", font=dict(size=13, color=TEXT_MAIN), x=0),
        height=340,
        xaxis_title="Estimated system capex (€)",
        yaxis_title="Annual savings (€)",
    )
    st.plotly_chart(fig_pf, width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# KPI cards row 1 — financials (below charts)
# ─────────────────────────────────────────────────────────────────────────────
section_header("Daily Financials")

c1, c2, c3, c4 = st.columns(4)

savings_cls = "good" if result["daily_savings"] >= 0 else "bad"
with c1:
    st.markdown(metric_card(
        "Daily cost — with system",
        fmt_eur(result["daily_cost_with_system"]),
        f"Monthly: {fmt_eur(result['monthly_cost'])}",
    ), unsafe_allow_html=True)

with c2:
    st.markdown(metric_card(
        "Baseline cost (no system)",
        fmt_eur(result["daily_cost_baseline"]),
        f"Monthly: {fmt_eur(baseline['monthly_cost'])}",
    ), unsafe_allow_html=True)

with c3:
    st.markdown(metric_card(
        "Daily elec savings",
        fmt_eur(result["daily_savings"]),
        f"{fmt_pct(result['savings_pct'])} reduction",
        cls=savings_cls,
    ), unsafe_allow_html=True)

with c4:
    st.markdown(metric_card(
        "Export revenue",
        fmt_eur(result["daily_export_revenue"]),
        f"Feed-in: {fmt_eur(feedin_tariff)}/kWh",
        cls="warn",
    ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Annual all-in overview
section_header("Annual All-in Overview")

ca1, ca2, ca3, ca4 = st.columns(4)
with ca1:
    total_baseline_year = float(result["daily_cost_baseline"] * 365) + gas_baseline_year + fixed_baseline_year
    st.markdown(metric_card(
        "Baseline total",
        fmt_eur(total_baseline_year) + "/yr",
        "Elec + gas + fixed costs",
    ), unsafe_allow_html=True)
with ca2:
    total_system_year = float(result["daily_cost_with_system"] * 365) + gas_with_system_year + fixed_with_system_year
    st.markdown(metric_card(
        "With system total",
        fmt_eur(total_system_year) + "/yr",
        "Elec + gas + fixed costs",
        cls="good" if total_system_year < total_baseline_year else "",
    ), unsafe_allow_html=True)
with ca3:
    st.markdown(metric_card(
        "Gas savings",
        fmt_eur(gas_savings_year) + "/yr",
        f"HP covers {hp_coverage*100:.0f}% of heating",
        cls="good" if gas_savings_year > 0 else "",
    ), unsafe_allow_html=True)
with ca4:
    st.markdown(metric_card(
        "Fixed cost delta",
        fmt_eur(fixed_savings_year) + "/yr",
        "Gas connection − feed-in cost",
        cls="good" if fixed_savings_year > 0 else ("bad" if fixed_savings_year < 0 else ""),
    ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# KPI cards row 2 — energy metrics (below charts)
# ─────────────────────────────────────────────────────────────────────────────
section_header("Energy Metrics")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(metric_card(
        "Solar generated",
        fmt_kwh(result["total_solar_kwh"]),
        f"{solar_kwp} kWp array",
        cls="warn",
    ), unsafe_allow_html=True)

with c2:
    st.markdown(metric_card(
        "Self-consumption",
        fmt_pct(result["self_consumption_pct"]),
        "Solar used on-site",
        cls="good",
    ), unsafe_allow_html=True)

with c3:
    st.markdown(metric_card(
        "Solar coverage",
        fmt_pct(result["solar_utilisation_pct"]),
        "Of total demand met by solar",
        cls="good",
    ), unsafe_allow_html=True)

with c4:
    grid_cls = "bad" if result["grid_dependency_pct"] > 60 else ("warn" if result["grid_dependency_pct"] > 30 else "good")
    st.markdown(metric_card(
        "Grid dependency",
        fmt_pct(result["grid_dependency_pct"]),
        "Of demand imported",
        cls=grid_cls,
    ), unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align:center; color:{TEXT_MUTED}; font-size:0.68rem; padding:0.5rem 0 1rem;">
    Home Energy Configurator · 24-hour deterministic simulation · All figures are estimates
</div>
""", unsafe_allow_html=True)
