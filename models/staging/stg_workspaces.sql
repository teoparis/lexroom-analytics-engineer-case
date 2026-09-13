select
    cast(workspace_id as varchar) as workspace_id,
    upper(trim(cast(country as varchar))) as country_raw,
    coalesce(nullif(upper(trim(cast(country as varchar))), ''), 'UNKNOWN') as country,
    lower(trim(cast(plan as varchar))) as plan,
    lower(trim(cast(firm_size_bucket as varchar))) as firm_size_bucket,
    cast(signup_date as date) as signup_date
from {{ ref('raw_workspaces') }}
