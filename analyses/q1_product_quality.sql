select *
from {{ ref('mart_ama_module_weekly') }}
order by module_tag, week_start;
