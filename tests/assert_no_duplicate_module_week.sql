select week_start, module_tag, count(*) as row_count
from {{ ref('mart_ama_module_weekly') }}
group by week_start, module_tag
having count(*) > 1
