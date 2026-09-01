import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- 1. RESPONSIVE PAGE CONFIGURATION ---
st.set_page_config(page_title="PMO Energy Command Center", layout="wide", initial_sidebar_state="expanded")

# Dynamic CSS that adapts to BOTH Light and Dark themes
st.markdown("""
    <style>
    /* Responsive Metric Cards using Streamlit's native variables */
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        border-color: var(--primary-color);
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ E-Mobility PMO Command Center")
st.markdown("**Executive decision platform:** Modeling 5-year exponential grid shocks alongside on-site microgrid execution and NPV returns.")
st.markdown("---")

# --- 2. THE 6 PROJECT & BUSINESS PARAMETERS ---
st.sidebar.header("🎛️ PMO Control Matrix")

with st.sidebar.expander("Macro Energy Forecast (5-Year)", expanded=True):
    base_elec_mwh = st.sidebar.number_input("1. Base Grid Price (€/MWh)", 50.0, 300.0, 95.0, 5.0)
    annual_elec_growth = st.sidebar.slider("2. Annual Energy Inflation (%)", 5.0, 50.0, 25.0, 1.0) / 100.0

with st.sidebar.expander("Gigafactory Operations", expanded=True):
    annual_capacity_gwh = st.sidebar.slider("3. Plant Capacity (GWh/yr)", 10, 100, 40, 5)
    scrap_rate = st.sidebar.slider("4. Factory Scrap Rate (%)", 5.0, 30.0, 15.0, 1.0) / 100.0
    energy_intensity_kwh = 45

with st.sidebar.expander("PMO: Microgrid Capex Execution", expanded=True):
    bac_capex_mln = st.sidebar.number_input("5. Microgrid Budget (BAC) [€M]", 50.0, 300.0, 150.0, 10.0)
    grid_offset_pct = st.sidebar.slider("6. Grid Energy Offset Target (%)", 20.0, 80.0, 50.0, 5.0) / 100.0

with st.sidebar.expander("EVM Schedule & Efficiencies", expanded=True):
    planned_duration = st.sidebar.slider("Target Duration (Months)", 12, 36, 24, 1)
    schedule_slippage = st.sidebar.slider("Schedule Slippage (Months)", 0, 12, 3, 1)
    cpi_performance = st.sidebar.slider("Cost Performance Index (CPI)", 0.70, 1.20, 0.90, 0.01)
    spi_performance = st.sidebar.slider("Schedule Performance Index (SPI)", 0.70, 1.20, 0.85, 0.01)
    discount_rate = 0.08

# --- 3. CORE FINANCIAL & FORECAST CALCULATIONS ---
years = np.arange(2026, 2031)
horizon_len = len(years)

projected_grid_prices_mwh = [base_elec_mwh * ((1 + annual_elec_growth) ** i) for i in range(horizon_len)]
projected_grid_prices_kwh = [price / 1000.0 for price in projected_grid_prices_mwh]

annual_good_output_kwh = annual_capacity_gwh * 1000000 * 1000
total_energy_needed_kwh = (annual_good_output_kwh * energy_intensity_kwh) / (1 - scrap_rate)

legacy_opex_mln = [(total_energy_needed_kwh * price) / 1000000.0 for price in projected_grid_prices_kwh]
microgrid_opex_mln = [(total_energy_needed_kwh * price * (1 - grid_offset_pct)) / 1000000.0 for price in projected_grid_prices_kwh]
annual_savings_mln = [leg - mic for leg, mic in zip(legacy_opex_mln, microgrid_opex_mln)]

actual_duration = planned_duration + schedule_slippage
eac_capex_mln = bac_capex_mln / cpi_performance
cost_variance_mln = bac_capex_mln - eac_capex_mln

monthly_energy_waste_mln = annual_savings_mln[1] / 12.0
cost_of_delay_mln = monthly_energy_waste_mln * schedule_slippage

cash_flows = [-eac_capex_mln] + annual_savings_mln
discount_factors = [(1 + discount_rate) ** i for i in range(len(cash_flows))]
dcf = [cf / df for cf, df in zip(cash_flows, discount_factors)]
npv_mln = sum(dcf)

# --- 4. EXECUTIVE METRICS ROW ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("2030 Grid Price Forecast", f"€{projected_grid_prices_mwh[-1]:.0f}/MWh", f"+{annual_elec_growth*100:.0f}% Compounding YoY", delta_color="inverse")
with col2:
    st.metric("Estimate at Completion", f"€{eac_capex_mln:.1f}M", f"Budget Variance: €{cost_variance_mln:.1f}M", delta_color="inverse")
with col3:
    st.metric("Cost of Delay (CoD)", f"€{cost_of_delay_mln:.1f}M Loss", f"{schedule_slippage} Months Late", delta_color="inverse")
with col4:
    st.metric("Microgrid NPV", f"€{npv_mln:.1f}M", "Positive = Viable Project", delta_color="normal" if npv_mln > 0 else "inverse")

st.markdown("<br>", unsafe_allow_html=True)

# --- 5. DATA VISUALIZATIONS (RESPONSIVE TO THEME) ---

st.subheader("I. 5-Year Exponential Grid Exposure vs. Microgrid Protection")
fig_forecast = go.Figure()
fig_forecast.add_trace(go.Scatter(x=years, y=legacy_opex_mln, fill='tozeroy', mode='lines+markers', name='Legacy OPEX (100% Grid)', line=dict(color='#e11d48', width=3)))
fig_forecast.add_trace(go.Scatter(x=years, y=microgrid_opex_mln, fill='tozeroy', mode='lines+markers', name=f'Protected OPEX ({grid_offset_pct*100:.0f}% Offset)', line=dict(color='#059669', width=3)))
fig_forecast.update_layout(height=380, yaxis_title="Annual Energy Cost (€M)", hovermode="x unified", margin=dict(t=20, b=20, l=20, r=20))
# Using Streamlit's native theme engine for Plotly
st.plotly_chart(fig_forecast, use_container_width=True, theme="streamlit")

st.markdown("<br>", unsafe_allow_html=True)

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("II. Execution Health (EVM)")
    time = np.arange(0, actual_duration + 1)
    pv = np.clip((time / planned_duration) * bac_capex_mln, 0, bac_capex_mln)
    ev = np.clip(pv * spi_performance, 0, bac_capex_mln)
    ac = np.clip(ev / cpi_performance, 0, eac_capex_mln)
    
    fig_evm = go.Figure()
    fig_evm.add_trace(go.Scatter(x=time, y=pv, mode='lines', name='Planned Value (PV)', line=dict(color='#64748b', dash='dash')))
    fig_evm.add_trace(go.Scatter(x=time, y=ev, mode='lines+markers', name='Earned Value (EV)', line=dict(color='#0284c7', width=3)))
    fig_evm.add_trace(go.Scatter(x=time, y=ac, mode='lines+markers', name='Actual Cost (AC)', line=dict(color='#d97706', width=3)))
    fig_evm.update_layout(height=350, xaxis_title="Months", yaxis_title="Cost (€M)", margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_evm, use_container_width=True, theme="streamlit")

with col_chart2:
    st.subheader("III. Capex NPV Waterfall")
    cf_labels = ['Capex (Y0)', '2026', '2027', '2028', '2029', '2030']
    fig_npv = go.Figure(go.Waterfall(
        name="Cash Flow", orientation="v", measure=["relative", "relative", "relative", "relative", "relative", "total"],
        x=cf_labels, y=[-eac_capex_mln] + [cf for cf in dcf[1:]],
        decreasing={"marker":{"color":"#e11d48"}}, increasing={"marker":{"color":"#059669"}}, totals={"marker":{"color":"#0284c7"}}
    ))
    fig_npv.update_layout(height=350, yaxis_title="Discounted Flow (€M)", margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_npv, use_container_width=True, theme="streamlit")
