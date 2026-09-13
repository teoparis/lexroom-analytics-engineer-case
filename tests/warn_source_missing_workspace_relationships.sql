{{ config(severity='warn') }}

select 'user' as record_type, u.user_id as record_id, u.workspace_id
from {{ ref('stg_users') }} u
left join {{ ref('stg_workspaces') }} w using (workspace_id)
where w.workspace_id is null

union all

select 'event', e.event_id, e.workspace_id
from {{ ref('stg_events_ama') }} e
left join {{ ref('stg_workspaces') }} w using (workspace_id)
where w.workspace_id is null
