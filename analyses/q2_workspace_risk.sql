select
    workspace_id, risk_score, risk_confidence,
    satisfaction_deterioration, performance_deterioration,
    relative_engagement_deterioration, plan, country
from {{ ref('mart_workspace_health') }}
where risk_score is not null
order by risk_score desc, risk_confidence, workspace_id;
