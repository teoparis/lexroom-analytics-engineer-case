{{ config(severity='warn') }}

select event_id, response_latency_ms_raw
from {{ ref('stg_events_ama') }}
where response_latency_ms_raw < 0
