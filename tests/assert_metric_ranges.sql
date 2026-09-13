select 'module_positive_feedback_rate' as failure, week_start::varchar as grain_1, module_tag as grain_2
from {{ ref('mart_ama_module_weekly') }}
where positive_feedback_rate not between 0 and 1

union all

select 'module_critical_issue_rate', week_start::varchar, module_tag
from {{ ref('mart_ama_module_weekly') }}
where critical_issue_rate not between 0 and 1

union all

select 'module_latency_slo_rate', week_start::varchar, module_tag
from {{ ref('mart_ama_module_weekly') }}
where latency_slo_rate not between 0 and 1

union all

select 'weekly_quality_score', week_start::varchar, null
from {{ ref('mart_ama_quality_weekly') }}
where ama_quality_score not between 0 and 100

union all

select 'workspace_risk_score', workspace_id, null
from {{ ref('mart_workspace_health') }}
where risk_score not between 0 and 100
