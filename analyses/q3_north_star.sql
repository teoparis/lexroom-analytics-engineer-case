select
    week_start, ama_quality_score, event_count, valid_feedback_count,
    feedback_coverage, positive_feedback_rate,
    critical_issue_avoidance_rate, latency_slo_rate
from {{ ref('mart_ama_quality_weekly') }}
order by week_start;
