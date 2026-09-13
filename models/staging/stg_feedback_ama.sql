with ranked as (
    select
        *,
        row_number() over (
            partition by feedback_id
            order by created_at desc, event_id, user_id, thumbs
        ) as duplicate_rank
    from {{ ref('raw_feedback_ama') }}
),

deduplicated as (
    select *
    from ranked
    where duplicate_rank = 1
)

select
    cast(feedback_id as varchar) as feedback_id,
    cast(event_id as varchar) as event_id,
    cast(user_id as varchar) as user_id,
    cast(thumbs as integer) as thumbs_raw,
    case when thumbs in (-1, 1) then cast(thumbs as integer) end as thumbs,
    thumbs in (-1, 1) as is_valid_thumbs,
    nullif(lower(trim(cast(reason_tag as varchar))), '') as reason_tag,
    cast(free_text as varchar) as free_text,
    cast(created_at as timestamp) as created_at
from deduplicated
