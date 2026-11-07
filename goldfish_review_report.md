# Goldfish Annotated Review Report

Status: resolved

**Target:** [approved design](docs/designs/clinical-trial-criteria-explorer.md), full file, original lines1–336.

**Resolution state:** fourteen proposed corrections accepted and applied; one contested subclaim skipped; no remaining unaddressed consolidated actions. **Date:** 2026-11-08.

**Original SHA256:** 846EFBC44BE29497D0FE97031BF2685FBBD50F2EDA67417D5BC360645F49F7F5.

The author requested EGM Resolve for all findings. This report addresses all fourteen consolidated actions and traces all nineteen raw findings. It proposes fourteen fixes and contests only the unsupported maintainer-link interpretation within R12. No item is declined or escalated. Proposed routine choices are concrete so the author can approve one complete batch. Actual embedding/model/provider selection, resource budgets, and paid spending remain the previously agreed future gates; no such amount or model is invented here.

The complete resulting document is the [proposed design](docs/designs/clinical-trial-criteria-explorer.proposed.md). Its C01–C10 sections contain the exact types, formulas, state transitions and examples; the same contracts are available separately in [proposed implementation contracts](resolution_contracts.proposed.md). The proposed design contains twenty replacements in the existing text plus those detailed contracts. The author accepted that exact candidate with "auto accept". Its corrections are now applied to the approved target; candidate files retain their original proposal wording as historical records.

## Prioritized Findings and AI Suggestions

### R01 — First-record contract [implementation-readiness, codebase-details] — Major

- **Affected scope:** original lines226–230,238; feature1 normalization. Raw I9-1,K9-1.
- **Discrepancy:** the Study field list omits exact field types/nullability, source paths, identifiers, timestamp representation and malformed-input behavior; source verification follows normalization instead of preceding it.
- **Rationale:** independent implementations would choose incompatible boundary behavior and tests. There is no existing code to supply the missing contract.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** the current official ClinicalTrials.gov OpenAPI confirms the source paths and full source-update date. Strict preservation can be specified before making any dataset request.
- **Proposed Edit:** in feature1 replace "Read only documented source fields ..." with the C01 mapping/error contract. C01 fixes the function signature, frozen Study representation, exact NCT syntax, five source paths, datetime-to-UTC ingestion timestamp, explicit missing/null/empty/present criteria state, unknown-status handling, source URL, deterministic validation order and StudyNormalizationError codes. It includes synthetic expected results. Check source schema before feature1 rather than deferring the mapping to feature2.

### R02 — Minimal first-feature environment [implementation-readiness] — Major

- **Affected scope:** original lines226,316–317; raw I9-2.
- **Discrepancy:** Python support, backend, model representation and initial dependencies were left for the implementer to choose.
- **Rationale:** the stated editable-install/test commands do not yet identify a concrete package setup.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** use the already detected Python3.12 and standard-library records so the first lesson needs no ML/validation framework. This is a proposed author-confirmable setup, not a claim of tested compatibility.
- **Proposed Edit:** reference C02 in the pyproject task: Python>=3.12,<3.13; setuptools.build_meta with setuptools>=77,<85; src/trial_explorer; version0.1.0; no feature1 runtime dependency; pytest>=8.3,<10 in dev; importlib test mode; explicit normalization checks with frozen dataclasses. Record resolved versions when installing. C02 explains Pydantic/raw-dictionary alternatives and the cost of manual boundary validation.

### R03 — Bounds of collection-wide answers [design, zoom-out] — Major

- **Affected scope:** original lines56,115–119,135; raw D7-1,Z8-2.
- **Discrepancy:** a question asks for each matching study while retrieval returns at most five passages, and the individual-study absence rule does not establish collection completeness.
- **Rationale:** apparently complete answers could omit valid matches despite having correct citations for displayed results.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** bounded search fits the approved first-version scope without adding exhaustive registry enumeration.
- **Proposed Edit:** rewrite starter question4 to request up to five matching passages. C03 requires result_unit=passage, exhaustive=false, snapshot, filters, permitted scope and counts, with the explicit display "These passages match the query in the stored sample; this result is not exhaustive." Prohibit collection-wide absence/completeness claims; preserve full-record review for an individual selected study.

### R04 — Result unit and evaluation metric [design, zoom-out, readiness] — Major

- **Affected scope:** original lines34,115,158,258–272; raw D7-2,Z8-3 and metric portion of I9-5.
- **Discrepancy:** G2 promises ranked studies, while retrieval and recall@5 operate on passages, without study grouping/ranking.
- **Rationale:** five passages can all come from one study; a passage metric is not evidence of study coverage.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** one consistent passage contract is smaller and already matches the planned indexes and evidence IDs.
- **Proposed Edit:** change G2 to at most five ranked original-source passages with study IDs. C03 explicitly permits multiple passages per study. C06 defines per-check distinct-passage recall@5, macro averaging, comparison-side checks, exclusions and N/A behavior. No study-ranking claim remains.

### R05 — Premature answer caching [zoom-out] — Major

- **Affected scope:** original lines152,298–300; raw Z5-1,Z8-1.
- **Discrepancy:** persistent answer caching, invalidation and session-sensitive keys are required before costs or latency have been measured.
- **Rationale:** this adds state/correctness obligations without a demonstrated repeated-query need.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** removing this feature narrows the release without dropping the intended retrieval, session, cost, and observability lessons. It is a scope change to apply only after the EGM batch decision.
- **Proposed Edit:** delete the successful-answer-cache requirement and its invalidation tests. C10/C07 retain raw snapshots, vector indexes, checkpoints, sessions, dispatch ledger and redacted telemetry. Do not enable model-node caching. Terminal results are persisted only to prevent replay of the same request; a new question does not reuse an old generated answer. Reconsider answer caching after measurements.

### R06 — Snapshot selection and partial failures [readiness] — Major

- **Affected scope:** original lines238–244; raw I9-3.
- **Discrepancy:** query/order, usable-record criteria, stopping rule, manifest schema, IDs and partial-fetch persistence are unspecified.
- **Rationale:** sample membership and the meaning of completeness would differ between implementations.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** official API sorting supports date/numeric fields, not NCTId; a frozen candidate window and local ID ordering produce reproducibility from saved records without claiming a future live query returns the same data.
- **Proposed Edit:** C04 specifies query.cond=type 2 diabetes, JSON Markdown, LastUpdatePostDate:desc, pageSize50, at most four successful pages, token handling including empty pages, strict normalization, deterministic duplicate resolution, local NCT-order selection of50, complete versus partial manifests, UUID4 IDs, atomic manifest finalization, canonical JSON/hash rules, timeouts/retries and non-importable partial runs. Actual selected count/target_met remain visible.

### R07 — Deterministic passages and storage [readiness] — Major

- **Affected scope:** original lines248–254; raw I9-4.
- **Discrepancy:** criterion boundaries, nested grouping, IDs, tables, conflict and version semantics permit incompatible implementations.
- **Rationale:** evidence IDs and quoted offsets must be reproducible before evaluation can depend on them.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** paragraph-v1 deliberately groups lists conservatively and supplies the whole parent section to preserve qualifiers. It does not pretend to interpret clinical logic.
- **Proposed Edit:** C05 fixes heading/block rules, original Unicode offsets, section parent context, exact source slices, versioned passage-ID formula, search_text=text, required SQLite columns/keys/checks/FKs, one-transaction import, verified idempotence, and empty-database initialization/version errors. The documentation's synthetic nested-list offsets were checked; no application test was run.

### R08 — Retrieval configuration and evaluation schema [readiness] — Major

- **Affected scope:** original lines258–272; raw nonmetric portions of I9-5; coordinate with R04.
- **Discrepancy:** BM25/tokenization, ties, filters, fusion configuration and a literal query field are undefined.
- **Rationale:** rankings and scores could change silently and test labels cannot drive reproducible queries.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** define baseline defaults and equations, then measure their quality. No metric result or optimality is assumed.
- **Proposed Edit:** C03 specifies shared nct_ids/recruitment_statuses filters. C06 specifies lexical-v1 tokenizer, BM25 k1=1.2/b=.75/positive-IDF formula, stable ties, exact normalized FAISS IndexFlatIP over permitted vectors, per-retriever depth20, RRF60/final5, JSONL query/scope/evidence schema, strict label validation and distinct real/synthetic aggregates. It defines citation validity separately from manually assessed claim fidelity. Keyword mode works directly from SQLite before vector setup.

### R09 — Adapter, fake, state and budget interfaces [readiness, codebase] — Major

- **Affected scope:** original lines276–292; raw I9-6,K9-2.
- **Discrepancy:** offline adapter/fake schemas, state transitions, call/step limits and atomic spending behavior are missing despite a deferred provider decision.
- **Rationale:** deterministic control-flow tests need a concrete contract independent of which model is eventually selected.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** provider choice can remain gated while application interfaces and failure behavior are defined now. Checkpoints can replay work, so the dispatch ledger must protect against an unintended second paid call.
- **Proposed Edit:** C07 specifies typed request/reply/usage/failure unions, per-study answer groups, claim bounds, three read-only tools, one tool request per reply, complete-source markers, ScriptedModelAdapter expectations/clock/usage/errors, node transitions, max3 tool executions/max4 model attempts with one transient retry/max16 application entries/30s deadline, persisted expiry, session exclusion, SQLite reservations and conditional dispatch, idempotent reconciliation and unknown usage. Explicitly Create tests/fakes.py. Neither a cap amount nor a model is selected.

### R10 — Observable API and CLI contracts [readiness] — Major

- **Affected scope:** original lines296–300,321 and earlier CLI tasks; raw I9-7.
- **Discrepancy:** endpoint/command names exist without request/response schemas, pagination, bounds, lifecycle, HTTP errors and flags.
- **Rationale:** integration tests otherwise need to invent externally observable behavior.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** simple offset pagination and explicit snapshot IDs fit the local single-learner application without adding endpoints or authentication scope.
- **Proposed Edit:** C08 fixes four endpoint bodies/responses, shared filters, question length2000, study limit20/max50/offset, session UUID creation/reuse and snapshot conflicts, per-study comparison statuses, exact HTTP mapping and CLI syntax/exit codes. Keyword search/evaluation need no embedding config; vector building cannot silently download a model. Generation failures remain explicit HTTP failures with source evidence when available.

### R11 — Candidate screening versus final embedding selection [implementation style] — Major

- **Affected scope:** original line268; raw T9-1.
- **Discrepancy:** the plan asks for a measured sample before permitting the download needed to measure it.
- **Rationale:** this circular prerequisite prevents a learner from knowing which experiment is authorized.
- **AI Suggestion:** PROPOSE FIX.
- **Justification:** staged candidate permission differs from final selection, consistent with the author's budget/resource constraints.
- **Proposed Edit:** replace the circular sentence with C09's ordered metadata screening, author-approved bounded candidate download/sample, measured development evidence, and final model/revision decision before full indexing. Failed sampling does not authorize another candidate; held-out labels do not guide selection.

### R12 — Engineering rationale for B [structural] — Major, qualified

- **Affected scope:** original lines184–192; raw S7-1.
- **Discrepancy:** the document records "B is better" and trade-offs but lacks an expressly adopted project-level rationale.
- **Rationale:** a future reader should understand the reason for the selected direction without treating unmeasured hardware/quality claims as facts.
- **AI Suggestion:** PROPOSE FIX for rationale; CONTEST only the demand for an upstream issue/PR link to validate the author's own explicit choice.
- **Justification:** the Alternatives Rule prohibits unsupported attribution to a maintainer, not recording this author's documented preference. The predecessor already records that preference. Proposing a current rationale for confirmation is appropriate; inventing the author's earlier motive is not.
- **Proposed Edit:** replace the decision paragraph with decision history plus C10's proposed current rationale: keep retrieval/evaluation lessons independent of local generation setup and inference performance, while explicitly accepting hosted credentials/network/cost obligations. It remains a proposal for the present decision, not a fabricated historical reason or measured rejection of local inference.

### R13 — Calibrate validation wording [feature style] — Nit

- **Affected scope:** original line144; raw T7-1.
- **Discrepancy:** "claims when verified" can imply that meaning was verified, despite the separate fidelity limitation.
- **Rationale:** provenance/schema checks cannot establish clinical or semantic correctness.
- **AI Suggestion:** PROPOSE FIX.
- **Proposed Edit:** use "claims passing response-structure and citation checks" and explicitly state that these checks do not establish semantic or clinical fidelity. C07 defines that limit consistently.

### R14 — File-action drift [codebase-details] — Nit

- **Affected scope:** original lines276,284,310; raw K9-3.
- **Discrepancy:** an existing sitemap is marked Create; the future model-decision file lacks an explicit Create action.
- **Rationale:** action labels must match the actual repository state after finalization.
- **AI Suggestion:** PROPOSE FIX.
- **Proposed Edit:** Modify the existing finalized design/sitemap; Create docs/model_decisions.md at first screening and Modify it as evidence/choices become available. Preserve past review reports. C10 and the candidate milestone edits supply the exact actions.

## Completeness and application boundary

All nineteen raw finding IDs are mapped above: Z5-1; D7-1,D7-2,S7-1,T7-1; Z8-1,Z8-2,Z8-3; I9-1 through I9-7; K9-1 through K9-3; T9-1. Stage6 had no finding. Duplicates share an action; I9-5 spans R04 and R08.

Three research agents supplied read-only source/schema, retrieval/evaluation and service-boundary proposals. The primary EGM resolver selected and integrated the proposed defaults. A second consistency check corrected canonical hashing, search-text ownership, SQL nullability/version0 handling, per-study response statuses, deadline/recovery state, idempotent accounting and keyword-before-vector operation. This is proposal verification, not an isolated EGM re-audit or proof of implementation correctness.

The pre-resolution design hash is retained above; the post-resolution hash is recorded below. All fourteen proposed corrections are now applied after the author's batch acceptance. No paid call or model download occurred, and no implementation feature or test was started. Proposal references are in the candidate's final References section; app defaults are labeled separately from verified library/API facts.

## EGM application decision and exit record

The author replied "auto accept" on 2026-11-08. All fourteen PROPOSE FIX actions were applied in one batch. The contested maintainer/public-link subclaim in R12 was skipped; its rationale correction was accepted. Accepted fixes: 14. Contested subclaims: 1. Escalated: 0. Declined: 0. Remaining unaddressed consolidated actions: 0.

The finalized design and retained working draft were synchronized. Historical reviewer reports, the complete proposed design, and its separate contract artifact are preserved as review inputs/history. The recorded original line ranges identify the earlier reviewed revision; they are not current line references.

This is document-resolution completion, not an independent post-resolution audit, convergence, measured implementation correctness, or authorization to implement every feature. Model/provider choices and paid caps remain their explicit future prerequisites. The author's incremental learning gates remain in force.

**Applied design SHA256:** D461EE9936B50F908F6414AD83EC88E06ADCD31AB9B9026C7D49C97FAED081D5
