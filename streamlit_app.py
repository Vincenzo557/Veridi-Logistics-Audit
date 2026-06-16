"""
Veridi Logistics — Delivery Performance Audit Dashboard
Deploy: streamlit run streamlit_app.py
Cloud:  https://streamlit.io/cloud  (connect GitHub repo, set main file to streamlit_app.py)

All CSV files must be in the same folder as this script (relative paths).
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Veridi Logistics Audit",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stMetric"] { background: #f8fafc; border-radius: 10px; padding: 16px; }
  [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
  .section-header { font-size: 1.3rem; font-weight: 600; color: #1e293b;
                    border-left: 4px solid #6366f1; padding-left: 12px; margin: 24px 0 12px; }
</style>
""", unsafe_allow_html=True)

COLOR_MAP = {"On Time": "#22c55e", "Late": "#f59e0b", "Super Late": "#ef4444"}

# ── DATA LOADING ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    orders    = pd.read_csv("olist_orders_dataset.csv")
    reviews   = pd.read_csv("olist_order_reviews_dataset.csv")
    customers = pd.read_csv("olist_customers_dataset.csv")
    products  = pd.read_csv("olist_products_dataset.csv")
    items     = pd.read_csv("olist_order_items_dataset.csv")
    translate = pd.read_csv("product_category_name_translation.csv")

    # Deduplicate reviews
    reviews["review_creation_date"] = pd.to_datetime(reviews["review_creation_date"])
    reviews_deduped = (
        reviews.sort_values("review_creation_date")
               .drop_duplicates(subset="order_id", keep="first")
    )

    # Master join
    master = (
        orders
        .merge(reviews_deduped[["order_id", "review_score"]], on="order_id", how="left")
        .merge(customers[["customer_id", "customer_state", "customer_city"]], on="customer_id", how="left")
    )

    # Parse dates
    for col in ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]:
        master[col] = pd.to_datetime(master[col])

    # Delivered only
    delivered = master[master["order_status"] == "delivered"].copy()
    delivered = delivered.dropna(subset=["order_delivered_customer_date", "order_estimated_delivery_date"])

    # Delay calc
    delivered["days_difference"] = (
        delivered["order_estimated_delivery_date"] - delivered["order_delivered_customer_date"]
    ).dt.days
    delivered["days_late"] = (-delivered["days_difference"]).clip(lower=0)

    def classify(d):
        if d >= 0:   return "On Time"
        elif d >= -5: return "Late"
        else:         return "Super Late"

    delivered["delivery_status"] = delivered["days_difference"].apply(classify)

    # English categories
    items_cat = (
        items
        .merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
        .merge(translate, on="product_category_name", how="left")
    )
    cat_per_order = items_cat.groupby("order_id")["product_category_name_english"].first().reset_index()
    delivered = delivered.merge(cat_per_order, on="order_id", how="left")

    # Month column for trend
    delivered["purchase_month"] = delivered["order_purchase_timestamp"].dt.to_period("M").astype(str)

    return delivered

# ── LOAD ─────────────────────────────────────────────────────────────────────
with st.spinner("Loading delivery data..."):
    try:
        df = load_data()
        data_loaded = True
    except FileNotFoundError as e:
        data_loaded = False
        missing_file = str(e)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/delivery.png", width=60)
    st.title("Veridi Audit")
    st.markdown("---")

    if data_loaded:
        states = sorted(df["customer_state"].dropna().unique())
        selected_states = st.multiselect("Filter by State", states, default=states)

        categories = sorted(df["product_category_name_english"].dropna().unique())
        selected_cats = st.multiselect("Filter by Category", categories, default=categories)

        st.markdown("---")
        st.caption("Dataset: Olist Brazilian E-Commerce")
        st.caption(f"{len(df):,} delivered orders")

# ── MAIN ─────────────────────────────────────────────────────────────────────
st.title("🚚 Veridi Logistics — Delivery Performance Audit")
st.markdown("*Connecting logistics data with customer sentiment to find the root cause of delivery failures.*")

if not data_loaded:
    st.error(f"⚠️ Could not load data: `{missing_file}`")
    st.info("Place all Olist CSV files in the **same folder** as `streamlit_app.py` and restart.")
    st.stop()

# Apply filters
filtered = df[
    df["customer_state"].isin(selected_states) &
    df["product_category_name_english"].isin(selected_cats)
] if selected_states and selected_cats else df

# ── KPI ROW ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)

total       = len(filtered)
pct_ontime  = (filtered["delivery_status"] == "On Time").mean() * 100
pct_late    = (filtered["delivery_status"] != "On Time").mean() * 100
avg_review  = filtered["review_score"].mean()
median_slack = filtered["days_difference"].median()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Orders",    f"{total:,}")
k2.metric("On-Time Rate",    f"{pct_ontime:.1f}%",   delta=f"{pct_ontime-80:.1f}% vs 80% target")
k3.metric("Late Rate",       f"{pct_late:.1f}%",     delta=f"{-pct_late:.1f}%", delta_color="inverse")
k4.metric("Avg Review Score",f"{avg_review:.2f}/5")
k5.metric("Median ETA Slack",f"{median_slack:+.0f} days")

st.markdown("---")

# ── ROW 1: Status Pie + Review by Status ─────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-header">Delivery Status Breakdown</div>', unsafe_allow_html=True)
    status_counts = filtered["delivery_status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig_pie = px.pie(
        status_counts, names="status", values="count",
        color="status", color_discrete_map=COLOR_MAP,
        hole=0.45,
    )
    fig_pie.update_traces(textinfo="percent+label", textfont_size=13)
    fig_pie.update_layout(height=350, showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown('<div class="section-header">Review Score by Delivery Status</div>', unsafe_allow_html=True)
    rev_by_status = (
        filtered.groupby("delivery_status")["review_score"]
        .mean().reset_index()
        .rename(columns={"review_score": "avg_score"})
    )
    order = ["On Time", "Late", "Super Late"]
    rev_by_status["delivery_status"] = pd.Categorical(rev_by_status["delivery_status"], categories=order, ordered=True)
    rev_by_status = rev_by_status.sort_values("delivery_status")

    fig_bar = px.bar(
        rev_by_status, x="delivery_status", y="avg_score",
        color="delivery_status", color_discrete_map=COLOR_MAP,
        text="avg_score",
        labels={"avg_score": "Avg Score (1–5)", "delivery_status": ""},
    )
    fig_bar.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig_bar.update_layout(
        height=350, yaxis_range=[0, 5.5],
        showlegend=False, plot_bgcolor="white",
        margin=dict(t=10, b=10)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── ROW 2: State Analysis ─────────────────────────────────────────────────────
st.markdown('<div class="section-header">🗺️ Geographic Analysis — Late Deliveries by State</div>', unsafe_allow_html=True)

state_stats = (
    filtered.groupby("customer_state")
    .agg(
        total=("order_id", "count"),
        late=("delivery_status", lambda x: (x != "On Time").sum()),
        avg_review=("review_score", "mean"),
    )
    .reset_index()
)
state_stats["pct_late"] = (state_stats["late"] / state_stats["total"] * 100).round(1)

fig_state = px.bar(
    state_stats.sort_values("pct_late", ascending=False),
    x="customer_state", y="pct_late",
    color="pct_late", color_continuous_scale="RdYlGn_r",
    text="pct_late",
    labels={"pct_late": "% Late", "customer_state": "State"},
    custom_data=["avg_review", "total"]
)
fig_state.update_traces(
    texttemplate="%{text:.1f}%", textposition="outside",
    hovertemplate="<b>%{x}</b><br>% Late: %{y:.1f}%<br>Avg Review: %{customdata[0]:.2f}<br>Orders: %{customdata[1]:,}<extra></extra>"
)
fig_state.update_layout(
    height=420, plot_bgcolor="white",
    coloraxis_showscale=False,
    xaxis_tickangle=-45,
    margin=dict(t=20, b=10)
)
st.plotly_chart(fig_state, use_container_width=True)

# ── ROW 3: Scatter + Trend ───────────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.markdown('<div class="section-header">Days Late vs. Review Score</div>', unsafe_allow_html=True)
    sample = filtered.sample(min(6000, len(filtered)), random_state=42)
    fig_scatter = px.scatter(
        sample, x="days_late", y="review_score",
        color="delivery_status", color_discrete_map=COLOR_MAP,
        opacity=0.2,
        labels={"days_late": "Days Late", "review_score": "Review Score"},
    )
    # Manual average trend line (no statsmodels needed)
    avg_by_day = (
        filtered[filtered["days_late"] <= 30]
        .groupby("days_late")["review_score"].mean()
        .reset_index()
    )
    fig_scatter.add_scatter(
        x=avg_by_day["days_late"], y=avg_by_day["review_score"],
        mode="lines", line=dict(color="#0f172a", width=2.5),
        name="Avg score"
    )
    fig_scatter.update_layout(height=380, plot_bgcolor="white", margin=dict(t=10, b=10))
    st.plotly_chart(fig_scatter, use_container_width=True)

with col4:
    st.markdown('<div class="section-header">Monthly On-Time Rate Trend</div>', unsafe_allow_html=True)
    monthly = (
        filtered.groupby("purchase_month")
        .agg(ontime_rate=("delivery_status", lambda x: (x == "On Time").mean() * 100))
        .reset_index()
        .sort_values("purchase_month")
    )
    fig_trend = px.line(
        monthly, x="purchase_month", y="ontime_rate",
        markers=True,
        labels={"ontime_rate": "On-Time Rate (%)", "purchase_month": "Month"},
    )
    fig_trend.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="80% Target")
    fig_trend.update_layout(
        height=380, plot_bgcolor="white",
        xaxis_tickangle=-45, margin=dict(t=10, b=10)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ── ROW 4: Categories + ETA Bias ─────────────────────────────────────────────
col5, col6 = st.columns(2)

with col5:
    st.markdown('<div class="section-header">📦 Late Rate by Product Category</div>', unsafe_allow_html=True)
    cat_stats = (
        filtered.groupby("product_category_name_english")
        .agg(total=("order_id", "count"), late=("delivery_status", lambda x: (x != "On Time").sum()))
        .reset_index()
    )
    cat_stats["pct_late"] = (cat_stats["late"] / cat_stats["total"] * 100).round(1)
    cat_stats = cat_stats[cat_stats["total"] >= 50].sort_values("pct_late", ascending=False).head(15)

    fig_cat = px.bar(
        cat_stats, x="pct_late", y="product_category_name_english",
        orientation="h", color="pct_late", color_continuous_scale="Reds",
        labels={"pct_late": "% Late", "product_category_name_english": ""},
    )
    fig_cat.update_layout(
        height=430, plot_bgcolor="white",
        coloraxis_showscale=False,
        yaxis={"autorange": "reversed"},
        margin=dict(t=10, b=10)
    )
    st.plotly_chart(fig_cat, use_container_width=True)

with col6:
    st.markdown('<div class="section-header">📐 ETA Bias Distribution (Candidate\'s Choice)</div>', unsafe_allow_html=True)
    fig_hist = px.histogram(
        filtered, x="days_difference", nbins=70,
        color_discrete_sequence=["#6366f1"],
        opacity=0.8,
        labels={"days_difference": "Days Early (+) or Late (−)"},
    )
    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="On-Time Boundary")
    skew = filtered["days_difference"].skew()
    fig_hist.add_annotation(
        x=0.98, y=0.95, xref="paper", yref="paper",
        text=f"Skewness: {skew:.2f}",
        showarrow=False, bgcolor="#fff", bordercolor="#6366f1", borderwidth=1
    )
    fig_hist.update_layout(
        height=430, plot_bgcolor="white",
        margin=dict(t=10, b=10)
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Data: Olist Brazilian E-Commerce Public Dataset (Kaggle) · Built for Veridi Logistics Delivery Audit")
