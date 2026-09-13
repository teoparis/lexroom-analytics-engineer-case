select
    'event_feedback_counts' as failure,
    event_id as grain_1,
    null as grain_2
from {{ ref('int_ama_events_enriched') }}
where valid_feedback_count <> positive_feedback_count + negative_feedback_count
   or critical_issue_count <> wrong_answer_count + hallucination_count
   or critical_issue_count > valid_feedback_count
   or least(
        feedback_record_count,
        valid_feedback_count,
        positive_feedback_count,
        negative_feedback_count,
        critical_issue_count,
        wrong_answer_count,
        hallucination_count
   ) < 0

union all

select
    'module_week_feedback_counts',
    cast(week_start as varchar),
    module_tag
from {{ ref('mart_ama_module_weekly') }}
where valid_feedback_count <> positive_feedback_count + negative_feedback_count
   or critical_issue_count <> wrong_answer_count + hallucination_count
   or critical_issue_count > valid_feedback_count
