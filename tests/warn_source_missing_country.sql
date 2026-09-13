{{ config(severity='warn') }}

select workspace_id
from {{ ref('raw_workspaces') }}
where country is null or trim(cast(country as varchar)) = ''
