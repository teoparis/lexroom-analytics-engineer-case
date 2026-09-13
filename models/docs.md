{% docs stg_events_ama %}
One row per unique AMA answer event. This model standardizes legal-module labels and separates usable latency from the original value: negative latency becomes null for analysis, while the source value remains available for auditing. Events are not discarded simply because a related user or workspace is missing.
{% enddocs %}

{% docs stg_feedback_ama %}
One row per unique feedback submission. Valid thumbs are `1` and `-1`; unexpected values become null without losing the original value. Feedback that points to an unknown event stays visible in staging as a source-quality issue but cannot affect downstream answer-quality metrics.
{% enddocs %}

{% docs stg_users %}
One row per supplied user. The model retains deletion status because a deleted user can still have legitimate historical activity. Missing workspace relationships remain visible rather than being silently invented or removed.
{% enddocs %}

{% docs stg_workspaces %}
One row per supplied workspace. Country, plan and firm-size bucket provide business context. A missing country is exposed as `UNKNOWN` for easier consumption, while the original null is preserved for investigation.
{% enddocs %}

{% docs int_ama_events_enriched %}
One row per AMA event with its user, workspace and aggregated feedback signals. Feedback is aggregated before the join so that multiple feedback records can never duplicate an event. Free-text comments are deliberately excluded from the shared analytical layer.
{% enddocs %}

{% docs mart_ama_module_weekly %}
One row per legal module and reporting week. Product can use it to compare reach, received-feedback quality, critical-issue rate, feedback coverage and latency over the latest eight calendar-complete weeks in the supplied snapshot. The mart supports prioritization, not causal diagnosis.
{% enddocs %}

{% docs mart_workspace_health %}
One row per known workspace. It compares the most recent four weeks with the previous four weeks across satisfaction, latency and relative engagement. The risk score measures deterioration in product experience, not churn probability; confidence remains separate so a large movement with little evidence is not treated as the strongest action signal.
{% enddocs %}

{% docs mart_ama_quality_weekly %}
One row per reporting week. It provides Leadership with a provisional AMA Quality Score and the component metrics needed to interpret it. The score combines received positive feedback, avoidance of critical feedback reasons and compliance with a provisional five-second latency threshold. It does not measure legal correctness or citation validity.
{% enddocs %}

{% docs workspace_risk_score %}
An experience-deterioration score from 0 to 100: 50% satisfaction deterioration, 30% performance deterioration and 20% relative-engagement deterioration. Missing components remain visible, and the accompanying confidence category reflects evidence volume in both comparison windows.
{% enddocs %}

{% docs ama_quality_score %}
A provisional weekly operating score from 0 to 100: 50% positive received-feedback rate, 30% critical-issue avoidance rate and 20% latency-SLO rate. It must always be read with its components, feedback count and feedback coverage.
{% enddocs %}
