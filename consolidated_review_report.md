# Consolidated EGM Design Review

## Outcome

All five requested stages completed, using nine fresh-context reviewer runs. The design is understandable, but not yet fully implementation-ready under EGM's zero-decision standard. No reviewer labeled a finding Blocker. Major findings still prevent calling the review clean. This report does not overrule the author's approved goals or silently accept reviewer proposals.

The immediate normalization feature needs two decisions before code: its exact input/output/error contract and its minimal Python packaging/model setup. Later-feature gaps should be resolved before those features, rather than expanding the first coding task to solve the entire application.

No design changes, application code, paid requests, model downloads, or implementation tests occurred during this review. No convergence is claimed: this was the requested uninterrupted report-only pass, not repeated remediation rounds.

## Scope and provenance

- Target: [approved design](docs/designs/clinical-trial-criteria-explorer.md), 336 lines.
- Reviewed SHA256: 846EFBC44BE29497D0FE97031BF2685FBBD50F2EDA67417D5BC360645F49F7F5.
- FeatureRange: 1–207. DetailedRange: 208–336, discovered at the implementation header.
- Mode: consolidated report, selected by the author.
- Additional baseline: [discussion_summary.md](discussion_summary.md), the only existing local document linked by the target.
- Baseline SHA256 at review: 5C83AB40DF03C1BA7198A911DEC086509076D688B5F09BBC10AE0C07CD9C4F74.
- External links excluded at the author's instruction: https://faiss.ai/, https://www.sqlite.org/whentouse.html, https://docs.langchain.com/oss/python/langgraph/persistence. Their contents were not re-fetched or used as reviewer context.
- Stage 6 used the target alone, plus its reviewer persona; no baseline or earlier reports.
- Stage 8 also read the generated Stage 5–7 reports, as required by the pipeline.
- Personas and standards came from installed EGM 0.1.1. These are review instructions, not extra project evidence.
- Each reviewer was spawned with fork_turns=none. This excludes parent conversation turns; isolation from host-injected instruction files has not been independently verified. Reviewers were told not to retrieve project history or instruction-referenced extra documents.
- Source inventory/search was permitted for reuse/current-state checks. The codebase reviewer additionally read .gitignore as configuration; other extra project documents were not read.

## Stage completion

- Stage 5, initial zoom out: completed, /root/egm_initial_zoom. [Report](zoom_out_report.md).
- Stage 6, comprehension: completed, /root/egm_comprehension. No findings; complete paraphrase preserved in [report](comprehension_report.md).
- Stage 7, design/structure/style: all three completed, /root/egm_design_critic, /root/egm_structural, /root/egm_feature_style. [Report](critic_report.md).
- Stage 8, intermediate zoom out: completed, /root/egm_intermediate_zoom. Confirmed unchanged issues; no newly applied mitigations. [Report](intermediate_zoom_out_report.md).
- Stage 9, readiness/codebase/style: all three completed, /root/egm_readiness, /root/egm_codebase, /root/egm_implementation_style. [Report](implementation_readiness_report.md). Style completed its omitted predecessor read on follow-up; no reviewer remains not-run.

## Consolidated action list and traceability

The raw reports contain 19 finding instances: 17 Major and 2 Nit. Repeated instances across stages are not independent defects. The 14 actions below preserve all raw IDs; I9-5 spans both the metric mismatch and retrieval configuration. These are proposed actions, not applied fixes or accepted risks.

### R01 — Major — Define the first record's contract before implementation

Sources: I9-1, K9-1. Target lines 226–230, 238. Applies immediately to feature 1.

Specify exact API input paths; Study field types/nullability; treatment of missing, null and empty criteria; timestamp representation; NCT syntax; source URL construction; malformed-input exception/result semantics; and concrete expected examples. Checking the source mapping belongs before normalization, not only before ingestion. This is a small contract-writing task, not a reason to implement the source API client first.

### R02 — Major — Choose the minimal first-feature environment

Source: I9-2. Lines 226, 316–317. Applies immediately to feature 1.

Select the supported Python range, packaging backend, record representation, and required development dependencies so the install/test commands are executable. Keep later ML/service dependencies out until needed. Present defensible choices to the author under EGM rather than silently selecting them during coding.

### R03 — Major — State the bounds of collection-wide answers

Sources: D7-1, Z8-2. Lines 56, 115–119, 135. Resolve before retrieval/answers.

Recommended proposal: describe sample-wide results as bounded evidence matches, disclose the result limit and reviewed scope, and prohibit exhaustive claims. An individual-study absence check cannot prove that every matching study in the sample has been found. Exhaustive enumeration would require a separate, explicitly scoped operation.

### R04 — Major — Use one search-result unit and matching metric

Sources: D7-2, Z8-3, metric portion of I9-5. Lines 34, 115, 158, 258–272.

Choose between passage results with study IDs and study-grouped results. The simpler proposal is passage results, with passage recall@5 explicitly defined. If studies remain the promised unit, define grouping and ranking and a study-level evaluation. Do not report one metric as proof of the other behavior.

### R05 — Major — Defer answer caching until evidence supports it

Sources: Z5-1, Z8-1. Lines 152, 298–300. Resolve before persistence/API answer-cache work.

Proposed scope reduction: retain request telemetry and remove persistent generated-answer caching from the first version. Reconsider it after measuring repeated-question cost or latency. This changes an approved requirement, so it requires an author decision before editing the design.

### R06 — Major — Define snapshot selection and partial-failure rules

Source: I9-3. Lines 238–244. Resolve before feature 2.

Specify the actual query, ordering, usable-record criteria, stop rule, snapshot-ID formula, manifest fields, retries and partial-fetch persistence/completeness behavior. Make incomplete datasets inspectable without labeling them complete.

### R07 — Major — Make passage and storage contracts deterministic

Source: I9-4. Lines 248–254. Resolve before feature 3.

Provide criterion-boundary and nested-context examples, source offsets, passage-ID formula, SQLite tables/keys, transaction/conflict behavior and schema-version handling. Equivalent inputs should not generate incompatible evidence identifiers across reasonable implementations.

### R08 — Major — Specify retrieval configuration and evaluation-case schema

Source: remaining portions of I9-5. Lines 258–272. Resolve before features 4–5.

Specify tokenizer/scoring configuration, tie order, allowed filters, fusion constant and candidate depths. Include query text in each evaluation case and define the metric equation, case aggregation and exclusions. Coordinate metric changes with R04; do not count that shared issue twice.

### R09 — Major — Define adapter, fake, state, and budget transitions

Sources: I9-6, K9-2. Lines 276–292. Resolve before features 6–7.

Specify provider-independent request/response/claim/tool/state shapes, deterministic fake-adapter sequencing, failures and unknown usage, and explicitly create tests/fakes.py. Define graph/model-call defaults, unknown-tool behavior and terminal outcomes. Define atomic reservation/reconciliation rules for concurrent requests sharing a session cap. Provider choice and prices may remain a separate author gate; they do not fill these offline contracts.

### R10 — Major — Finish observable API and CLI contracts

Source: I9-7. Lines 296–300, 321. Resolve before each affected interface is implemented.

Define request/response examples, defaults, filters, pagination, session lifecycle, HTTP error codes, input bounds and command flags. CLI syntax is needed when it first appears in ingestion, not only at the API milestone.

### R11 — Major — Separate candidate screening from final embedding selection

Source: T9-1. Line 268. Resolve before model sampling/downloads.

Specify metadata and compatibility screening, a bounded candidate download/benchmark, and then final model selection. The current instruction requires a measured sample before the download needed to obtain it.

### R12 — Major, qualified — Record the actual rationale for selecting B

Source: S7-1. Lines 184–192. Decision-documentation issue, not a prerequisite for pure normalization mechanics.

The reviewer correctly identifies that the record contains a preference without a separately stated engineering rationale. Ask the author for that rationale or propose one clearly for confirmation; do not invent it or claim measured local-model failure.

Orchestrator qualification: the standard's link requirement refers specifically to attributing rejection to a maintainer. The design attributes an explicit decision to its own author and durably records that decision in the predecessor. A public issue/PR link should not be demanded solely to validate this author instruction. This qualification is not an accepted resolution of the underlying missing-rationale finding.

### R13 — Nit — Calibrate response-validation wording

Source: T7-1. Line 144.

Replace ambiguous "claims when verified" with claims passing the defined schema and citation checks. Those checks establish provenance/structure, not semantic or clinical correctness.

### R14 — Nit — Refresh file-action labels after finalization

Source: K9-3. Lines 276, 284, 310.

The design sitemap now exists: modify it if needed. Explicitly create the not-yet-existing model-decision record at its prerequisite step. These labels drifted when this plan was finalized; they are not missing-implementation defects.

## Suggested resolution order

First resolve R01 and R02 and record the resulting small feature contract. Address R12 when confirming the next architecture rationale. Settle R03–R05 before retrieval-related implementation so result semantics and scope are stable. Refine later contracts just before the corresponding approved feature; preserve the author's prediction, exercise, and next-feature approval gates.

The next workflow is EGM Resolve: evaluate each finding, propose edits or contest it with evidence, obtain the required author decision, and apply approved document repairs. Running this review does not authorize implementing or silently changing a feature. Any re-audit must be recorded separately against the resulting design revision.
