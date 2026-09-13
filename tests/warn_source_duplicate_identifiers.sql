{{ config(severity='warn') }}

select 'event' as record_type, cast(event_id as varchar) as record_id, count(*) as row_count
from {{ ref('raw_events_ama') }}
group by event_id
having count(*) > 1

union all

select 'feedback', cast(feedback_id as varchar), count(*)
from {{ ref('raw_feedback_ama') }}
group by feedback_id
having count(*) > 1
