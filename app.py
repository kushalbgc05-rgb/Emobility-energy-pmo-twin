import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- 1. RESPONSIVE PAGE CONFIGURATION ---
st.set_page_config(page_title="Gigafactory Project and Capex Tracker", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        transition: transform 0.2s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #0284c7;
    }
    .reference-link {
        color: #0284c7;
        text-decoration: none;
        font-weight: 500;
    }
    .reference-link:hover {
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Gigafactory Project and Capex Tracker")
st.markdown("**Executive decision platform:** Modeling 5-year exponential grid shocks alongside on-site microgrid execution and NPV returns.")
st.markdown("---")

# --- 2. PMO & OPERATIONAL CONTROLS ---
st.sidebar.header("🎛️ PMO Control Matrix")

with st.sidebar.expander("1. Macro Energy Risk (5-Year)", expanded=True):
    base_elec_mwh = st.sidebar.number_input("Base Grid Price (€/MWh)", 50.0, 300.0, 95.0, 5.0)
    annual_elec_growth = st.sidebar.slider("Annual Energy Inflation (%)", 5.0, 50.0, 20.0, 1.0) / 100.0

with st.sidebar.expander("2. Gigafactory Operations", expanded=True):
    annual_capacity_gwh = st.sidebar.slider("Plant Capacity (GWh/yr)", 10, 100, 40, 5)
    scrap_rate = st.sidebar.slider("Factory Scrap Rate (%)", 5.0, 30.0, 15.0, 1.0) / 100.0
    energy_intensity_kwh = 45  # kWh electricity per kWh battery output (IEA 2022)

with st.sidebar.expander("3. Microgrid Capex & Offset Target", expanded=True):
    bac_capex_mln = st.sidebar.number_input("Microgrid Budget (BAC) [€M]", 50.0, 400.0, 150.0, 10.0)
    grid_offset_pct = st.sidebar.slider("Microgrid Generation Target (%)", 20.0, 80.0, 50.0, 5.0) / 100.0

with st.sidebar.expander("4. Project Delivery (EVM Governance)", expanded=True):
    planned_duration = st.sidebar.slider("Planned Timeline (Months)", 12, 36, 24, 1)
    schedule_slippage = st.sidebar.slider("Schedule Slippage (Months)", 0, 12, 3, 1)
    cpi_performance = st.sidebar.slider("Cost Performance Index (CPI)", 0.70, 1.20, 0.90, 0.01)
    spi_performance = st.sidebar.slider("Schedule Performance Index (SPI)", 0.70, 1.20, 0.85, 0.01)
    discount_rate = 0.08

# --- 3. CORE FINANCIAL & ENERGY CALCULATIONS ---
years = np.arange(2026, 2031)
horizon_len = len(years)

# 5-Year electricity trajectory
projected_grid_prices_mwh = [base_elec_mwh * ((1 + annual_elec_growth) ** i) for i in range(horizon_len)]
projected_grid_prices_kwh = [price / 1000.0 for price in projected_grid_prices_mwh]

# Realistic energy consumption: 1 GWh = 1,000,000 kWh
annual_good_output_kwh = annual_capacity_gwh * 1_000_000
total_energy_needed_kwh = (annual_good_output_kwh * energy_intensity_kwh) / (1 - scrap_rate)

# OPEX in Millions of Euros (€M)
legacy_opex_mln = [(total_energy_needed_kwh * price) / 1_000_000.0 for price in projected_grid_prices_kwh]
microgrid_opex_mln = [(total_energy_needed_kwh * price * (1 - grid_offset_pct)) / 1_000_000.0 for price in projected_grid_prices_kwh]
annual_savings_mln = [leg - mic for leg, mic in zip(legacy_opex_mln, microgrid_opex_mln)]

# EVM & Slippage Cash Impact
actual_duration = planned_duration + schedule_slippage
eac_capex_mln = bac_capex_mln / cpi_performance
cost_variance_mln = bac_capex_mln - eac_capex_mln

# Cost of Delay based on unrealized monthly clean energy savings
monthly_savings_year1 = annual_savings_mln[0] / 12.0
cost_of_delay_mln = monthly_savings_year1 * schedule_slippage

# NPV Calculation (€M)
cash_flows = [-eac_capex_mln] + annual_savings_mln
discount_factors = [(1 + discount_rate) ** i for i in range(len(cash_flows))]
dcf = [cf / df for cf, df in zip(cash_flows, discount_factors)]
npv_mln = sum(dcf)

# --- 4. EXECUTIVE KPIS ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        "2030 Grid Exposure (No Hedge)",
        f"€{projected_grid_prices_mwh[-1]:.0f}/MWh",
        f"€{legacy_opex_mln[-1]:.1f}M / yr bill",
        delta_color="inverse"
    )
with kpi2:
    st.metric(
        "5-Year Microgrid NPV",
        f"€{npv_mln:.1f}M",
        f"Payback: ~{abs(eac_capex_mln / annual_savings_mln[0]):.1f} yrs",
        delta_color="normal" if npv_mln > 0 else "inverse"
    )
with kpi3:
    st.metric(
        "Forecast Capex (EAC)",
        f"€{eac_capex_mln:.1f}M",
        f"Variance: €{cost_variance_mln:+.1f}M (CPI {cpi_performance:.2f})",
        delta_color="inverse" if cost_variance_mln < 0 else "normal"
    )
with kpi4:
    st.metric(
        "Cost of Delay (CoD)",
        f"€{cost_of_delay_mln:.1f}M Loss",
        f"{schedule_slippage} Mo. Slippage (SPI {spi_performance:.2f})",
        delta_color="inverse"
    )

st.markdown("<br>", unsafe_allow_html=True)

# --- 5. DATA VISUALIZATIONS ---
st.subheader("I. Strategic Business Case: 5-Year Energy Inflation vs. Microgrid Protection")
st.caption("Compares total factory energy expenditure under 100% grid reliance vs. a 50% on-site microgrid hedge.")

fig_forecast = go.Figure()

# Legacy line
fig_forecast.add_trace(go.Scatter(
    x=years, y=legacy_opex_mln,
    mode='lines+markers', name='Unmitigated Grid OPEX (100% Exposure)',
    line=dict(color='#dc2626', width=3)
))

# Microgrid protected line
fig_forecast.add_trace(go.Scatter(
    x=years, y=microgrid_opex_mln,
    mode='lines+markers', name=f'Protected OPEX ({grid_offset_pct*100:.0f}% Clean Microgrid)',
    line=dict(color='#059669', width=3),
    fill='tonexty', fillcolor='rgba(16, 185, 129, 0.15)'
))

fig_forecast.update_layout(
    height=380,
    yaxis_title="Annual Plant Electricity Cost (€M/year)",
    xaxis_title="Operational Year",
    hovermode="x unified",
    margin=dict(t=20, b=20, l=20, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_forecast, use_container_width=True, config={'displayModeBar': True, 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape']})

col_bottom1, col_bottom2 = st.columns(2)

with col_bottom1:
    st.subheader("II. Delivery Governance: Microgrid Build Health (EVM)")
    st.caption("Tracks capital expenditure delivery using Earned Value Management.")

    months_arr = np.arange(0, actual_duration + 1)
    pv_arr = np.where(months_arr <= planned_duration, (bac_capex_mln / planned_duration) * months_arr, bac_capex_mln)
    ev_arr = (bac_capex_mln / actual_duration) * months_arr
    ac_arr = (eac_capex_mln / actual_duration) * months_arr

    fig_evm = go.Figure()
    fig_evm.add_trace(go.Scatter(x=months_arr, y=pv_arr, mode='lines', name='Planned Value (PV)', line=dict(dash='dash', color='#64748b', width=2)))
    fig_evm.add_trace(go.Scatter(x=months_arr, y=ev_arr, mode='lines', name='Earned Value (EV)', line=dict(color='#0284c7', width=2.5)))
    fig_evm.add_trace(go.Scatter(x=months_arr, y=ac_arr, mode='lines', name='Actual Cost (AC)', line=dict(color='#d97706', width=2.5)))

    fig_evm.update_layout(
        height=360,
        xaxis_title="Construction Timeline (Months)",
        yaxis_title="Cumulative Capital Spend (€M)",
        margin=dict(t=30, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_evm, use_container_width=True, config={'displayModeBar': True, 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape']})

with col_bottom2:
    st.subheader("III. Financial Return: Discounted Cash Flow Waterfall")
    st.caption("Initial microgrid construction Capex vs. cumulative discounted energy savings.")

    waterfall_labels = ["Initial Capex"] + [f"Year {y}" for y in years] + ["Net Present Value"]
    waterfall_measures = ["relative"] + ["relative"] * len(years) + ["total"]
    waterfall_values = [-eac_capex_mln] + dcf[1:] + [0]

    fig_waterfall = go.Figure(go.Waterfall(
        name="NPV Waterfall", orientation="v",
        measure=waterfall_measures,
        x=waterfall_labels,
        y=waterfall_values,
        decreasing={"marker": {"color": "#dc2626"}},
        increasing={"marker": {"color": "#059669"}},
        totals={"marker": {"color": "#0284c7"}}
    ))

    fig_waterfall.update_layout(
        height=360,
        yaxis_title="Discounted Cash Flow (€M)",
        margin=dict(t=30, b=20, l=20, r=20)
    )
    st.plotly_chart(fig_waterfall, use_container_width=True, config={'displayModeBar': True, 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape']})

# --- 6. DATA SOURCES ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander(" Data Sources", expanded=False):
    st.markdown("""
    **1. Grid Rate Inflation & Gigafactory Energy Intensity:**
    > International Energy Agency (IEA). *"Global Supply Chains of EV Batteries."*
    > <a href="https://www.iea.org/reports/global-supply-chains-of-ev-batteries" class="reference-link" target="_blank">IEA Official Report</a>
    <br><span style="font-size: 0.85em; color: gray;"><i>(Validates the ~45 kWh/kWh manufacturing energy intensity metric and the exposure of gigafactories to compounding grid price inflation).</i></span>

    <br>

    **2. Industrial Microgrid OPEX Reduction & Economic Optimization:**
    > Piasecki, P., et al. *"Smart Management of Energy Storage in Microgrid."* **Sustainability 15**, 15576 (2023).
    > <a href="https://doi.org/10.3390/su152115576" class="reference-link" target="_blank">DOI: 10.3390/su152115576</a>
    <br><span style="font-size: 0.85em; color: gray;"><i>(Peer-reviewed framework modeling how on-site microgrids hedge against wholesale grid price volatility, yielding positive Net Present Value).</i></span>
    """, unsafe_allow_html=True)
