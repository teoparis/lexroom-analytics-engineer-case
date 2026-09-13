{{ config(severity='warn') }}

select f.feedback_id, f.event_id
from {{ ref('stg_feedback_ama') }} f
left join {{ ref('stg_events_ama') }} e using (event_id)
where e.event_id is null
