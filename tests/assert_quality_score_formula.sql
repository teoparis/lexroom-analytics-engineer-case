select
    week_start,
    ama_quality_score,
    100 * (
        0.50 * positive_feedback_rate
        + 0.30 * critical_issue_avoidance_rate
        + 0.20 * latency_slo_rate
    ) as expected_quality_score
from {{ ref('mart_ama_quality_weekly') }}
where positive_feedback_rate is null
   or critical_issue_avoidance_rate is null
   or latency_slo_rate is null
   or ama_quality_score is null
   or abs(
        ama_quality_score
        - 100 * (
            0.50 * positive_feedback_rate
            + 0.30 * critical_issue_avoidance_rate
            + 0.20 * latency_slo_rate
        )
   ) > 0.000000001
