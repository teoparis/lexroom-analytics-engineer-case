{{ config(severity='warn') }}

select feedback_id, thumbs_raw
from {{ ref('stg_feedback_ama') }}
where not is_valid_thumbs
