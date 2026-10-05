import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- PAGE CONFIGURATION & CSS ---
st.set_page_config(
    page_title="Gigafactory Project and Capex Tracker",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
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
st.markdown(
    "Monitoring gigafactory construction and operational scale-up through Earned Value Management (EVM). "
    "This simulator quantifies Schedule Performance Index (SPI), Cost Performance Index (CPI), and the exact "
    "Cost of Delay (CoD) financial impact when critical path commissioning items slip."
)
st.divider()

# --- SIDEBAR PARAMETERS ---
st.sidebar.header("Project & Capex Parameters")

with st.sidebar.expander("Baseline Master Schedule", expanded=True):
    total_budget_m = st.number_input("Budget at Completion (BAC) [$M]", min_value=50, max_value=5000, value=850, step=50)
    total_duration = st.slider("Planned Project Duration (Months)", 12, 60, 24, 1)
    current_month = st.slider("Current Assessment Month", 1, total_duration, 14, 1)

with st.sidebar.expander("Execution Variance Simulator", expanded=True):
    st.caption("Adjust delays and overruns to simulate cash burn.")
    schedule_delay = st.slider("Schedule Delay (Months)", 0.0, 12.0, 2.5, 0.5)
    cost_overrun_pct = st.slider("Cost Overrun / Variance (%)", -10, 50, 15, 1) / 100.0

with st.sidebar.expander("Cost of Delay (CoD) Metrics", expanded=True):
    st.caption("Financial penalty for delayed start of production (SOP).")
    daily_burn_rate_k = st.number_input("Daily Operational Cash Burn [$k/day]", min_value=10, max_value=1000, value=150, step=10)

# --- EARNED VALUE MANAGEMENT (EVM) ENGINE ---
# Create an S-Curve for Planned Value (PV)
x_months = np.arange(0, total_duration + 1)
# Logistic curve approximation for construction S-Curve
k = 0.3  # Steepness
x0 = total_duration / 2
pv_curve = total_budget_m / (1 + np.exp(-k * (x_months - x0)))
# Normalize so it starts near 0 and ends exactly at total_budget_m
pv_curve = (pv_curve - pv_curve[0]) / (pv_curve[-1] - pv_curve[0]) * total_budget_m

planned_value = pv_curve[current_month]

# Earned Value (EV) reflects the actual progress made, accounting for the delay
effective_month = max(0, current_month - schedule_delay)
# Linearly interpolate the S-Curve to get exact EV
if effective_month == int(effective_month):
    earned_value = pv_curve[int(effective_month)]
else:
    lower_val = pv_curve[int(np.floor(effective_month))]
    upper_val = pv_curve[int(np.ceil(effective_month))]
    earned_value = lower_val + (upper_val - lower_val) * (effective_month % 1)

# Actual Cost (AC) incorporates the cost overrun percentage on the work performed
actual_cost = earned_value * (1.0 + cost_overrun_pct)

# EVM Indices
spi = earned_value / planned_value if planned_value > 0 else 1.0
cpi = earned_value / actual_cost if actual_cost > 0 else 1.0

# Cost of Delay (CoD)
delay_days = schedule_delay * 30
total_cod_m = (delay_days * daily_burn_rate_k) / 1000.0

# --- EXECUTIVE KPIS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Schedule Performance (SPI)", f"{spi:.2f}", "Target: 1.00 (On Time)", delta_color="off")
with col2:
    st.metric("Cost Performance (CPI)", f"{cpi:.2f}", "Target: 1.00 (On Budget)", delta_color="off")
with col3:
    st.metric("Current Earned Value (EV)", f"${earned_value:.1f}M", f"Planned: ${planned_value:.1f}M", delta_color="off")
with col4:
    st.metric("Accumulated Cost of Delay", f"${total_cod_m:.1f}M", f"{int(delay_days)} Days Delayed", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# --- VISUALIZATIONS ---
st.subheader("Earned Value vs. Actual Cost Trajectory (S-Curve)")

# Prepare DataFrame for plotting up to current month
df_evm = pd.DataFrame({
    "Month": x_months[:current_month+1],
    "Planned Value (PV)": pv_curve[:current_month+1]
})

# Calculate EV and AC curves up to current month based on constant delay/overrun
ev_array = []
ac_array = []
for m in x_months[:current_month+1]:
    eff_m = max(0, m - schedule_delay)
    if eff_m == int(eff_m):
        ev_val = pv_curve[int(eff_m)]
    else:
        ev_val = pv_curve[int(np.floor(eff_m))] + (pv_curve[int(np.ceil(eff_m))] - pv_curve[int(np.floor(eff_m))]) * (eff_m % 1)
    ev_array.append(ev_val)
    ac_array.append(ev_val * (1.0 + cost_overrun_pct))

df_evm["Earned Value (EV)"] = ev_array
df_evm["Actual Cost (AC)"] = ac_array

# Create Plotly Graph
fig = go.Figure()

# Plot PV (Full duration as dashed background curve to show the plan)
fig.add_trace(go.Scatter(
    x=x_months, y=pv_curve, mode='lines', name='Baseline Plan (PV)',
    line=dict(color='rgba(128, 128, 128, 0.5)', width=2, dash='dash')
))

# Plot actuals up to current month
fig.add_trace(go.Scatter(
    x=df_evm["Month"], y=df_evm["Planned Value (PV)"], mode='lines+markers', name='Planned Value (PV)',
    line=dict(color='#0284c7', width=3)
))
fig.add_trace(go.Scatter(
    x=df_evm["Month"], y=df_evm["Earned Value (EV)"], mode='lines+markers', name='Earned Value (EV)',
    line=dict(color='#10b981', width=3)
))
fig.add_trace(go.Scatter(
    x=df_evm["Month"], y=df_evm["Actual Cost (AC)"], mode='lines+markers', name='Actual Cost (AC)',
    line=dict(color='#ef4444', width=3)
))

# Add a vertical line for the current month
fig.add_vline(x=current_month, line_width=2, line_dash="dash", line_color="black", annotation_text="Current Month")

fig.update_layout(
    title="Gigafactory Construction Scale-Up: Cost & Schedule Tracking",
    xaxis_title="Timeline (Months)",
    yaxis_title="Capital Expenditure ($ Millions)",
    height=500,
    margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- DATA SOURCES ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("Data Sources", expanded=False):
    st.markdown("""
    **1. Earned Value Management (EVM) Framework:**
    > Project Management Institute (PMI). *"A Guide to the Project Management Body of Knowledge (PMBOK Guide)."* 
    > <a href="https://www.pmi.org/pmbok-guide-standards/foundational/pmbok" class="reference-link" target="_blank">PMI Standards</a>
    <br><span style="font-size: 0.85em; color: gray;"><i>(Validates the mathematical formulas used for the Schedule Performance Index (SPI), Cost Performance Index (CPI), and operational cash burn).</i></span>

    <br>

    **2. Cost of Delay (CoD) & Economic Impact:**
    > Reinertsen, D. G. *"The Principles of Product Development Flow: Second Generation Lean Product Development."* Celeritas Publishing (2009).
    > <a href="https://www.amazon.com/Principles-Product-Development-Flow-Generation/dp/1935401009" class="reference-link" target="_blank">Celeritas</a>
    <br><span style="font-size: 0.85em; color: gray;"><i>(Validates the financial framework for quantifying the Cost of Delay when critical path gigafactory commissioning items slip).</i></span>

    <br>

    **3. Gigafactory CapEx & Operations Baseline:**
    > RWTH Aachen University (PEM). *"Production process of a lithium-ion battery cell: Plant, facility and equipment setup."*
    > <a href="https://www.pem.rwth-aachen.de/go/id/oqqu/" class="reference-link" target="_blank">RWTH Aachen PEM Publications</a>
    <br><span style="font-size: 0.85em; color: gray;"><i>(Validates the baseline capital expenditure, machinery lead times, and energy consumption metrics during battery plant scale-up).</i></span>
    """, unsafe_allow_html=True)
