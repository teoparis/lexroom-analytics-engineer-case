# My first 90 days as Lexroom's first Analytics Engineer

## Starting point

My goal would be to make a small number of recurring decisions trustworthy before expanding the analytics stack. The public context makes this urgent: Lexroom announced in September 2026 that it operates in five European markets, serves more than 20,000 law firms and legal professionals, and connects its data-first architecture to more than 13 million legal sources. Expansion across jurisdictions creates both technical scale and semantic risk.

The first principle would be progressive trust. Critical contract failures should stop publication or serve the last known good result. Imperfect source signals should remain visible with an owner and an expected response. The second principle would be semantic scale: BigQuery handles compute, while shared definitions and ownership prevent Product, Customer Success, Sales and Leadership from measuring different versions of adoption and quality.

## Days 0-30: map decisions and establish trust

I would begin with the decisions that already recur. Product needs evidence about adoption and answer quality. Customer Success needs account deterioration with confidence. Sales needs governed adoption proof by segment without mixing contract value into product-quality scores. Leadership needs a stable operating view whose limits remain visible. Engineering needs actionable instrumentation feedback. Legal and AI quality experts need claim-level evidence that reflects jurisdiction and source authority.

I would trace the current flow from product events through Pub/Sub into BigQuery, then profile freshness, late arrivals, identifiers and joins. I would map module labels to jurisdiction and corpus version rather than assume the same label means the same thing in every market. The first metric register would record grain, owner, definition, source, refresh expectation, access class, consumer and change history.

The synthetic case suggests two starting interfaces: AMA quality and workspace experience health. I would validate their usefulness with stakeholders before treating them as governed KPIs. By day 30, I would aim to ship one trusted end-to-end model used in a real review, an initial data-quality register and an agreed contract for the most important AMA event.

## Days 31-60: build the trusted BigQuery layer

I would port the take-home layering to separate BigQuery development and production datasets. The first migration would reconcile a fixed snapshot between DuckDB and BigQuery before adding incremental behavior. This isolates SQL-dialect differences from late-arriving-data policy.

The first marts would protect unique grains, required identifiers, taxonomies, relationships and metric ranges. CI would run source profiling, dbt build, independent metric recomputation and documentation generation. I would agree a small tiered service policy with consumers: for example, a Tier-1 daily mart available by 09:00 CET, warning after a missed refresh, same-day acknowledgement by its owner, and last-known-good serving for recoverable source incidents. The exact thresholds should follow real decision cadence and ingestion behavior, not an invented universal SLA.

I would partner with Engineering on a versioned AMA event contract covering event, workspace and user identifiers, jurisdiction, module taxonomy, UTC and ingestion timestamps, latency semantics, retrieval metadata, model or prompt version, privacy classification and ownership. Existing history could remain imperfect; new contract versions would have an explicit standard.

By day 60, Product, Customer Success and Sales should use governed views in regular decision cadences, while Engineering receives contract failures with enough context to act. Each published metric should have a named owner, a documented change path and test coverage proportionate to the harm caused by a wrong answer.

## Days 61-90: measure legal-AI quality and scale adoption

The case data supports an operational quality proxy based on received feedback, critical reason tags and latency. It cannot prove that a legal claim is supported by a cited source, that the source is current for the jurisdiction, or that the system should have abstained. I would therefore start a measurement ladder rather than overload one score.

The next layer would track grounded-answer behavior: source availability, corpus freshness, citation accessibility, retrieval relevance and abstention. A controlled claim-level sample would then evaluate citation entailment, quotation fidelity, legal authority, jurisdiction and temporal validity. Legal or AI quality experts should own the rubric. Analytics Engineering should own reproducible sampling, lineage, evaluator version and reporting.

Self-service would be audience-specific: Product gets component trends and drill paths; Customer Success gets a confidence-aware workspace queue; Sales gets governed segment adoption without raw sensitive text; Engineering gets contracts, lineage and failing-record samples. I would pair these interfaces with office hours and short metric guides rather than grant direct raw-table access and call it self-service.

I would also establish a lightweight operating model: a weekly Product signal review, a biweekly definition review for changed events or metrics, and a monthly trust review with the CTO and relevant domain leaders. This distributes semantic ownership and prevents the first Analytics Engineer from becoming the only approval path.

Trusted marts could later support internal AI agents. An agent answering which workspaces deteriorated should return the metric version, time window, evidence volume and confidence, and follow the same IAM and privacy constraints as a human analyst.

## Risk controls

The main risks are metric fragmentation across markets, weak event contracts, stale or jurisdictionally incorrect sources, privacy exposure in prompts and feedback text, and trust erosion from overclaiming what a proxy measures. Acquisitions add another risk: superficially similar events may carry different local semantics.

Critical trusted-layer failures should block or preserve the last known good output. Known source defects should warn and route to an owner. Received-feedback rates should always travel with feedback count and coverage because feedback is self-selected. Commercial importance should remain outside experience health so the score keeps one meaning.

## Deliberate exclusions

I would not begin with a catalog rollout, ML churn model, infrastructure rewrite, real-time analytics platform or a new orchestration stack. Partitioning, clustering and incremental models should follow measured BigQuery access and correction patterns. The first 90 days should earn the need for complexity by showing that a small trusted layer changes decisions.

Public context checked 13 September 2026: <a href="https://www.lexroom.ai/en/blog/legal-ai-in-europe-lexroom-enters-france-and-bulgaria-with-its-first-acquisitions">Lexroom European expansion</a> and <a href="https://www.lexroom.ai/blog/la-citabilita-il-vero-problema-irrisolto-dellai-nel-diritto">Lexroom on citability</a>.
