with anchor as (
    select
        max(event_date) as dataset_anchor_date,
        cast(date_trunc('week', max(event_date)) as date) as anchor_week
    from {{ ref('int_ama_events_enriched') }}
),

weekly as (
    select
        e.week_start,
        cast(e.week_start + interval '6 days' as date) as week_end,
        a.dataset_anchor_date,
        cast(e.week_start + interval '6 days' as date) <= a.dataset_anchor_date as is_calendar_complete_week,
        count(*) as event_count,
        sum(e.valid_feedback_count) as valid_feedback_count,
        sum(e.positive_feedback_count) as positive_feedback_count,
        sum(e.critical_issue_count) as critical_issue_count,
        count(e.response_latency_ms) as valid_latency_count,
        sum(case when e.response_latency_ms <= 5000 then 1 else 0 end) as latency_slo_event_count,
        sum(case when e.valid_feedback_count > 0 then 1 else 0 end) / count(*)::double as feedback_coverage,
        sum(e.positive_feedback_count) / nullif(sum(e.valid_feedback_count), 0)::double as positive_feedback_rate,
        1 - sum(e.critical_issue_count) / nullif(sum(e.valid_feedback_count), 0)::double as critical_issue_avoidance_rate,
        sum(case when e.response_latency_ms <= 5000 then 1 else 0 end) / nullif(count(e.response_latency_ms), 0)::double as latency_slo_rate,
        sum(case when e.retrieved_chunks > 0 then 1 else 0 end) / count(*)::double as retrieval_coverage
    from {{ ref('int_ama_events_enriched') }} e
    cross join anchor a
    where e.week_start between a.anchor_week - interval '7 weeks' and a.anchor_week
    group by e.week_start, a.dataset_anchor_date
)

select
    *,
    100 * (
        0.50 * positive_feedback_rate
        + 0.30 * critical_issue_avoidance_rate
        + 0.20 * latency_slo_rate
    ) as ama_quality_score
from weekly
