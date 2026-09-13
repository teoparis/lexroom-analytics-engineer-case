with ranked as (
    select
        *,
        row_number() over (
            partition by event_id
            order by created_at desc, user_id, workspace_id, module_tag
        ) as duplicate_rank
    from {{ ref('raw_events_ama') }}
),

deduplicated as (
    select *
    from ranked
    where duplicate_rank = 1
)

select
    cast(event_id as varchar) as event_id,
    cast(user_id as varchar) as user_id,
    cast(workspace_id as varchar) as workspace_id,
    cast(module_tag as varchar) as module_tag_raw,
    case
        when lower(trim(cast(module_tag as varchar))) = 'civil' then 'civile'
        else lower(trim(cast(module_tag as varchar)))
    end as module_tag,
    cast(response_latency_ms as bigint) as response_latency_ms_raw,
    case when response_latency_ms >= 0 then cast(response_latency_ms as bigint) end as response_latency_ms,
    response_latency_ms >= 0 as is_valid_latency,
    cast(response_tokens as bigint) as response_tokens,
    cast(retrieved_chunks as bigint) as retrieved_chunks,
    cast(is_cached as boolean) as is_cached,
    cast(created_at as timestamp) as created_at,
    cast(created_at as date) as event_date
from deduplicated
