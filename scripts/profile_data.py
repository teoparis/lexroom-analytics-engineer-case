"""Reproducible profile of the four supplied Lexroom case CSV files."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"
OUTPUT = ROOT / "docs" / "data_profile.json"
ALLOWED_MODULES = {
    "civile",
    "penale",
    "tributario",
    "lavoro",
    "amministrativo",
    "societario",
}


def read_sources() -> tuple[pd.DataFrame, ...]:
    events = pd.read_csv(SEEDS / "raw_events_ama.csv")
    feedback = pd.read_csv(SEEDS / "raw_feedback_ama.csv")
    users = pd.read_csv(SEEDS / "raw_users.csv")
    workspaces = pd.read_csv(SEEDS / "raw_workspaces.csv")
    for frame, column in ((events, "created_at"), (feedback, "created_at"), (users, "created_at")):
        frame[column] = pd.to_datetime(frame[column], utc=True, format="mixed")
    workspaces["signup_date"] = pd.to_datetime(workspaces["signup_date"], utc=True, format="mixed")
    return events, feedback, users, workspaces


def main() -> None:
    events, feedback, users, workspaces = read_sources()
    events_dedup = events.sort_values(["event_id", "created_at"]).drop_duplicates("event_id", keep="last")
    feedback_dedup = feedback.sort_values(["feedback_id", "created_at"]).drop_duplicates("feedback_id", keep="last")
    modules = events_dedup["module_tag"].str.strip().str.lower().replace({"civil": "civile"})

    event_user = events_dedup.merge(
        users[["user_id", "created_at"]], on="user_id", how="left", suffixes=("_event", "_user")
    )
    event_workspace = events_dedup.merge(
        workspaces[["workspace_id", "signup_date"]], on="workspace_id", how="left"
    )
    feedback_per_event = feedback_dedup[
        feedback_dedup["event_id"].isin(events_dedup["event_id"])
    ].groupby("event_id").size()
    event_duplicate_rows = events[events.duplicated("event_id", keep=False)]
    feedback_duplicate_rows = feedback[feedback.duplicated("feedback_id", keep=False)]
    valid_latency = events_dedup[events_dedup["response_latency_ms"] >= 0]

    def conflicting_duplicate_groups(frame: pd.DataFrame, key: str) -> int:
        return int(sum(
            group.drop(columns=[key]).nunique(dropna=False).max() > 1
            for _, group in frame.groupby(key)
        ))

    profile = {
        "raw_rows": {
            "events": len(events),
            "feedback": len(feedback),
            "users": len(users),
            "workspaces": len(workspaces),
        },
        "unique_rows": {
            "events": events_dedup["event_id"].nunique(),
            "feedback": feedback_dedup["feedback_id"].nunique(),
            "users": users["user_id"].nunique(),
            "workspaces": workspaces["workspace_id"].nunique(),
        },
        "quality_findings": {
            "duplicate_event_rows": int(events.duplicated("event_id").sum()),
            "duplicate_feedback_rows": int(feedback.duplicated("feedback_id").sum()),
            "orphan_feedback_after_dedup": int((~feedback_dedup["event_id"].isin(events_dedup["event_id"])).sum()),
            "invalid_thumbs_after_dedup": int((~feedback_dedup["thumbs"].isin([-1, 1])).sum()),
            "negative_latency_after_dedup": int((events_dedup["response_latency_ms"] < 0).sum()),
            "zero_retrieved_chunks_after_dedup": int((events_dedup["retrieved_chunks"] == 0).sum()),
            "users_with_missing_workspace": int((~users["workspace_id"].isin(workspaces["workspace_id"])).sum()),
            "events_with_missing_workspace": int((~events_dedup["workspace_id"].isin(workspaces["workspace_id"])).sum()),
            "workspaces_with_missing_country": int(workspaces["country"].isna().sum()),
            "events_before_user_created_at": int((event_user["created_at_event"] < event_user["created_at_user"]).sum()),
            "events_before_workspace_signup": int((event_workspace["created_at"] < event_workspace["signup_date"]).sum()),
            "events_with_temporal_warning": int((
                (event_user["created_at_event"] < event_user["created_at_user"])
                | (event_workspace["created_at"] < event_workspace["signup_date"])
            ).sum()),
            "events_with_multiple_feedback": int((feedback_per_event > 1).sum()),
            "conflicting_duplicate_event_groups": conflicting_duplicate_groups(event_duplicate_rows, "event_id"),
            "conflicting_duplicate_feedback_groups": conflicting_duplicate_groups(feedback_duplicate_rows, "feedback_id"),
            "deleted_users": int(users["is_deleted"].sum()),
            "events_from_deleted_users": int(events_dedup["user_id"].isin(
                users.loc[users["is_deleted"], "user_id"]
            ).sum()),
            "unexpected_canonical_modules": sorted(set(modules.dropna()) - ALLOWED_MODULES),
        },
        "latency_diagnostics": {
            "valid_900_second_events": int((valid_latency["response_latency_ms"] == 900_000).sum()),
            "cached_median_ms": float(valid_latency.loc[valid_latency["is_cached"], "response_latency_ms"].median()),
            "non_cached_median_ms": float(valid_latency.loc[~valid_latency["is_cached"], "response_latency_ms"].median()),
        },
        "event_date_range": {
            "min": events_dedup["created_at"].min().isoformat(),
            "max": events_dedup["created_at"].max().isoformat(),
        },
        "raw_module_values": events_dedup["module_tag"].value_counts().sort_index().to_dict(),
        "canonical_module_counts": modules.value_counts().sort_index().to_dict(),
        "thumbs_values": {str(k): int(v) for k, v in feedback_dedup["thumbs"].value_counts().sort_index().items()},
        "reason_tag_values": feedback_dedup["reason_tag"].fillna("<null>").value_counts().to_dict(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(profile, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
