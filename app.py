"""Business Analytics Dashboard — Fixed & Improved Streamlit Application."""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ==============================================================================
# 1. PAGE SETUP & CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Business Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Business Analytics & Operations Dashboard")
st.markdown("---")

FILE_NAME = "Race 6-2026.csv"

# ==============================================================================
# 2. DATA LOADING (WITH CACHING FOR PERFORMANCE)
# ==============================================================================
@st.cache_data
def load_data(file_path: str) -> pd.DataFrame:
    """Load and clean the business analytics dataset from a CSV file."""
    try:
        raw = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(
            f"❌ Could not find **'{file_path}'**. "
            "Please ensure the data file is in the same directory as this script."
        )
        return pd.DataFrame()

    # Normalise column names: strip leading/trailing whitespace
    raw.columns = raw.columns.str.strip()

    # Clean wager column
    raw["wager"] = pd.to_numeric(
        raw["wager"].astype(str).str.replace(",", "").str.replace('"', ""),
        errors="coerce",
    )

    # Parse date
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")

    return raw


df_raw = load_data(FILE_NAME)

if df_raw.empty:
    st.stop()

# Work on a clean copy so we never mutate the cached dataframe
df = df_raw.copy()

# Identify product / race columns (everything that isn't metadata)
META_COLS = {"Date", "wager", "Total players of race 6"}
product_cols = [c for c in df.columns if c not in META_COLS]

# ==============================================================================
# 3. SIDEBAR — FILTERS
# ==============================================================================
with st.sidebar:
    st.header("🔍 Filters")

    date_min = df["Date"].min()
    date_max = df["Date"].max()

    if pd.notna(date_min) and pd.notna(date_max):
        date_range = st.date_input(
            "Date range",
            value=(date_min.date(), date_max.date()),
            min_value=date_min.date(),
            max_value=date_max.date(),
        )
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
            df = df[(df["Date"] >= start) & (df["Date"] <= end)]

    if product_cols:
        selected_products = st.multiselect(
            "Products to display",
            options=product_cols,
            default=product_cols,
        )
    else:
        selected_products = []

# Drop rows missing critical columns then sort
df_plot = df.dropna(subset=["Date", "wager"]).sort_values("Date")

# ==============================================================================
# 4. KPI SUMMARY CARDS
# ==============================================================================
total_wager    = df_plot["wager"].sum()
avg_wager      = df_plot["wager"].mean()
peak_wager     = df_plot["wager"].max()
total_players  = (
    df["Total players of race 6"].sum()
    if "Total players of race 6" in df.columns
    else None
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total Wager",   f"{total_wager:,.0f}")
k2.metric("📈 Avg Daily Wager", f"{avg_wager:,.0f}")
k3.metric("🏆 Peak Wager",    f"{peak_wager:,.0f}")
if total_players is not None:
    k4.metric("👥 Total Players (Race 6)", f"{int(total_players):,}")

st.markdown("---")

# ==============================================================================
# 5. SHARED CHART LAYOUT
# ==============================================================================
BASE_LAYOUT = dict(
    template="plotly_white",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=45, b=20),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=True, gridcolor="#e2e8f0", gridwidth=1),
)

# ==============================================================================
# 6. TOP ROW — TWO CHARTS SIDE BY SIDE
# ==============================================================================
col1, col2 = st.columns(2)

# --- Chart 1: Total Wagers Over Time ---
with col1:
    st.subheader("Total Wagers Over Time")
    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(
            x=df_plot["Date"],
            y=df_plot["wager"],
            mode="lines",
            name="Wager Amount",
            line=dict(color="#2563eb", width=3, shape="spline", smoothing=0.3),
            fill="tozeroy",
            fillcolor="rgba(37, 99, 235, 0.1)",
            hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br><b>Wager:</b> %{y:,.0f}<extra></extra>",
        )
    )
    fig1.update_layout(**BASE_LAYOUT, yaxis_title="Total Wager")
    # FIX: use_container_width replaces the invalid width="stretch"
    st.plotly_chart(fig1, use_container_width=True)

# --- Chart 2: Performance vs. Player Volume ---
with col2:
    st.subheader("Performance vs. Player Volume (Race 6)")
    fig2 = go.Figure()

    players_col = "Total players of race 6"
    if players_col in df.columns:
        fig2.add_trace(
            go.Bar(
                x=df["Date"],
                y=df[players_col],
                name="Total Players",
                marker_color="rgba(16, 185, 129, 0.6)",
                marker_line=dict(color="#10b981", width=1.5),
                hovertemplate="<b>Players:</b> %{y}<extra></extra>",
            )
        )

    if "Race 6" in df.columns:
        fig2.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["Race 6"],
                name="Race 6 Performance",
                mode="lines+markers",
                line=dict(color="#ef4444", width=3, shape="spline"),
                marker=dict(size=6),
                yaxis="y2",
                hovertemplate="<b>Performance:</b> %{y}<extra></extra>",
            )
        )
        # Dual-axis so bars and line scale independently
        fig2.update_layout(
            yaxis2=dict(
                overlaying="y",
                side="right",
                showgrid=False,
                title="Race 6 Performance",
            )
        )

    fig2.update_layout(
        **BASE_LAYOUT,
        yaxis_title="Total Players",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ==============================================================================
# 7. BOTTOM CHART — COMPARATIVE PRODUCT PERFORMANCE
# ==============================================================================
st.subheader("Product Performance Over Time")

if not selected_products:
    st.info("Select at least one product from the sidebar to display this chart.")
else:
    fig3 = go.Figure()
    color_palette = px.colors.qualitative.Prism

    for idx, prod in enumerate(selected_products):
        if prod not in df.columns:
            continue
        is_race_6   = prod.strip() == "Race 6"
        line_color  = "#ef4444" if is_race_6 else color_palette[idx % len(color_palette)]
        line_width  = 4 if is_race_6 else 2

        fig3.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df[prod],
                mode="lines",
                name=prod,
                line=dict(color=line_color, width=line_width, shape="spline", smoothing=1.0),
                hovertemplate=f"<b>{prod}</b>: %{{y}}<extra></extra>",
            )
        )

    fig3.update_layout(
        **BASE_LAYOUT,
        yaxis_title="Performance Metrics",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=500,
    )

    # Range selectors on the bottom chart
    fig3.update_xaxes(
        rangeselector=dict(
            buttons=[
                dict(count=7,  label="1w", step="day",   stepmode="backward"),
                dict(count=1,  label="1m", step="month", stepmode="backward"),
                dict(count=3,  label="3m", step="month", stepmode="backward"),
                dict(step="all", label="All"),
            ]
        ),
        rangeslider=dict(visible=True),
    )

    st.plotly_chart(fig3, use_container_width=True)

# ==============================================================================
# 8. RAW DATA EXPANDER
# ==============================================================================
with st.expander("🗂️ View raw data"):
    st.dataframe(df.style.format({"wager": "{:,.0f}"}), use_container_width=True)