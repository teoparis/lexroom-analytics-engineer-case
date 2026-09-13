with feedback_by_event as (
    select
        event_id,
        count(*) as feedback_record_count,
        count(thumbs) as valid_feedback_count,
        sum(case when thumbs = 1 then 1 else 0 end) as positive_feedback_count,
        sum(case when thumbs = -1 then 1 else 0 end) as negative_feedback_count,
        sum(case when thumbs is not null and reason_tag in ('wrong_answer', 'hallucination') then 1 else 0 end) as critical_issue_count,
        sum(case when thumbs is not null and reason_tag = 'wrong_answer' then 1 else 0 end) as wrong_answer_count,
        sum(case when thumbs is not null and reason_tag = 'hallucination' then 1 else 0 end) as hallucination_count
    from {{ ref('stg_feedback_ama') }}
    group by event_id
)

select
    e.event_id,
    e.user_id,
    e.workspace_id,
    e.module_tag_raw,
    e.module_tag,
    e.response_latency_ms_raw,
    e.response_latency_ms,
    e.is_valid_latency,
    e.response_tokens,
    e.retrieved_chunks,
    e.is_cached,
    e.created_at,
    e.event_date,
    cast(date_trunc('week', e.event_date) as date) as week_start,
    coalesce(f.feedback_record_count, 0) as feedback_record_count,
    coalesce(f.valid_feedback_count, 0) as valid_feedback_count,
    coalesce(f.positive_feedback_count, 0) as positive_feedback_count,
    coalesce(f.negative_feedback_count, 0) as negative_feedback_count,
    coalesce(f.critical_issue_count, 0) as critical_issue_count,
    coalesce(f.wrong_answer_count, 0) as wrong_answer_count,
    coalesce(f.hallucination_count, 0) as hallucination_count,
    u.user_role,
    u.created_at as user_created_at,
    u.is_deleted as is_deleted_user,
    w.country,
    w.plan,
    w.firm_size_bucket,
    w.signup_date,
    u.user_id is null as is_missing_user,
    w.workspace_id is null as is_missing_workspace,
    e.created_at < u.created_at as is_before_user_created_at,
    e.event_date < w.signup_date as is_before_workspace_signup
from {{ ref('stg_events_ama') }} e
left join feedback_by_event f using (event_id)
left join {{ ref('stg_users') }} u using (user_id)
left join {{ ref('stg_workspaces') }} w on e.workspace_id = w.workspace_id
