with anchor as (
    select
        max(event_date) as dataset_anchor_date,
        cast(date_trunc('week', max(event_date)) as date) as anchor_week
    from {{ ref('int_ama_events_enriched') }}
),

windowed as (
    select e.*
    from {{ ref('int_ama_events_enriched') }} e
    cross join anchor a
    where e.week_start between a.anchor_week - interval '7 weeks' and a.anchor_week
)

select
    w.week_start,
    cast(w.week_start + interval '6 days' as date) as week_end,
    a.dataset_anchor_date,
    cast(w.week_start + interval '6 days' as date) <= a.dataset_anchor_date as is_calendar_complete_week,
    w.module_tag,
    count(*) as event_count,
    sum(w.valid_feedback_count) as valid_feedback_count,
    sum(w.positive_feedback_count) as positive_feedback_count,
    sum(w.negative_feedback_count) as negative_feedback_count,
    sum(w.critical_issue_count) as critical_issue_count,
    sum(w.wrong_answer_count) as wrong_answer_count,
    sum(w.hallucination_count) as hallucination_count,
    count(w.response_latency_ms) as valid_latency_count,
    sum(case when w.response_latency_ms <= 5000 then 1 else 0 end) as latency_slo_event_count,
    sum(case when w.valid_feedback_count > 0 then 1 else 0 end) / count(*)::double as feedback_coverage,
    sum(w.positive_feedback_count) / nullif(sum(w.valid_feedback_count), 0)::double as positive_feedback_rate,
    sum(w.negative_feedback_count) / nullif(sum(w.valid_feedback_count), 0)::double as negative_feedback_rate,
    sum(w.critical_issue_count) / nullif(sum(w.valid_feedback_count), 0)::double as critical_issue_rate,
    sum(w.wrong_answer_count) / nullif(sum(w.valid_feedback_count), 0)::double as wrong_answer_rate,
    sum(w.hallucination_count) / nullif(sum(w.valid_feedback_count), 0)::double as hallucination_rate,
    quantile_cont(w.response_latency_ms, 0.95) filter (where w.response_latency_ms is not null) as p95_latency_ms,
    sum(case when w.response_latency_ms <= 5000 then 1 else 0 end) / nullif(count(w.response_latency_ms), 0)::double as latency_slo_rate,
    avg(w.retrieved_chunks) as avg_retrieved_chunks,
    sum(case when w.retrieved_chunks > 0 then 1 else 0 end) / count(*)::double as retrieval_coverage,
    sum(case when w.is_cached then 1 else 0 end) / count(*)::double as cached_share
from windowed w
cross join anchor a
group by w.week_start, a.dataset_anchor_date, w.module_tag
