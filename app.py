"""
app.py – Home Energy System Configurator & Optimizer
Run with: streamlit run app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from models import (
    SystemConfig, SolarConfig, BatteryConfig, EVConfig,
    HeatPumpConfig, HouseholdConfig, EconomicsConfig,
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
TEXT_MUTED   = "#8B949E"
TEXT_MAIN    = "#E6EDF3"

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] {{
      font-family: 'Inter', sans-serif;
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
      font-family: 'JetBrains Mono', monospace;
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
    font=dict(family="Inter", color=TEXT_MUTED, size=11),
    margin=dict(l=0, r=10, t=30, b=0),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
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


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — controls
# ─────────────────────────────────────────────────────────────────────────────

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

    # ── Solar ──────────────────────────────────────────────────────────────────
    st.markdown("### ☀️ Solar Panels")
    solar_kwp = st.slider("System size (kWp)", 0.0, 20.0, 6.0, 0.5)
    solar_eff  = st.slider("Panel efficiency", 0.60, 1.00, 0.85, 0.01,
                            help="Accounts for orientation, shading, inverter losses")

    # ── Battery ───────────────────────────────────────────────────────────────
    st.markdown("### 🔋 Battery Storage")
    bat_enabled = st.checkbox("Enable battery", value=True)
    bat_cap     = st.slider("Capacity (kWh)", 0.0, 30.0, 10.0, 0.5, disabled=not bat_enabled)
    bat_pwr     = st.slider("Max charge/discharge (kW)", 0.5, 10.0, 3.0, 0.5, disabled=not bat_enabled)
    bat_soc     = st.slider("Initial state of charge (%)", 0, 100, 20, 5, disabled=not bat_enabled)

    # ── EV ────────────────────────────────────────────────────────────────────
    st.markdown("### 🚗 EV Charger")
    ev_enabled  = st.checkbox("Enable EV charging", value=False)
    ev_weekly   = st.slider("Weekly charge demand (kWh)", 10.0, 200.0, 70.0, 5.0, disabled=not ev_enabled)
    ev_flex     = st.checkbox("Flexible charging (follows solar)", value=True, disabled=not ev_enabled)

    # ── Heat Pump ─────────────────────────────────────────────────────────────
    st.markdown("### ♨️ Heat Pump")
    hp_enabled  = st.checkbox("Enable heat pump", value=False)
    hp_daily    = st.slider("Daily demand (kWh)", 1.0, 30.0, 8.0, 0.5, disabled=not hp_enabled)

    # ── Household ─────────────────────────────────────────────────────────────
    st.markdown("### 🏠 Household Load")
    hh_base     = st.slider("Base load (kWh/day)", 2.0, 30.0, 10.0, 0.5)
    hh_peak     = st.slider("Evening peak multiplier", 1.0, 4.0, 2.0, 0.1,
                             help="How much higher evening demand is vs average daytime")

    # ── Economics ─────────────────────────────────────────────────────────────
    st.markdown("### 💰 Energy Economics")
    import_price  = st.slider("Import price (€/kWh)", 0.10, 0.60, 0.28, 0.01)
    feedin_tariff = st.slider("Feed-in tariff (€/kWh)", 0.00, 0.30, 0.08, 0.01)
    tou_toggle    = st.checkbox("Time-of-use pricing", value=False,
                                 help="Enables dynamic peak/off-peak electricity prices")

    st.divider()

    # ── Optimiser ─────────────────────────────────────────────────────────────
    st.markdown("### 🧠 Optimizer")
    run_optimizer = st.checkbox("Apply smart optimization", value=False,
                                 help="Shifts EV charging and battery SOC for minimum cost")

    # ── ROI inputs ────────────────────────────────────────────────────────────
    st.markdown("### 📊 ROI Estimator")
    system_cost = st.number_input("System install cost (€)", 0, 50000, 12000, 500)


# ─────────────────────────────────────────────────────────────────────────────
# Build config & run simulation
# ─────────────────────────────────────────────────────────────────────────────

cfg = SystemConfig(
    solar=SolarConfig(kwp=solar_kwp, efficiency=solar_eff),
    battery=BatteryConfig(
        capacity_kwh=bat_cap,
        max_charge_kw=bat_pwr,
        max_discharge_kw=bat_pwr,
        initial_soc_pct=bat_soc,
        enabled=bat_enabled,
    ),
    ev=EVConfig(enabled=ev_enabled, weekly_kwh=ev_weekly, flexible=ev_flex),
    heat_pump=HeatPumpConfig(enabled=hp_enabled, daily_kwh=hp_daily),
    household=HouseholdConfig(base_kwh_day=hh_base, peak_multiplier=hh_peak),
    economics=EconomicsConfig(
        import_price=import_price,
        feedin_tariff=feedin_tariff,
        time_of_use=tou_toggle,
    ),
)

if run_optimizer:
    cfg = optimise(cfg)

result  = simulate(cfg)

# baseline (no system) — only household + ev + hp, no solar/battery
cfg_base = SystemConfig(
    solar=SolarConfig(kwp=0.0),
    battery=BatteryConfig(enabled=False),
    ev=EVConfig(enabled=ev_enabled, weekly_kwh=ev_weekly, flexible=False),
    heat_pump=HeatPumpConfig(enabled=hp_enabled, daily_kwh=hp_daily),
    household=HouseholdConfig(base_kwh_day=hh_base, peak_multiplier=hh_peak),
    economics=EconomicsConfig(import_price=import_price, feedin_tariff=feedin_tariff, time_of_use=tou_toggle),
)
baseline = simulate(cfg_base)


# ─────────────────────────────────────────────────────────────────────────────
# Main dashboard
# ─────────────────────────────────────────────────────────────────────────────

# ── Hero bar ──────────────────────────────────────────────────────────────────
col_title, col_badge = st.columns([6, 1])
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
with col_badge:
    if run_optimizer:
        st.markdown('<br><span class="opt-badge">🧠 Optimised</span>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# KPI cards row 1 — financials
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
        "Daily savings",
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

# ─────────────────────────────────────────────────────────────────────────────
# KPI cards row 2 — energy metrics
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

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["⚡ Energy Flows", "🔋 Battery", "💰 Cost Analysis", "📈 ROI"])

hours = HOUR_LABELS

# ── Tab 1: Energy flows stacked area ─────────────────────────────────────────
with tab1:
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)

    fig = go.Figure()

    # Solar generation
    fig.add_trace(go.Scatter(
        x=hours, y=result["solar"],
        name="☀️ Solar", fill="tozeroy",
        fillcolor=f"{SOLAR_COL}30", line=dict(color=SOLAR_COL, width=2),
        hovertemplate="%{y:.2f} kWh<extra>Solar</extra>",
    ))

    # Household load
    fig.add_trace(go.Scatter(
        x=hours, y=result["household"],
        name="🏠 Household", fill="tozeroy",
        fillcolor=f"{LOAD_COL}22", line=dict(color=LOAD_COL, width=1.5, dash="dot"),
        hovertemplate="%{y:.2f} kWh<extra>Household</extra>",
    ))

    if ev_enabled:
        fig.add_trace(go.Scatter(
            x=hours, y=result["ev"],
            name="🚗 EV", fill="tozeroy",
            fillcolor=f"{EV_COL}22", line=dict(color=EV_COL, width=1.5),
            hovertemplate="%{y:.2f} kWh<extra>EV</extra>",
        ))

    if hp_enabled:
        fig.add_trace(go.Scatter(
            x=hours, y=result["heat_pump"],
            name="♨️ Heat pump", fill="tozeroy",
            fillcolor=f"{HP_COL}22", line=dict(color=HP_COL, width=1.5),
            hovertemplate="%{y:.2f} kWh<extra>Heat pump</extra>",
        ))

    # Grid import (bars)
    fig.add_trace(go.Bar(
        x=hours, y=result["grid_import"],
        name="⬇️ Grid import", marker_color=f"{GRID_IMP_COL}80",
        hovertemplate="%{y:.2f} kWh<extra>Grid import</extra>",
    ))

    # Grid export (bars, negative = inverted)
    fig.add_trace(go.Bar(
        x=hours, y=[-v for v in result["grid_export"]],
        name="⬆️ Grid export", marker_color=f"{GRID_EXP_COL}80",
        hovertemplate="%{y:.2f} kWh<extra>Grid export</extra>",
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="24-Hour Energy Flow", font=dict(size=13, color=TEXT_MAIN), x=0),
        barmode="overlay",
        height=340,
        yaxis_title="kWh/hour",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Demand breakdown donut
    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        demand_labels = ["Household", "EV", "Heat pump"]
        demand_vals   = [
            float(result["household"].sum()),
            float(result["ev"].sum()),
            float(result["heat_pump"].sum()),
        ]
        demand_colors = [LOAD_COL, EV_COL, HP_COL]
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
            st.plotly_chart(fig_pie, use_container_width=True)
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
            st.plotly_chart(fig_pie2, use_container_width=True)
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
            fillcolor=f"{BATTERY_COL}25", line=dict(color=BATTERY_COL, width=2),
            hovertemplate="%{y:.1f}%<extra>SOC</extra>",
        ), row=1, col=1)

        # Charge / discharge bars
        fig_bat.add_trace(go.Bar(
            x=hours, y=result["battery_charge"],
            name="Charging", marker_color=f"{BATTERY_COL}70",
            hovertemplate="%{y:.2f} kWh<extra>Charging</extra>",
        ), row=2, col=1)
        fig_bat.add_trace(go.Bar(
            x=hours, y=[-v for v in result["battery_discharge"]],
            name="Discharging", marker_color=f"{SOLAR_COL}80",
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
        st.plotly_chart(fig_bat, use_container_width=True)
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
            fillcolor=f"{LOAD_COL}25", line=dict(color=LOAD_COL, width=2),
            hovertemplate="€%{y:.3f}<extra>No system</extra>",
        ))
        fig_cost.add_trace(go.Scatter(
            x=hours, y=hourly_cost_with,
            name="With system", fill="tozeroy",
            fillcolor=f"{ACCENT}25", line=dict(color=ACCENT, width=2),
            hovertemplate="€%{y:.3f}<extra>With system</extra>",
        ))
        fig_cost.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Hourly Electricity Cost", font=dict(size=13, color=TEXT_MAIN), x=0),
            height=280,
            yaxis_title="€",
        )
        st.plotly_chart(fig_cost, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_cb:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        if tou_toggle:
            # Show dynamic price curve
            fig_tou = go.Figure(go.Scatter(
                x=hours, y=result["prices"],
                name="Import price", fill="tozeroy",
                fillcolor=f"{ACCENT2}25", line=dict(color=ACCENT2, width=2),
                hovertemplate="€%{y:.3f}/kWh<extra>Price</extra>",
            ))
            fig_tou.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="Time-of-Use Price Signal", font=dict(size=13, color=TEXT_MAIN), x=0),
                height=280,
                yaxis_title="€/kWh",
            )
            st.plotly_chart(fig_tou, use_container_width=True)
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
            st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Grid import/export summary
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    fig_grid = go.Figure()
    fig_grid.add_trace(go.Bar(
        x=hours, y=result["grid_import"],
        name="Grid import", marker_color=f"{GRID_IMP_COL}80",
        hovertemplate="%{y:.2f} kWh<extra>Import</extra>",
    ))
    fig_grid.add_trace(go.Bar(
        x=hours, y=result["grid_export"],
        name="Grid export", marker_color=f"{GRID_EXP_COL}80",
        hovertemplate="%{y:.2f} kWh<extra>Export</extra>",
    ))
    fig_grid.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Grid Interaction (import / export)", font=dict(size=13, color=TEXT_MAIN), x=0),
        barmode="group",
        height=240,
        yaxis_title="kWh/hour",
    )
    st.plotly_chart(fig_grid, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── Tab 4: ROI ────────────────────────────────────────────────────────────────
with tab4:
    annual_savings = result["daily_savings"] * 365
    payback_years  = compute_payback(system_cost, annual_savings)
    payback_months = payback_years * 12

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.markdown(metric_card(
            "Annual savings",
            fmt_eur(annual_savings),
            f"{fmt_eur(result['daily_savings'])}/day",
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
        fillcolor=f"{LOAD_COL}20", line=dict(color="transparent"),
        showlegend=False,
    ))
    fig_roi.add_trace(go.Scatter(
        x=years_range, y=pos_vals,
        name="In profit", fill="tozeroy",
        fillcolor=f"{ACCENT}20", line=dict(color="transparent"),
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
    st.plotly_chart(fig_roi, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align:center; color:{TEXT_MUTED}; font-size:0.68rem; padding:0.5rem 0 1rem;">
    Home Energy Configurator · 24-hour deterministic simulation · All figures are estimates
</div>
""", unsafe_allow_html=True)
