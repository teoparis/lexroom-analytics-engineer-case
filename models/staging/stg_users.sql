select
    cast(user_id as varchar) as user_id,
    cast(workspace_id as varchar) as workspace_id,
    lower(trim(cast(role as varchar))) as user_role,
    cast(created_at as timestamp) as created_at,
    cast(is_deleted as boolean) as is_deleted
from {{ ref('raw_users') }}
