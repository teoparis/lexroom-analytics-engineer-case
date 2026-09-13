{{ config(severity='warn') }}

select feedback_id, reason_tag
from {{ ref('stg_feedback_ama') }}
where reason_tag is not null
  and reason_tag not in ('wrong_answer', 'hallucination', 'incomplete', 'slow', 'other')
