select event_id, response_latency_ms
from {{ ref('int_ama_events_enriched') }}
where response_latency_ms < 0
