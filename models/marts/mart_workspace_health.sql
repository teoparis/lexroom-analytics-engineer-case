with anchor as (
    select
        max(event_date) as dataset_anchor_date,
        cast(date_trunc('week', max(event_date)) as date) as anchor_week
    from {{ ref('int_ama_events_enriched') }}
),

event_windows as (
    select
        e.*,
        case
            when e.week_start between a.anchor_week - interval '3 weeks' and a.anchor_week then 'recent_4w'
            when e.week_start between a.anchor_week - interval '7 weeks' and a.anchor_week - interval '4 weeks' then 'previous_4w'
        end as comparison_window
    from {{ ref('int_ama_events_enriched') }} e
    cross join anchor a
    where e.week_start between a.anchor_week - interval '7 weeks' and a.anchor_week
),

platform as (
    select
        sum(case when comparison_window = 'recent_4w' then 1 else 0 end) as recent_platform_events,
        sum(case when comparison_window = 'previous_4w' then 1 else 0 end) as previous_platform_events
    from event_windows
),

workspace_metrics as (
    select
        workspace_id,
        sum(case when comparison_window = 'recent_4w' then 1 else 0 end) as recent_event_count,
        sum(case when comparison_window = 'previous_4w' then 1 else 0 end) as previous_event_count,
        sum(case when comparison_window = 'recent_4w' then valid_feedback_count else 0 end) as recent_valid_feedback_count,
        sum(case when comparison_window = 'previous_4w' then valid_feedback_count else 0 end) as previous_valid_feedback_count,
        sum(case when comparison_window = 'recent_4w' then positive_feedback_count else 0 end)
            / nullif(sum(case when comparison_window = 'recent_4w' then valid_feedback_count else 0 end), 0)::double as recent_positive_feedback_rate,
        sum(case when comparison_window = 'previous_4w' then positive_feedback_count else 0 end)
            / nullif(sum(case when comparison_window = 'previous_4w' then valid_feedback_count else 0 end), 0)::double as previous_positive_feedback_rate,
        sum(case when comparison_window = 'recent_4w' and response_latency_ms <= 5000 then 1 else 0 end)
            / nullif(sum(case when comparison_window = 'recent_4w' and response_latency_ms is not null then 1 else 0 end), 0)::double as recent_latency_slo_rate,
        sum(case when comparison_window = 'previous_4w' and response_latency_ms <= 5000 then 1 else 0 end)
            / nullif(sum(case when comparison_window = 'previous_4w' and response_latency_ms is not null then 1 else 0 end), 0)::double as previous_latency_slo_rate
    from event_windows
    group by workspace_id
),

scored as (
    select
        w.workspace_id,
        w.country,
        w.plan,
        w.firm_size_bucket,
        w.signup_date,
        a.dataset_anchor_date,
        cast(a.anchor_week - interval '7 weeks' as date) as previous_period_start,
        cast(a.anchor_week - interval '22 days' as date) as previous_period_end,
        cast(a.anchor_week - interval '3 weeks' as date) as recent_period_start,
        cast(a.anchor_week + interval '6 days' as date) as recent_period_end,
        coalesce(m.recent_event_count, 0) as recent_event_count,
        coalesce(m.previous_event_count, 0) as previous_event_count,
        coalesce(m.recent_valid_feedback_count, 0) as recent_valid_feedback_count,
        coalesce(m.previous_valid_feedback_count, 0) as previous_valid_feedback_count,
        m.recent_positive_feedback_rate,
        m.previous_positive_feedback_rate,
        m.recent_latency_slo_rate,
        m.previous_latency_slo_rate,
        coalesce(m.recent_event_count, 0) / nullif(p.recent_platform_events, 0)::double as recent_platform_activity_share,
        coalesce(m.previous_event_count, 0) / nullif(p.previous_platform_events, 0)::double as previous_platform_activity_share,
        case
            when m.recent_positive_feedback_rate is not null and m.previous_positive_feedback_rate is not null
                then greatest(0, m.previous_positive_feedback_rate - m.recent_positive_feedback_rate)
        end as satisfaction_deterioration,
        case
            when m.recent_latency_slo_rate is not null and m.previous_latency_slo_rate is not null
                then greatest(0, m.previous_latency_slo_rate - m.recent_latency_slo_rate)
        end as performance_deterioration,
        case
            when coalesce(m.previous_event_count, 0) > 0 and p.previous_platform_events > 0 and p.recent_platform_events > 0
                then greatest(0, 1 - (
                    (coalesce(m.recent_event_count, 0) / p.recent_platform_events::double)
                    / (m.previous_event_count / p.previous_platform_events::double)
                ))
        end as relative_engagement_deterioration
    from {{ ref('stg_workspaces') }} w
    left join workspace_metrics m using (workspace_id)
    cross join platform p
    cross join anchor a
)

select
    *,
    case
        when satisfaction_deterioration is not null
            and performance_deterioration is not null
            and relative_engagement_deterioration is not null
        then 100 * (
            0.50 * satisfaction_deterioration
            + 0.30 * performance_deterioration
            + 0.20 * relative_engagement_deterioration
        )
    end as risk_score,
    case
        when recent_valid_feedback_count >= 10 and previous_valid_feedback_count >= 10
            and recent_event_count >= 30 and previous_event_count >= 30 then 'high'
        when recent_valid_feedback_count >= 3 and previous_valid_feedback_count >= 3
            and recent_event_count >= 10 and previous_event_count >= 10 then 'medium'
        else 'low'
    end as risk_confidence,
    case
        when satisfaction_deterioration is not null
            and performance_deterioration is not null
            and relative_engagement_deterioration is not null then 3
        else (
            case when satisfaction_deterioration is not null then 1 else 0 end
            + case when performance_deterioration is not null then 1 else 0 end
            + case when relative_engagement_deterioration is not null then 1 else 0 end
        )
    end as available_risk_components
from scored
