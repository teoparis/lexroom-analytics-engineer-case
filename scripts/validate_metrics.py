"""Independently recompute the core dbt metrics with pandas.

The resulting JSON is both an audit receipt and the source for generated
walkthrough evidence. It deliberately does not import dbt SQL or dashboard
helpers, so agreement is an independent check rather than a second call to the
same implementation.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"
OUTPUT = ROOT / "docs" / "metric_validation.json"
Z_95 = 1.959963984540054
MODULE_REPLACEMENTS = {"civil": "civile"}


def safe_rate(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else float(numerator) / float(denominator)


def assert_close(label: str, actual: float, expected: float) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-9):
        raise AssertionError(f"{label}: dbt={actual}, pandas={expected}")


def assert_nullable_close(label: str, actual: float, expected: float | None) -> None:
    if expected is None:
        if not pd.isna(actual):
            raise AssertionError(f"{label}: dbt={actual}, pandas=null")
        return
    if pd.isna(actual):
        raise AssertionError(f"{label}: dbt=null, pandas={expected}")
    assert_close(label, actual, expected)


def json_number(value: float | int | None, digits: int = 6) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, int):
        return value
    return round(float(value), digits)


def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float | None, float | None]:
    """Wilson score interval for one binomial proportion."""
    if total <= 0:
        return None, None
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = (proportion + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def newcombe_difference_interval(
    recent_successes: int,
    recent_total: int,
    previous_successes: int,
    previous_total: int,
) -> tuple[float | None, float | None]:
    """Newcombe-Wilson 95% interval for recent minus previous proportions."""
    if recent_total <= 0 or previous_total <= 0:
        return None, None
    recent_rate = recent_successes / recent_total
    previous_rate = previous_successes / previous_total
    recent_low, recent_high = wilson_interval(recent_successes, recent_total)
    previous_low, previous_high = wilson_interval(previous_successes, previous_total)
    delta = recent_rate - previous_rate
    lower = delta - math.sqrt((recent_rate - recent_low) ** 2 + (previous_high - previous_rate) ** 2)
    upper = delta + math.sqrt((recent_high - recent_rate) ** 2 + (previous_rate - previous_low) ** 2)
    return max(-1.0, lower), min(1.0, upper)


def prepare_events() -> tuple[pd.DataFrame, pd.DataFrame]:
    events = pd.read_csv(SEEDS / "raw_events_ama.csv")
    feedback = pd.read_csv(SEEDS / "raw_feedback_ama.csv")
    events["created_at"] = pd.to_datetime(events["created_at"], utc=True, format="mixed")
    feedback["created_at"] = pd.to_datetime(feedback["created_at"], utc=True, format="mixed")
    events = events.sort_values(["event_id", "created_at"]).drop_duplicates("event_id", keep="last")
    feedback = feedback.sort_values(["feedback_id", "created_at"]).drop_duplicates("feedback_id", keep="last")

    events["module_tag"] = (
        events["module_tag"].astype(str).str.strip().str.lower().replace(MODULE_REPLACEMENTS)
    )
    events["latency_clean"] = events["response_latency_ms"].where(events["response_latency_ms"] >= 0)
    events["event_date"] = events["created_at"].dt.floor("D")
    events["week_start"] = events["event_date"] - pd.to_timedelta(events["event_date"].dt.weekday, unit="D")
    feedback["thumbs_clean"] = feedback["thumbs"].where(feedback["thumbs"].isin([-1, 1]))
    feedback["reason_clean"] = feedback["reason_tag"].str.strip().str.lower()
    feedback["positive"] = (feedback["thumbs_clean"] == 1).astype(int)
    feedback["negative"] = (feedback["thumbs_clean"] == -1).astype(int)
    feedback["critical"] = (
        feedback["thumbs_clean"].notna()
        & feedback["reason_clean"].isin(["wrong_answer", "hallucination"])
    ).astype(int)
    feedback["wrong_answer"] = (
        feedback["thumbs_clean"].notna() & (feedback["reason_clean"] == "wrong_answer")
    ).astype(int)
    feedback["hallucination"] = (
        feedback["thumbs_clean"].notna() & (feedback["reason_clean"] == "hallucination")
    ).astype(int)

    feedback_agg = feedback.groupby("event_id", as_index=False).agg(
        feedback_record_count=("feedback_id", "count"),
        valid_feedback_count=("thumbs_clean", "count"),
        positive_feedback_count=("positive", "sum"),
        negative_feedback_count=("negative", "sum"),
        critical_issue_count=("critical", "sum"),
        wrong_answer_count=("wrong_answer", "sum"),
        hallucination_count=("hallucination", "sum"),
    )
    enriched = events.merge(feedback_agg, on="event_id", how="left")
    count_columns = [
        "feedback_record_count", "valid_feedback_count", "positive_feedback_count",
        "negative_feedback_count", "critical_issue_count", "wrong_answer_count",
        "hallucination_count",
    ]
    enriched[count_columns] = enriched[count_columns].fillna(0).astype(int)
    return enriched, pd.read_csv(SEEDS / "raw_workspaces.csv")


def validate_quality(
    enriched: pd.DataFrame,
    dbt_quality: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Timestamp, list[dict[str, object]]]:
    anchor_week = enriched["week_start"].max()
    anchor_date = enriched["event_date"].max()
    windowed = enriched[enriched["week_start"].between(anchor_week - pd.Timedelta(weeks=7), anchor_week)]
    rows = []
    for week, group in windowed.groupby("week_start"):
        feedback_count = int(group["valid_feedback_count"].sum())
        positive_count = int(group["positive_feedback_count"].sum())
        critical_count = int(group["critical_issue_count"].sum())
        valid_latency_count = int(group["latency_clean"].notna().sum())
        latency_slo_count = int((group["latency_clean"] <= 5000).sum())
        positive_rate = safe_rate(positive_count, feedback_count)
        critical_avoidance = 1 - safe_rate(critical_count, feedback_count)
        latency_slo = safe_rate(latency_slo_count, valid_latency_count)
        rows.append({
            "week_start": week.tz_localize(None).date(),
            "week_end": (week + pd.Timedelta(days=6)).tz_localize(None).date(),
            "dataset_anchor_date": anchor_date.tz_localize(None).date(),
            "is_calendar_complete_week": week + pd.Timedelta(days=6) <= anchor_date,
            "event_count": len(group),
            "valid_feedback_count": feedback_count,
            "positive_feedback_count": positive_count,
            "critical_issue_count": critical_count,
            "valid_latency_count": valid_latency_count,
            "latency_slo_event_count": latency_slo_count,
            "feedback_coverage": safe_rate((group["valid_feedback_count"] > 0).sum(), len(group)),
            "positive_feedback_rate": positive_rate,
            "critical_issue_avoidance_rate": critical_avoidance,
            "latency_slo_rate": latency_slo,
            "retrieval_coverage": safe_rate((group["retrieved_chunks"] > 0).sum(), len(group)),
            "ama_quality_score": 100 * (0.50 * positive_rate + 0.30 * critical_avoidance + 0.20 * latency_slo),
        })
    expected = pd.DataFrame(rows).sort_values("week_start").reset_index(drop=True)
    actual = dbt_quality.sort_values("week_start").reset_index(drop=True)
    if len(expected) != len(actual):
        raise AssertionError("Weekly quality row count differs")
    checked_columns = [
        "event_count", "valid_feedback_count", "positive_feedback_count", "critical_issue_count",
        "valid_latency_count", "latency_slo_event_count", "feedback_coverage",
        "positive_feedback_rate", "critical_issue_avoidance_rate", "latency_slo_rate",
        "retrieval_coverage", "ama_quality_score",
    ]
    for index, row in expected.iterrows():
        for column in checked_columns:
            assert_close(f"quality[{index}].{column}", actual.loc[index, column], row[column])
        if bool(actual.loc[index, "is_calendar_complete_week"]) != bool(row["is_calendar_complete_week"]):
            raise AssertionError(f"quality[{index}].is_calendar_complete_week differs")

    trend = [{
        "week_start": str(row.week_start),
        "week_end": str(row.week_end),
        "event_count": int(row.event_count),
        "valid_feedback_count": int(row.valid_feedback_count),
        "feedback_coverage": json_number(row.feedback_coverage),
        "positive_feedback_rate": json_number(row.positive_feedback_rate),
        "critical_issue_avoidance_rate": json_number(row.critical_issue_avoidance_rate),
        "latency_slo_rate": json_number(row.latency_slo_rate),
        "ama_quality_score": json_number(row.ama_quality_score),
    } for row in expected.itertuples(index=False)]
    return expected, anchor_week, trend


def expected_module_week(group: pd.DataFrame) -> dict[str, float | int | None]:
    feedback_count = int(group["valid_feedback_count"].sum())
    positive_count = int(group["positive_feedback_count"].sum())
    negative_count = int(group["negative_feedback_count"].sum())
    critical_count = int(group["critical_issue_count"].sum())
    wrong_count = int(group["wrong_answer_count"].sum())
    hallucination_count = int(group["hallucination_count"].sum())
    valid_latency_count = int(group["latency_clean"].notna().sum())
    latency_slo_count = int((group["latency_clean"] <= 5000).sum())
    return {
        "event_count": len(group),
        "valid_feedback_count": feedback_count,
        "positive_feedback_count": positive_count,
        "negative_feedback_count": negative_count,
        "critical_issue_count": critical_count,
        "wrong_answer_count": wrong_count,
        "hallucination_count": hallucination_count,
        "valid_latency_count": valid_latency_count,
        "latency_slo_event_count": latency_slo_count,
        "feedback_coverage": safe_rate((group["valid_feedback_count"] > 0).sum(), len(group)),
        "positive_feedback_rate": safe_rate(positive_count, feedback_count),
        "negative_feedback_rate": safe_rate(negative_count, feedback_count),
        "critical_issue_rate": safe_rate(critical_count, feedback_count),
        "wrong_answer_rate": safe_rate(wrong_count, feedback_count),
        "hallucination_rate": safe_rate(hallucination_count, feedback_count),
        "p95_latency_ms": group["latency_clean"].dropna().quantile(0.95, interpolation="linear"),
        "latency_slo_rate": safe_rate(latency_slo_count, valid_latency_count),
        "avg_retrieved_chunks": group["retrieved_chunks"].mean(),
        "retrieval_coverage": safe_rate((group["retrieved_chunks"] > 0).sum(), len(group)),
        "cached_share": safe_rate(group["is_cached"].sum(), len(group)),
    }


def validate_modules(
    enriched: pd.DataFrame,
    dbt_modules: pd.DataFrame,
    anchor_week: pd.Timestamp,
) -> tuple[int, list[dict[str, object]]]:
    windowed = enriched[enriched["week_start"].between(anchor_week - pd.Timedelta(weeks=7), anchor_week)].copy()
    actual_frame = dbt_modules.copy()
    actual_frame["week_start"] = pd.to_datetime(actual_frame["week_start"]).dt.date
    actual = actual_frame.set_index(["week_start", "module_tag"])
    checked = 0
    comparison_rows: list[dict[str, object]] = []
    for (week, module), group in windowed.groupby(["week_start", "module_tag"]):
        key = (week.tz_localize(None).date(), module)
        if key not in actual.index:
            raise AssertionError(f"module week missing from dbt output: {key}")
        expected = expected_module_week(group)
        dbt_row = actual.loc[key]
        for column, value in expected.items():
            assert_nullable_close(f"module_week[{key}].{column}", dbt_row[column], value)
        checked += 1
    if checked != len(actual):
        raise AssertionError(f"Module-week row count differs: dbt={len(actual)}, pandas={checked}")

    windowed["comparison_window"] = "recent_4w"
    windowed.loc[windowed["week_start"] <= anchor_week - pd.Timedelta(weeks=4), "comparison_window"] = "previous_4w"
    for module, group in windowed.groupby("module_tag"):
        period_values = {}
        for period in ("previous_4w", "recent_4w"):
            period_group = group[group["comparison_window"] == period]
            valid_feedback = int(period_group["valid_feedback_count"].sum())
            positive_feedback = int(period_group["positive_feedback_count"].sum())
            critical_feedback = int(period_group["critical_issue_count"].sum())
            period_values[period] = {
                "event_count": len(period_group),
                "valid_feedback_count": valid_feedback,
                "positive_feedback_count": positive_feedback,
                "critical_issue_count": critical_feedback,
                "positive_feedback_rate": safe_rate(positive_feedback, valid_feedback),
                "critical_issue_rate": safe_rate(critical_feedback, valid_feedback),
            }
        previous = period_values["previous_4w"]
        recent = period_values["recent_4w"]
        delta = recent["positive_feedback_rate"] - previous["positive_feedback_rate"]
        ci_low, ci_high = newcombe_difference_interval(
            recent["positive_feedback_count"], recent["valid_feedback_count"],
            previous["positive_feedback_count"], previous["valid_feedback_count"],
        )
        critical_delta = recent["critical_issue_rate"] - previous["critical_issue_rate"]
        comparison_rows.append({
            "module_tag": module,
            "previous_event_count": previous["event_count"],
            "recent_event_count": recent["event_count"],
            "previous_valid_feedback_count": previous["valid_feedback_count"],
            "recent_valid_feedback_count": recent["valid_feedback_count"],
            "previous_positive_feedback_rate": json_number(previous["positive_feedback_rate"]),
            "recent_positive_feedback_rate": json_number(recent["positive_feedback_rate"]),
            "positive_rate_change_pp": json_number(100 * delta, 3),
            "positive_rate_change_95ci_pp": [json_number(100 * ci_low, 3), json_number(100 * ci_high, 3)],
            "critical_issue_rate_change_pp": json_number(100 * critical_delta, 3),
            "evidence_interpretation": "supported deterioration" if ci_high < 0 else "directional only",
        })
    comparison_rows.sort(key=lambda row: row["positive_rate_change_pp"])
    return checked, comparison_rows


def validate_health(
    enriched: pd.DataFrame,
    workspaces: pd.DataFrame,
    dbt_health: pd.DataFrame,
    anchor_week: pd.Timestamp,
) -> tuple[int, int, list[dict[str, object]], dict[str, int]]:
    periods = {
        "recent": (anchor_week - pd.Timedelta(weeks=3), anchor_week),
        "previous": (anchor_week - pd.Timedelta(weeks=7), anchor_week - pd.Timedelta(weeks=4)),
    }
    platform_events = {
        name: len(enriched[enriched["week_start"].between(*bounds)])
        for name, bounds in periods.items()
    }
    actual = dbt_health.set_index("workspace_id")
    expected_rows: list[dict[str, object]] = []
    for workspace_id in workspaces["workspace_id"]:
        metrics: dict[str, float | int | None] = {}
        for name, bounds in periods.items():
            group = enriched[
                (enriched["workspace_id"] == workspace_id)
                & enriched["week_start"].between(*bounds)
            ]
            feedback_count = int(group["valid_feedback_count"].sum())
            event_count = len(group)
            metrics[f"{name}_event_count"] = event_count
            metrics[f"{name}_valid_feedback_count"] = feedback_count
            metrics[f"{name}_positive"] = safe_rate(group["positive_feedback_count"].sum(), feedback_count)
            metrics[f"{name}_latency"] = safe_rate((group["latency_clean"] <= 5000).sum(), group["latency_clean"].notna().sum())
            metrics[f"{name}_share"] = safe_rate(event_count, platform_events[name])
        sat = None if metrics["recent_positive"] is None or metrics["previous_positive"] is None else max(0, metrics["previous_positive"] - metrics["recent_positive"])
        perf = None if metrics["recent_latency"] is None or metrics["previous_latency"] is None else max(0, metrics["previous_latency"] - metrics["recent_latency"])
        engage = None if not metrics["previous_share"] else max(0, 1 - metrics["recent_share"] / metrics["previous_share"])
        score = None if None in (sat, perf, engage) else 100 * (0.50 * sat + 0.30 * perf + 0.20 * engage)
        if metrics["recent_valid_feedback_count"] >= 10 and metrics["previous_valid_feedback_count"] >= 10 and metrics["recent_event_count"] >= 30 and metrics["previous_event_count"] >= 30:
            confidence = "high"
        elif metrics["recent_valid_feedback_count"] >= 3 and metrics["previous_valid_feedback_count"] >= 3 and metrics["recent_event_count"] >= 10 and metrics["previous_event_count"] >= 10:
            confidence = "medium"
        else:
            confidence = "low"
        expected_rows.append({
            "workspace_id": workspace_id,
            "recent_event_count": metrics["recent_event_count"],
            "previous_event_count": metrics["previous_event_count"],
            "recent_valid_feedback_count": metrics["recent_valid_feedback_count"],
            "previous_valid_feedback_count": metrics["previous_valid_feedback_count"],
            "recent_positive_feedback_rate": metrics["recent_positive"],
            "previous_positive_feedback_rate": metrics["previous_positive"],
            "recent_latency_slo_rate": metrics["recent_latency"],
            "previous_latency_slo_rate": metrics["previous_latency"],
            "satisfaction_deterioration": sat,
            "performance_deterioration": perf,
            "relative_engagement_deterioration": engage,
            "risk_score": score,
            "risk_confidence": confidence,
        })

    numeric_columns = [
        "recent_event_count", "previous_event_count", "recent_valid_feedback_count",
        "previous_valid_feedback_count", "recent_positive_feedback_rate",
        "previous_positive_feedback_rate", "recent_latency_slo_rate",
        "previous_latency_slo_rate", "satisfaction_deterioration",
        "performance_deterioration", "relative_engagement_deterioration", "risk_score",
    ]
    for expected in expected_rows:
        workspace_id = expected["workspace_id"]
        if workspace_id not in actual.index:
            raise AssertionError(f"workspace missing from dbt output: {workspace_id}")
        dbt_row = actual.loc[workspace_id]
        for column in numeric_columns:
            assert_nullable_close(f"health[{workspace_id}].{column}", dbt_row[column], expected[column])
        if dbt_row["risk_confidence"] != expected["risk_confidence"]:
            raise AssertionError(f"health[{workspace_id}].risk_confidence differs")
    if len(expected_rows) != len(actual):
        raise AssertionError(f"Workspace row count differs: dbt={len(actual)}, pandas={len(expected_rows)}")

    supported = [row for row in expected_rows if row["risk_score"] is not None]
    supported.sort(key=lambda row: (-row["risk_score"], row["workspace_id"]))
    top_signals = [{
        "workspace_id": row["workspace_id"],
        "risk_score": json_number(row["risk_score"], 3),
        "risk_confidence": row["risk_confidence"],
        "recent_event_count": row["recent_event_count"],
        "previous_event_count": row["previous_event_count"],
        "recent_valid_feedback_count": row["recent_valid_feedback_count"],
        "previous_valid_feedback_count": row["previous_valid_feedback_count"],
        "satisfaction_deterioration": json_number(row["satisfaction_deterioration"]),
        "performance_deterioration": json_number(row["performance_deterioration"]),
        "relative_engagement_deterioration": json_number(row["relative_engagement_deterioration"]),
    } for row in supported[:12]]
    confidence_counts = pd.Series([row["risk_confidence"] for row in expected_rows]).value_counts().to_dict()
    return len(expected_rows), len(supported), top_signals, {key: int(value) for key, value in confidence_counts.items()}


def main() -> None:
    enriched, workspaces = prepare_events()
    with duckdb.connect(str(ROOT / "lexroom.duckdb"), read_only=True) as connection:
        dbt_quality = connection.sql("select * from mart_ama_quality_weekly").df()
        dbt_modules = connection.sql("select * from mart_ama_module_weekly").df()
        dbt_health = connection.sql("select * from mart_workspace_health").df()

    expected_quality, anchor_week, quality_trend = validate_quality(enriched, dbt_quality)
    module_rows_checked, product_comparison = validate_modules(enriched, dbt_modules, anchor_week)
    workspace_rows_checked, workspace_scores_checked, top_workspaces, confidence_counts = validate_health(
        enriched, workspaces, dbt_health, anchor_week
    )
    anchor_date = enriched["event_date"].max()
    summary = {
        "status": "passed",
        "independent_engine": "pandas",
        "dbt_engine": "DuckDB",
        "methodology": {
            "product_uncertainty": "95% Newcombe-Wilson interval for recent minus previous independent feedback proportions",
            "interpretation": "descriptive; feedback is self-selected and module comparisons are not multiplicity-adjusted",
        },
        "time_window": {
            "dataset_anchor_date": str(anchor_date.date()),
            "anchor_week_start": str(anchor_week.date()),
            "anchor_is_calendar_week_end": bool(anchor_date.weekday() == 6),
            "previous_4w_start": str((anchor_week - pd.Timedelta(weeks=7)).date()),
            "previous_4w_end": str((anchor_week - pd.Timedelta(days=22)).date()),
            "recent_4w_start": str((anchor_week - pd.Timedelta(weeks=3)).date()),
            "recent_4w_end": str((anchor_week + pd.Timedelta(days=6)).date()),
        },
        "checks": {
            "quality_weeks_checked": len(expected_quality),
            "module_week_rows_checked": module_rows_checked,
            "workspace_rows_checked": workspace_rows_checked,
            "workspace_scores_checked": workspace_scores_checked,
        },
        "quality_trend": quality_trend,
        "product_window_comparison": product_comparison,
        "workspace_summary": {
            "risk_confidence_counts": confidence_counts,
            "top_raw_risk_signals": top_workspaces,
        },
    }
    OUTPUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
