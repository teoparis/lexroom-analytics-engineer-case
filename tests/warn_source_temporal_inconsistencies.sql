{{ config(severity='warn') }}

select event_id, is_before_user_created_at, is_before_workspace_signup
from {{ ref('int_ama_events_enriched') }}
where is_before_user_created_at or is_before_workspace_signup
