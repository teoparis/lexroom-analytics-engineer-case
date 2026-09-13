"""Lexroom AMA Decision Cockpit, backed only by dbt marts."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "lexroom.duckdb"
NAVY = "#01102b"
BLUE = "#1c73e7"
TEAL = "#0f766e"
AMBER = "#d97706"
RED = "#b91c1c"
MUTED = "#57708c"

st.set_page_config(page_title="Lexroom AMA Decision Cockpit", page_icon="L", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f7fbff; }
    [data-testid="stHeader"] { background: rgba(247,251,255,.92); }
    h1, h2, h3 { color: #01102b; letter-spacing: -0.025em; }
    [data-testid="stMetric"] { background: white; border-top: 3px solid #1c73e7; padding: 16px; }
    div[data-baseweb="tab-list"] { gap: 1rem; }
    div[data-baseweb="tab"] { font-weight: 650; }
    .caption-box { background: #edf0fe; border-left: 4px solid #1c73e7; padding: 12px 16px; }
    .proxy-box { background: white; border: 1px solid #cad7e8; padding: 12px 16px; margin-top: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_marts(db_path: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with duckdb.connect(db_path, read_only=True) as connection:
        quality = connection.sql("select * from mart_ama_quality_weekly order by week_start").df()
        modules = connection.sql("select * from mart_ama_module_weekly order by week_start, module_tag").df()
        workspaces = connection.sql("select * from mart_workspace_health order by risk_score desc nulls last").df()
    return quality, modules, workspaces


def pct(value: float | None) -> str:
    return "—" if pd.isna(value) else f"{value:.1%}"


if not DB_PATH.exists():
    st.error("Database non trovato. Esegui `dbt seed` e `dbt build` dalla root del progetto.")
    st.stop()

quality, modules, workspaces = load_marts(str(DB_PATH))
quality["week_start"] = pd.to_datetime(quality["week_start"])
quality["week_end"] = pd.to_datetime(quality["week_end"])
modules["week_start"] = pd.to_datetime(modules["week_start"])
anchor_date = pd.to_datetime(quality["dataset_anchor_date"]).max().date()
first_week = quality["week_start"].min().date()
last_week_end = quality["week_end"].max().date()
calendar_complete = bool(quality["is_calendar_complete_week"].all())

st.title("Lexroom AMA Decision Cockpit")
st.caption(
    f"Static synthetic snapshot · {first_week:%d %b %Y} to {last_week_end:%d %b %Y} · "
    f"data cutoff {anchor_date:%d %b %Y} · calendar boundary complete: {'yes' if calendar_complete else 'no'}"
)

leadership_tab, product_tab, cs_tab = st.tabs(["Leadership", "Product", "Customer Success"])

with leadership_tab:
    latest = quality.iloc[-1]
    first = quality.iloc[0]
    cols = st.columns(4)
    cols[0].metric("AMA Quality Score", f"{latest['ama_quality_score']:.1f}", f"{latest['ama_quality_score'] - first['ama_quality_score']:+.1f} vs first week")
    cols[1].metric("Positive feedback", pct(latest["positive_feedback_rate"]))
    cols[2].metric("Critical issue avoidance", pct(latest["critical_issue_avoidance_rate"]))
    cols[3].metric("Feedback coverage", pct(latest["feedback_coverage"]), f"n={int(latest['valid_feedback_count'])}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=quality["week_start"], y=quality["ama_quality_score"], mode="lines+markers",
        name="AMA Quality Score", line=dict(color=BLUE, width=3), marker=dict(size=8)
    ))
    fig.update_layout(
        title="Overall AMA quality trend", yaxis_title="Score (0–100)", xaxis_title=None,
        yaxis=dict(range=[0, 100]), hovermode="x unified", template="plotly_white", height=390,
        margin=dict(l=20, r=20, t=60, b=20), showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

    component_long = quality.melt(
        id_vars="week_start",
        value_vars=["positive_feedback_rate", "critical_issue_avoidance_rate", "latency_slo_rate"],
        var_name="component", value_name="rate",
    )
    component_long["component"] = component_long["component"].map({
        "positive_feedback_rate": "Positive feedback",
        "critical_issue_avoidance_rate": "Critical issue avoidance",
        "latency_slo_rate": "Latency within 5s",
    })
    component_fig = px.line(
        component_long, x="week_start", y="rate", color="component", markers=True,
        color_discrete_sequence=[TEAL, AMBER, NAVY], title="Score components",
    )
    component_fig.update_layout(
        template="plotly_white", height=350, yaxis_tickformat=".0%", yaxis_range=[0, 1],
        yaxis_title="Rate", xaxis_title=None, legend_title=None,
    )
    st.plotly_chart(component_fig, width="stretch")
    st.markdown(
        f'<div class="caption-box">The final week has only {int(latest["valid_feedback_count"])} valid feedback records and {latest["feedback_coverage"]:.1%} coverage. Treat the sharp score decline as a signal that needs confirmation, not a precise estimate of all-user satisfaction.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="proxy-box"><b>Metric boundary.</b> This operating proxy uses the signals available in the case. It does not test citation entailment, source authority, jurisdictional correctness, corpus freshness or whether AMA should have abstained.</div>',
        unsafe_allow_html=True,
    )

with product_tab:
    metric_labels = {
        "positive_feedback_rate": "Positive feedback rate",
        "critical_issue_rate": "Critical issue rate",
        "latency_slo_rate": "Latency within 5 seconds",
        "feedback_coverage": "Feedback coverage",
    }
    selected_metric = st.selectbox("Weekly metric", list(metric_labels), format_func=metric_labels.get)
    product_fig = px.line(
        modules, x="week_start", y=selected_metric, color="module_tag", markers=True,
        title=f"{metric_labels[selected_metric]} by legal module",
    )
    product_fig.update_layout(
        template="plotly_white", height=450, yaxis_tickformat=".0%", yaxis_range=[0, 1],
        yaxis_title=metric_labels[selected_metric], xaxis_title=None, legend_title="Module",
    )
    st.plotly_chart(product_fig, width="stretch")
    st.caption("Feedback rates describe received valid feedback. Coverage and sample size remain visible because feedback is self-selected.")

    st.subheader("Latest week evidence")
    latest_week = modules["week_start"].max()
    latest_modules = modules[modules["week_start"] == latest_week][[
        "module_tag", "event_count", "valid_feedback_count", "feedback_coverage",
        "positive_feedback_rate", "critical_issue_rate", "p95_latency_ms",
    ]].sort_values(["positive_feedback_rate", "event_count"], ascending=[True, False])
    st.dataframe(
        latest_modules,
        hide_index=True,
        width="stretch",
        column_config={
            "module_tag": "Module",
            "event_count": st.column_config.NumberColumn("Events", format="%d"),
            "valid_feedback_count": st.column_config.NumberColumn("Valid feedback", format="%d"),
            "feedback_coverage": st.column_config.NumberColumn("Coverage", format="percent"),
            "positive_feedback_rate": st.column_config.NumberColumn("Positive", format="percent"),
            "critical_issue_rate": st.column_config.NumberColumn("Critical issues", format="percent"),
            "p95_latency_ms": st.column_config.NumberColumn("P95 latency (ms)", format="%.0f"),
        },
    )
    st.info("Focus: societario and civile have better-supported deterioration signals; civile also has the largest reach. Amministrativo has the sharpest point estimate but much wider uncertainty because only 18 recent valid feedback records are available.")

with cs_tab:
    confidence_counts = workspaces["risk_confidence"].value_counts()
    st.caption(
        f"Evidence levels across 80 known workspaces: {int(confidence_counts.get('high', 0))} high, "
        f"{int(confidence_counts.get('medium', 0))} medium and {int(confidence_counts.get('low', 0))} low confidence."
    )
    f1, f2, f3 = st.columns(3)
    confidence_options = ["high", "medium", "low"]
    selected_confidence = f1.multiselect("Confidence", confidence_options, default=confidence_options)
    selected_plans = f2.multiselect("Plan", sorted(workspaces["plan"].dropna().unique()), default=sorted(workspaces["plan"].dropna().unique()))
    selected_countries = f3.multiselect("Country", sorted(workspaces["country"].dropna().unique()), default=sorted(workspaces["country"].dropna().unique()))
    filtered = workspaces[
        workspaces["risk_confidence"].isin(selected_confidence)
        & workspaces["plan"].isin(selected_plans)
        & workspaces["country"].isin(selected_countries)
    ].copy()
    scored = filtered.dropna(subset=["risk_score"]).sort_values("risk_score", ascending=False)
    top = scored.head(12).sort_values("risk_score")
    risk_colors = top["risk_confidence"].map({"high": RED, "medium": AMBER, "low": MUTED})
    risk_fig = go.Figure(go.Bar(
        x=top["risk_score"], y=top["workspace_id"], orientation="h", marker_color=risk_colors,
        customdata=top[["risk_confidence", "plan", "country", "recent_event_count", "recent_valid_feedback_count"]],
        hovertemplate=(
            "<b>%{y}</b><br>Risk: %{x:.1f}<br>Confidence: %{customdata[0]}"
            "<br>Plan: %{customdata[1]}<br>Country: %{customdata[2]}"
            "<br>Recent events: %{customdata[3]:.0f}<br>Recent feedback: %{customdata[4]:.0f}<extra></extra>"
        ),
    ))
    risk_fig.update_layout(
        template="plotly_white", height=430, xaxis_range=[0, 100], xaxis_title="Risk score", yaxis_title=None,
        title="Highest experience deterioration scores in the selected population", showlegend=False,
    )
    st.plotly_chart(risk_fig, width="stretch")

    queue = scored[[
        "workspace_id", "risk_score", "risk_confidence", "plan", "country", "firm_size_bucket",
        "recent_event_count", "previous_event_count", "recent_valid_feedback_count",
        "satisfaction_deterioration", "performance_deterioration", "relative_engagement_deterioration",
    ]]
    st.dataframe(
        queue,
        hide_index=True,
        width="stretch",
        column_config={
            "workspace_id": "Workspace",
            "risk_score": st.column_config.NumberColumn("Risk", format="%.1f"),
            "risk_confidence": "Confidence",
            "plan": "Plan",
            "country": "Country",
            "firm_size_bucket": "Firm size",
            "recent_event_count": st.column_config.NumberColumn("Recent events", format="%.0f"),
            "previous_event_count": st.column_config.NumberColumn("Previous events", format="%.0f"),
            "recent_valid_feedback_count": st.column_config.NumberColumn("Recent feedback", format="%.0f"),
            "satisfaction_deterioration": st.column_config.NumberColumn("Satisfaction decline", format="percent"),
            "performance_deterioration": st.column_config.NumberColumn("Performance decline", format="percent"),
            "relative_engagement_deterioration": st.column_config.NumberColumn("Relative engagement decline", format="percent"),
        },
    )
    st.caption("Health measures experience deterioration only. Plan and firm size remain separate prioritization context. A missing risk score means at least one comparison component lacks a valid baseline.")
