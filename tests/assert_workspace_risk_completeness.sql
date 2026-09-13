select
    workspace_id,
    available_risk_components,
    risk_score
from {{ ref('mart_workspace_health') }}
where (available_risk_components = 3 and risk_score is null)
   or (available_risk_components < 3 and risk_score is not null)
   or available_risk_components not between 0 and 3
   or (
        risk_score is not null
        and abs(
            risk_score
            - 100 * (
                0.50 * satisfaction_deterioration
                + 0.30 * performance_deterioration
                + 0.20 * relative_engagement_deterioration
            )
        ) > 0.000000001
   )
