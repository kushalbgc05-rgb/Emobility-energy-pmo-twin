import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- 1. RESPONSIVE PAGE CONFIGURATION ---
st.set_page_config(page_title="Gigafactory Project and Capex Tracker", layout="wide", initial_sidebar_state="expanded")

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

# --- 2. THE 6 PROJECT & BUSINESS PARAMETERS ---
st.sidebar.header("PMO Control Matrix")

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

# --- 5. DATA VISUALIZATIONS ---
st.subheader("I. 5-Year Exponential Grid Exposure vs. Microgrid Protection")
fig_forecast = go.Figure()
fig_forecast.add_trace(go.Scatter(x=years, y=legacy_opex_mln, fill='tozeroy', mode='lines+markers', name='Legacy OPEX (100% Grid)', line=dict(color='#e11d48', width=3)))
fig_forecast.add_trace(go.Scatter(x=years, y=microgrid_opex_mln, fill='tozeroy', mode='lines+markers', name=f'Protected OPEX ({grid_offset_pct*100:.0f}% Offset)', line=dict(color='#059669', width=3)))
fig_forecast.update_layout(height=380, yaxis_title="Annual Energy Cost (€M)", hovermode="x unified", margin=dict(t=20, b=20, l=20, r=20))
st.plotly_chart(fig_forecast, use_container_width=True, theme="streamlit")

col_bottom1, col_bottom2 = st.columns(2)

with col_bottom1:
    st.subheader("II. Execution Health (EVM)")
    months_arr = np.arange(0, actual_duration + 1)
    
    pv_arr = np.where(months_arr <= planned_duration, (bac_capex_mln / planned_duration) * months_arr, bac_capex_mln)
    ev_arr = (bac_capex_mln / actual_duration) * months_arr
    ac_arr = (eac_capex_mln / actual_duration) * months_arr
    
    fig_evm = go.Figure()
    fig_evm.add_trace(go.Scatter(x=months_arr, y=pv_arr, mode='lines', name='Planned Value (PV)', line=dict(dash='dash', color='gray')))
    fig_evm.add_trace(go.Scatter(x=months_arr, y=ev_arr, mode='lines', name='Earned Value (EV)', line=dict(color='#0284c7')))
    fig_evm.add_trace(go.Scatter(x=months_arr, y=ac_arr, mode='lines', name='Actual Cost (AC)', line=dict(color='#d97706')))
    
    fig_evm.update_layout(height=350, xaxis_title="Months", yaxis_title="Cost (€M)", margin=dict(t=20, b=20, l=20, r=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_evm, use_container_width=True, theme="streamlit")

with col_bottom2:
    st.subheader("III. Capex NPV Waterfall")
    waterfall_labels = ["Initial Capex"] + [str(y) for y in years] + ["Net Present Value"]
    waterfall_measures = ["relative"] + ["relative"] * len(years) + ["total"]
    waterfall_values = dcf + [0]
    
    fig_waterfall = go.Figure(go.Waterfall(
        name="NPV Waterfall", orientation="v",
        measure=waterfall_measures,
        x=waterfall_labels,
        y=waterfall_values,
        decreasing={"marker": {"color": "#e11d48"}},
        increasing={"marker": {"color": "#059669"}},
        totals={"marker": {"color": "#0284c7"}}
    ))
    
    fig_waterfall.update_layout(height=350, yaxis_title="Discounted Cash Flow (€M)", margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_waterfall, use_container_width=True, theme="streamlit")

# --- 6. DATA SOURCES ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📚 Data Sources (Methodology & Baseline Parameters)", expanded=False):
    st.markdown("""
    **1. Grid Rate Inflation & Gigafactory Energy Intensity:**
    > International Energy Agency (IEA). *"Global Supply Chains of EV Batteries."* 
    > <a href="https://www.iea.org/reports/global-supply-chains-of-ev-batteries" class="reference-link" target="_blank">IEA Official Report</a>
    <br><span style="font-size: 0.85em; color: gray;"><i>(Validates the extreme energy intensity of battery manufacturing—specifically the ~45 kWh of electricity required per 1 kWh of cell capacity—and models the operational risk of global grid price inflation).</i></span>

    <br>

    **2. Microgrid OPEX Reduction & NPV Optimization:**
    > National Renewable Energy Laboratory (NREL) / US Department of Energy. *"REopt®: Renewable Energy Integration & Optimization."*
    > <a href="https://reopt.nrel.gov/" class="reference-link" target="_blank">NREL REopt Platform</a>
    <br><span style="font-size: 0.85em; color: gray;"><i>(The industry-standard techno-economic modeling platform used to validate how industrial microgrids offset legacy grid exposure to generate a positive Net Present Value).</i></span>

    <br>

    **3. Earned Value Management (EVM) Forecasting:**
    > National Aeronautics and Space Administration (NASA). *"Earned Value Management (EVM) Implementation Handbook."*
    > <a href="https://www.nasa.gov/ocfo/ppc-corner/evm/" class="reference-link" target="_blank">NASA EVM Central</a>
    <br><span style="font-size: 0.85em; color: gray;"><i>(Validates the strict mathematical formulas used for the Cost Performance Index (CPI), Schedule Performance Index (SPI), and Estimate at Completion (EAC) required for gigafactory capital scaling).</i></span>
    """, unsafe_allow_html=True)
