# Clinical Trial Criteria Explorer

- Author: Yazeed-Jonsh
- Status: Approved by author; EGM resolution applied; no re-audit claimed
- Date: 2026-11-07
- Last revised: 2026-11-08
- Predecessor: [discussion_summary.md](discussion_summary.md)
- EGM stage: resolution complete; incremental implementation handoff

Author approved Overview and Goals in chat: "yes I approve them". This approval covers the reader, the approximately 50-study type 2 diabetes sample, and product boundaries.

The author then selected Option B in chat: "B is better", and approved the completed Technical Plan: "yes I approve it". Local retrieval with hosted generation and the technical contracts below are approved. Live model requests still require a provider/model choice and an agreed spending cap.

The author approved Alternatives Considered in chat: "I approve the approve Alternatives Considered", and Detailed Implementation: "yes I approve the detailed implementation plan". All design sections have author approval. This is not authorization to implement all features in one session.

## Overview

Build a small application that helps a reader find and understand the eligibility criteria recorded for public clinical trials. A reader can search a fixed collection of studies, inspect inclusion and exclusion requirements, ask a question about a selected study, and compare two studies. Each explanation includes the original wording and a link to the study record.

The proposed first reader is a student or researcher exploring trial records. This is a portfolio and learning application. It has not been clinically validated.

The proposed first collection contains about 50 type 2 diabetes studies from ClinicalTrials.gov. The collection is a reproducible sample, not a complete inventory of trials. Show the snapshot date so a reader can distinguish the stored evidence from current information.

## The Problem

Criteria are written as free text and can contain multiple conditions, numeric thresholds, exceptions, and nested requirements. A reader comparing records must repeatedly find the relevant wording and keep the source associated with each statement.

The application will make that evidence easier to locate. Its central failure risk is changing the meaning when explaining a requirement: dropping a negation, changing a threshold, or turning missing information into a fact. Search quality and preservation of meaning must therefore be measured separately.

The strongest alternative is to use ClinicalTrials.gov directly. This project must demonstrate useful evidence retrieval and comparison on a small benchmark rather than claim it improves clinical decision making.

## Goals and observable acceptance criteria

- G1 — Traceable records: every stored study has its NCT ID, source URL, source update date when supplied, retrieval timestamp, and original eligibility text. Missing fields remain explicit.
- G2 — Search: return at most five ranked source passages with study IDs and evidence snippets. Several passages may come from one study; results are non-exhaustive. Passage recall@5 measures passage retrieval, not study coverage (C03/C06). A small labeled question set measures whether relevant evidence appears in the first five results. Set a performance target after measuring the baseline.
- G3 — Faithful explanations: each factual statement about a criterion points to an exact supporting passage. Retain negations, quantities, units, and exceptions. Mark ambiguous statements for review rather than guessing.
- G4 — Comparison: show evidence from each of two selected studies separately. An absent criterion is described as not stated in the stored record.
- G5 — Uncertainty: questions without supporting evidence receive an explicit missing-information response. Every designated unanswerable benchmark case must exercise this behavior before release.
- G6 — Appropriate boundary: participation questions explain that the study team must confirm eligibility. Use public records and fictional test examples.
- G7 — Reproducibility: record the data selection, snapshot date, configuration, and commands needed to reproduce evaluation. Publish actual scores with denominators and a list of observed failures.
- G8 — Learning: for each implemented milestone, the author can explain its purpose, the relevant code path, and one failure case. Record a short explanation in the learning notes.

## Non-Goals

- Deciding an individual's eligibility, recommending treatment, or enrolling participants.
- Collecting real patient records or operating a clinical service.
- Claiming live or comprehensive trial coverage from a saved sample.
- Model fine-tuning, multiple agent frameworks, or large-scale deployment during this first version.

## Five starter evaluation questions

These are question templates, not answered benchmark cases. On Day 2, bind them to actual study IDs and manually verify the expected source passages.

1. What minimum and maximum ages are stated for study A? Preserve units and record any missing limit.
2. What does study A explicitly say about insulin use? Return its wording or state that the record does not answer.
3. How do the stated HbA1c requirements differ between studies A and B? Preserve thresholds, operators, and units.
4. Show up to five passages in this stored sample mentioning kidney-related exclusion criteria. Cite them and disclose that results are not exhaustive; do not infer eligibility.
5. Does study A require a laboratory threshold that its record does not mention? The expected response is missing information.

## Open Questions

- Resolved: the author approved the proposed reader, condition, and sample size with Overview and Goals.
- Verify API access, data selection, and difficult records before promising the complete ten-session scope.
- Resolved: local SQLite, FAISS, BM25, FastAPI, and a bounded LangGraph workflow are the shared foundation of selected Option B.
- Select an embedding model and hosted provider/model after checking compatibility and evaluating a representative workload. Confirm pricing, data handling, credentials, and a spending cap before live model requests.
- Define the evaluation set and how the author will review criteria fidelity. A developer review is not clinical validation.

## Technical Plan — selected Option B

Option B has been selected. Option A remains below as decision history for the later Alternatives section. Exact model and package versions will be checked during implementation; no dependency has been installed.

### Selected foundation

Use Python, a local SQLite database for study metadata and source passages, local text embeddings with a FAISS index for vector retrieval, and BM25 keyword retrieval. Combine ranked results rather than directly adding scores on different scales. Build the keyword baseline before the combined retriever so its effect can be measured.

Keep the original eligibility text and stable passage IDs. Search text may be normalized, but citations must resolve to original source text and the correct study snapshot. Split text at criterion boundaries and retain parent context where a list depends on a heading or exception.

Use a FastAPI service with a /api/v1 prefix and its interactive API documentation for the initial interface. Add a bounded LangGraph workflow with explicitly allowed search, study-detail, and comparison tools after the basic retrieval pipeline works. Save selected study IDs and workflow state per session. Previous generated answers are not evidence for later answers.

Validate structured model responses against permitted evidence IDs. Reject invented IDs, return source wording where a generated explanation cannot be supported, and expose uncertainty. Matching a citation proves that the passage exists, not that the paraphrase is medically faithful; the labeled evaluation must inspect meaning as well.

These components were included in both architecture options. The author selected B and subsequently approved the completed Technical Plan below.

### Previous candidate A — Local retrieval and local generation

Mechanism: download an embedding model and a small text-generation model, then run search and generation on this computer. After initial downloads and data collection, serving the stored sample can work without an external model API. The generation adapter must support explicit tool requests; reject a candidate that cannot pass the tool-calling smoke test.

Trade-offs: no model API usage charges and full local control, but model downloads consume storage and running generation consumes memory and CPU or GPU resources. Small models may struggle with long criteria, negation, or structured tool responses.

Failure conditions: insufficient memory, unacceptable measured latency, inability to perform tool calls reliably, or poor criteria fidelity. Confirm hardware and benchmark a candidate before committing to it. A failure does not silently switch to a paid provider; bring the evidence back for an architecture revision.

### Selected B — Local retrieval with hosted generation

Mechanism: store studies and embeddings locally, retrieve the relevant passages locally, and send only the question and selected public passages to a hosted model. The hosted model returns structured tool requests or an evidence-linked response. Keep the model behind an adapter so data collection and retrieval tests do not require network calls.

Trade-offs: avoids local generation hardware requirements, but adds API credentials, network dependency, provider limits, and usage costs. Quality still requires measurement. Select the provider and model, verify pricing and data handling, and agree on a spending cap before live requests.

Failure conditions: unavailable credentials, exhausted budget, timeouts, rate limits, or failed fidelity tests. Use bounded retries; return retrieved evidence with an explicit generation-unavailable result when the service fails. This fallback is distinct from a generated explanation.

### Selected data flow

ClinicalTrials.gov snapshot -> original source text and metadata -> criterion passages -> keyword and vector indexes -> combined retrieval -> selected evidence -> model adapter -> citation checks -> response.

The generation adapter calls the hosted service. Retrieval and ordinary tests remain local and usable when generation is unavailable.

### Study snapshot and local storage

The ingestion step saves original API responses and a manifest with the query, retrieved NCT IDs, retrieval time, and content hashes. After inspection on Day 2, freeze that manifest for the first evaluation. Refreshing data creates a new snapshot instead of overwriting the evidence used by earlier results. A query yielding fewer than 50 usable studies is reported explicitly rather than filled with unrelated records.

SQLite stores studies and passages keyed by snapshot. Each study retains the original criteria, source URL, source update date when provided, recruitment status, and explicit missing values. Each passage stores its parent criterion/heading, source character offsets, and a stable identifier derived from snapshot, study, and offsets. Normalized search text is separate from original text. Derived comparisons and generated answers never replace source text.

Persist indexes with a manifest containing the snapshot hash, passage ID mapping, embedding model identifier/revision, dimensions, normalization, and chunking configuration. Refuse a mismatched index and require rebuilding it. This prevents the correct-looking citation from pointing to the wrong data after a refresh.

### Retrieval and context assembly

Apply structured study filters before selecting retrieval candidates. Search both the BM25 and vector indexes within that permitted study set. Merge rankings using reciprocal rank fusion, then remove duplicate passages. An initial search returns at most five ranked passages and reports result_unit=passage, exhaustive=false, filters, scope and counts under C03/C06. Comparisons return up to five passages per side; bounded results never establish a complete study list. Treat that limit as an initial configuration to evaluate, not an optimized value.

For a question about a selected study, constrain retrieval to its ID. For a two-study comparison, retrieve evidence independently from each study and preserve the two evidence groups in the prompt. Include the relevant parent criterion and heading so that qualifiers survive chunk boundaries. If context exceeds the configured model budget, reduce the number of complete passages and report the limit; never silently cut a threshold or exception in half.

Return search results as evidence snippets and rankings, not as eligibility scores. A low search score or a missing top-five result does not establish that a criterion is absent from the whole record. Before saying "not stated in this stored record," inspect that study's full stored eligibility text. If it cannot fit within the review budget or remains ambiguous, return "unable to determine from the reviewed evidence" instead.

### Explicit tools and bounded agent state

Expose three read-only application tools: search criteria using a query and validated filters; fetch the original eligibility text for an existing NCT ID in the snapshot; and retrieve evidence for exactly two existing NCT IDs. Tool inputs use validated schemas and result-size limits. The model cannot issue SQL, arbitrary network requests, shell commands, or writes to study records.

Use LangGraph to run request validation, model tool selection, tool execution, answer construction, and response validation. Start with a maximum of three tool executions and a hard graph step limit. All model calls share the same request budget. Stop with the collected evidence and an explicit incomplete result if the limit is reached.

Save a session ID, snapshot ID, selected study IDs, bounded recent conversation, evidence IDs, and workflow checkpoints locally. Sessions must not silently switch snapshots. A follow-up retrieves current evidence from the pinned snapshot; it does not use a previous generated answer as factual support. This first version runs on localhost for one learner; exposing it publicly requires a separate authentication and session-isolation design.

### Hosted adapter, citations, and fallback behavior

The provider-independent adapter accepts the question, selected evidence, tool definitions, and call limits. It returns typed tool requests or structured claims with evidence IDs. Require native tool/function calling and structured-response support from the selected provider/model, then verify both with a small smoke test. Mock responses exercise control flow only; they are not evidence of real model quality.

The application resolves evidence IDs to quotes, source offsets, study URLs, and snapshot dates itself. For every claimed citation, check that the passage belongs to the permitted study and snapshot, and that the displayed quote matches the saved original text. Reject unknown IDs and unsupported output structure. Numeric and negation checks can flag suspicious changes, but cannot prove semantic fidelity. Show the original criterion beside its explanation and include ambiguous paraphrases in manual evaluation.

Distinguish answered, not-stated-in-record, insufficient-reviewed-evidence, generation-unavailable, and review-needed outcomes. With no provider configured, users can search and read exact source passages. Provider errors or validation failures return evidence with an explicit unavailable/unverified explanation state. Do not present source excerpts as a successfully generated answer.

### Initial API contract

- GET /api/v1/studies: list studies and structured filters within the current snapshot.
- GET /api/v1/studies/{nct_id}: return a study's saved original criteria and provenance.
- POST /api/v1/search: query the local indexes without a hosted call.
- POST /api/v1/questions: answer a question, optionally scoped to selected study IDs and a session; comparison uses exactly two selected IDs.

Responses include the snapshot ID/date and source evidence. Question responses add outcome, claims passing response-structure and citation checks, citations, and a request ID. These checks do not establish semantic or clinical fidelity. Reject malformed IDs, unknown studies/snapshots, empty questions, and inputs beyond documented limits. Provider outages are explicit service failures with available source evidence. Interactive API documentation is the first interface; a custom frontend is a later enhancement.

### Cost, privacy, and operational limits

Keep credentials in environment variables excluded from Git. Only public trial excerpts and intended non-sensitive demo questions are sent to the provider. The application is not designed for personal patient narratives; the demo instructs readers to use fictional examples. A text filter cannot guarantee that a user has not entered private information.

Before enabling live generation, record provider/model, model context limit, verified current input/output prices, maximum input/output tokens, request deadline, and a user-agreed session spending cap. Refuse live calls until these are configured. Reserve a conservative upper cost bound before each attempted call, including retries; reconcile reported usage afterward and retain the reservation when usage is unknown. Do not claim an application counter is a provider billing guarantee. Use provider-side limits where available.

Bound retries for transient errors; every retry consumes the request call and cost allowance. Version 1 does not cache generated answers or use LangGraph model-node caching. Keep source snapshots, indexes, sessions, checkpoints and the spending ledger for their separate evidence/execution purposes. Reconsider answer caching only after measured repeated-question cost or latency. Log request IDs, workflow steps, evidence IDs, durations, outcome, model identifier, and token usage when returned. Avoid logging credentials or complete user questions by default.

### Verification tied to product goals

Create source-verified fixtures before writing assertions. Cover offset/citation integrity, missing values, units, negation, exceptions, cross-study evidence leakage, invalid tool arguments, exhausted call budgets, provider failures, and stale indexes with pytest. Use FastAPI integration tests for validation, response schemas, and search availability without credentials. An offline fake hosted adapter supports deterministic CI; live evaluation is an explicit separate command.

Grow the five question templates into a small manually labeled development set and a separate held-out set. Include answerable, absent-information, ambiguous, comparison, and participation questions. Record relevant passage IDs, expected source wording, and expected outcome before tuning. Measure evidence recall at five, correct citations divided by all citations, manually checked claim fidelity, abstention behavior, latency, and cost. Compare keyword-only, vector-only, and combined retrieval on the same snapshot. Publish per-case failures and sample sizes; a small benchmark does not establish clinical safety.

### Critical user journeys

1. Given a frozen sample, a reader searches for a criterion. The application returns ranked source snippets, study IDs, and the snapshot date without requiring hosted credentials.
2. Given a selected study, a reader asks about a threshold. The application retrieves the original criterion and returns a source-linked explanation preserving quantities and exceptions, or an explicit uncertainty outcome.
3. Given two selected studies, a reader compares criteria. The application keeps evidence attributed to each study and handles missing or ambiguous requirements separately.
4. Given unavailable generation or a reached budget, the application explains that generation is unavailable and still offers local evidence. It never labels a failed call as a complete answer.

### Cost and feasibility evidence

- Python 3.12.7 was detected on this machine.
- Windows denied the memory, CPU, and GPU queries. Hardware capacity and local inference performance remain unverified.
- No models, packages, or study records have been downloaded. No costs or latency measurements have been recorded.
- At this sample size the proposed tools serve learning goals; the benchmark must establish whether combined retrieval improves on keyword search.

### Technical references checked during planning

- [FAISS documentation](https://faiss.ai/): vector similarity search, Python wrappers, and CPU installation.
- [SQLite appropriate uses](https://www.sqlite.org/whentouse.html): local application storage and its concurrency trade-offs.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): session checkpoints and state scoped to a thread.

## Alternatives Considered

This section records alternatives from the predecessor discussion. It adds no new architecture decision and makes no claim that quality, speed, or costs have been benchmarked.

### A — Run answer generation locally

Mechanism: retain the local study store and search indexes, and run the answer-generation model on this computer.

Benefits: local control, no per-call hosted generation fee, and operation without an external model service after downloads.

Costs and failure conditions: the model must fit available memory, respond within acceptable measured time, and handle tool calls, thresholds, and negation. Hardware inspection was denied, so local feasibility is unverified. Local execution does not guarantee accurate explanations.

Decision history: the author selected B with "B is better"; no historical motive is invented. Rationale adopted through EGM Resolve: avoid making local generation installation and inference performance a prerequisite for retrieval/evaluation learning. Hosted generation adds credentials, network dependence and usage charges to measure/control. The author accepted this rationale with "auto accept"; it is not proof of local inference failure. The author decision is preserved in the predecessor; no upstream-maintainer rejection is claimed.

### B — Local retrieval with hosted generation (selected)

Mechanism: retrieve public evidence locally and send selected passages with the question to a hosted model. Store source text, metadata, embeddings, and evaluation fixtures locally.

Benefits: avoids running answer generation on the learner's computer. Ingestion and local search can be developed before hosted credentials are configured. Deterministic adapter fakes support ordinary tests while live model quality is measured separately.

Costs and failure conditions: introduces provider availability, credentials, token limits, and usage costs. Hosted models can still misread criteria or produce unsupported explanations. The approved citation checks, original-source display, fidelity evaluation, and request budgets remain necessary. No provider, model, current price, or measured quality advantage has been established.

Revisit this choice if the budget cannot support the workload, provider requirements cannot be met, or the chosen model fails evaluation. Bring measured evidence back to the author before changing the architecture.

### Existing ClinicalTrials.gov interface — product baseline

The predecessor identifies the existing website as the strongest product alternative: a reader can inspect original records without maintaining this application. The learning project adds the planned evidence-linked comparisons and retrieval experiments. Its value must be demonstrated on a benchmark. The author approved building the project; that does not establish that the original website is inadequate or rejected for general use.

## Detailed Implementation Plan

### Execution rules and scope

Implement the milestones below sequentially. A milestone may take several short sessions; ten one-hour sessions remain an effort target, not a delivery guarantee. Complete one feature's explanation, code, author prediction, tests, review, and exercise before requesting permission for the next feature. Approval of this document does not waive those feature boundaries.

Before writing code, explain the feature's purpose, input/output shape, data flow, prerequisites, and one trade-off. After writing its tests, ask the author to predict an important outcome and wait before running them. Explain any failure with a hint before supplying a complete fix to the author's exercise. Record the attempt and measured result without writing the exercise solution in advance.

Use the package name trial_explorer under src/. Test files sit under tests/. The paths below are relative to this repository. All source and test paths are planned creations; only documentation is being modified during EGM drafting. No existing files are scheduled for deletion.

### Unified file and feature list

#### 1. Normalize one trial record — first coding feature

Purpose: transform a single API-shaped dictionary into a predictable local study record while preserving original eligibility wording. This pure transformation does not fetch data or call a model. A pure function returns a result from its inputs without network or database effects, which makes failures easier to isolate.

Create these files:

- ./pyproject.toml — use the minimal Python3.12, setuptools, stdlib dataclass and pytest setup specified in C02; introduce the larger stack at its corresponding milestone after compatibility checks.
- ./src/trial_explorer/__init__.py — make the package importable; do not trigger network calls or database creation on import.
- ./src/trial_explorer/models.py — define Study with nct_id, title, criteria_text, source_url, source_updated_at, retrieved_at, snapshot_id, and recruitment_status. Require a valid NCT identifier; retain missing optional values explicitly. Distinguish a missing criteria field from a present empty string. Preserve the original supplied text exactly.
- ./src/trial_explorer/normalize.py — implement normalize_study(raw_record, retrieved_at, snapshot_id). Use the exact source mapping, types, presence states and errors in C01, verified before feature 1. Construct the source URL from its validated ID, with no I/O or coercion.
- ./tests/test_normalize.py — cover one valid record, missing optional metadata, missing criteria, empty criteria, malformed ID, malformed nested fields, and exact preservation of negation, units, and whitespace. Use small fictional dictionaries in this test module and label them as synthetic.

Modify ./README.md with the first actually working installation and test commands, ./TASKS.md with observed feature progress, and create ./docs/learning_log.md to record explanation, author prediction, test result, exercise attempt, and next-feature approval. Exercise: add one new synthetic edge-case test after the author sees the implemented transformation; do not supply the answer in advance.

Acceptance: normalization is reproducible without credentials or network access; optional missing data stays missing; the original criteria string is unchanged. Ask the author to predict how a missing optional field differs from a missing NCT ID before running the tests.

#### 2. Collect a reproducible public snapshot

Create ./src/trial_explorer/ingest.py to fetch ClinicalTrials.gov records with pagination, explicit timeouts, bounded retries, deduplication by NCT ID, and the agreed condition query. Use C01 source paths already verified before normalization and the supported C04 query/pagination rules; recheck for schema drift before implementation. Route every record through normalization and report rejected records with reasons.

Create ./src/trial_explorer/snapshots.py to write immutable snapshots under ./data/raw/<snapshot_id>/ and a manifest containing the exact query, selected NCT IDs, retrieval timestamp, response hashes, selection rule, and rejected-record count. Refuse to overwrite a snapshot ID. Preserve raw responses separately from normalized records. Select records in a documented order so the sample can be explained; never claim this sample is representative of all trials.

Create ./src/trial_explorer/cli.py with explicit fetch and inspect-snapshot commands. Add the package command entry point to ./pyproject.toml. Create ./tests/test_ingest.py for stubbed multi-page responses, duplicates, timeouts, and partial failures, and ./tests/test_snapshots.py for hash consistency, manifest accuracy, and overwrite refusal. Stubbed HTTP responses must never run real network calls in ordinary tests.

Create ./docs/data_provenance.md to document the actual query, selection, schema mapping, snapshot regeneration, and observed missing fields. Keep downloaded data ignored by Git. Update ./README.md and ./TASKS.md. Acceptance: a frozen manifest identifies every saved record; partial collection is explicit and a failed fetch is never labeled a complete snapshot.

#### 3. Store evidence and preserve its location

Extend ./src/trial_explorer/models.py with Passage carrying snapshot_id, nct_id, passage_id, heading, parent context, original-text offsets, original text, and separate search text.

Create ./src/trial_explorer/passages.py to segment eligibility text at criterion boundaries while retaining headings and exceptions. Use the paragraph-v1 grouping, parent-section retention, passage IDs and storage contracts in C05. Character offsets refer to the exact stored Python string, not encoded byte offsets. Group ambiguous nested criteria rather than severing their qualifiers. Stable passage IDs include the snapshot, study, and offsets.

Create ./src/trial_explorer/store.py to create a versioned SQLite schema, insert snapshots/studies/passages transactionally, enforce composite snapshot/study relationships, and expose parameterized read queries. Treat original snapshots as immutable. Return explicit absent records rather than empty invented studies. Store generated output separately from source evidence.

Create ./tests/test_passages.py for exact substring reconstruction, Unicode, parent context, headings, exceptions, and stable IDs. Create ./tests/test_store.py for round trips, rollback, duplicate handling, and isolation between snapshots. Use temporary SQLite files in tests. Extend ./src/trial_explorer/cli.py with an explicit import-snapshot command and update documentation. Acceptance: every passage resolves to the original text in exactly one snapshot/study pair.

#### 4. Establish keyword search and a labeled baseline

Create ./src/trial_explorer/retrieval.py with a shared search contract returning passage IDs, rank, search method, and provenance. Implement BM25 first. Validate allowed study filters and return at most the configured result limit. Unsupported filters produce a validation error; they must not silently broaden the search.

Create ./eval/cases.dev.jsonl and ./eval/cases.heldout.jsonl only after the author has inspected real source records. Target 15 development cases and 10 held-out cases, including unanswerable, ambiguous, and comparison examples. Every case follows C06: literal query, snapshot/scope, source-verified passage labels, expected outcome and fidelity points, with an explicit passage recall@5 equation and exclusions. Synthetic cases remain clearly labeled and separate from real-record measurements. Do not use hosted model guesses as ground truth.

Create ./src/trial_explorer/evaluate.py to read these cases, compute evidence recall at five for cases with positive evidence, exclude explicitly inapplicable cases with counts, and write per-case results with configuration and snapshot hashes. Keep held-out labels out of retrieval tuning. Create ./tests/test_retrieval.py for filtering and deterministic ranking behavior, and ./tests/test_evaluate.py for manually calculable metric cases and zero-denominator handling.

Extend ./src/trial_explorer/cli.py with search and evaluate-retrieval commands. Create ./docs/evaluation.md for case construction, rubric, development/held-out separation, and actual baseline results. Acceptance: baseline scores have denominators and reproducible inputs; no expected improvement is fabricated.

#### 5. Add embeddings and combined retrieval

Create ./src/trial_explorer/embeddings.py with a local embedding adapter and ./src/trial_explorer/indexes.py for the FAISS index, passage mapping, and manifest checks. Follow C09: screen metadata, approve a bounded candidate sample/download, measure that candidate on development data, then choose the final model/revision before full indexing. Sampling permission is distinct from final selection.

Update ./src/trial_explorer/retrieval.py with vector retrieval and reciprocal rank fusion. Start with a simple exact vector index for the small sample and normalized vectors consistent with its similarity metric. Persist the model revision, vector dimension, normalization, passage mapping, chunking configuration, and snapshot hash. Refuse stale or mismatched indexes. Apply study constraints to candidate selection so irrelevant top results cannot crowd out an allowed study.

Create ./tests/test_indexes.py for save/load consistency, stale manifest rejection, and correct ID mapping. Extend ./tests/test_retrieval.py with exact tiny vectors, fusion behavior, ties, and filter isolation. Tiny vectors verify retrieval logic without downloading a model. Test actual embeddings separately and label that result. Update dependencies and CLI index-building commands. Compare keyword-only, vector-only, and combined retrieval on the same cases, saving actual results in ./docs/evaluation.md.

#### 6. Build cited question responses with a hosted adapter

Create ./src/trial_explorer/config.py for validated runtime settings and ./src/trial_explorer/providers/__init__.py for a package boundary. Create ./src/trial_explorer/providers/base.py defining the hosted adapter contract and ./src/trial_explorer/providers/hosted.py for the single provider selected by the author. Implement no provider-specific calls until the provider/model decision, current prices/data handling, token limits, and spending cap have been recorded in ./docs/model_decisions.md. Local work and fake-adapter tests can proceed before this decision.

Create ./src/trial_explorer/prompts.py for versioned instructions that distinguish source data from executable instructions. Create ./src/trial_explorer/answers.py to assemble bounded context, ask for structured claims, and assign the approved response outcomes. Create ./src/trial_explorer/citations.py to resolve permitted evidence IDs and verify exact quotes, source offsets, study scope, and snapshot provenance. Extend ./src/trial_explorer/models.py with request, claim, citation, and outcome schemas.

Create ./src/trial_explorer/budget.py for per-request token/call allowances and session cost reservations, including retries and unknown usage. Disable live generation unless all required pricing and limit settings exist. Create ./.env.example with empty credential fields and documented configuration names; keep actual credentials untracked. Explicitly Create ./tests/fakes.py with the C07 scripted expectations/replies/errors/usage contract; all default tests use it without network access.

Create ./tests/test_answers.py for unsupported claims, no evidence, failed generation, context truncation boundaries, and comparison scope; ./tests/test_citations.py for wrong IDs/quotes/snapshots and preserved source wording; and ./tests/test_budget.py for reservation, reconciliation, unknown usage, and exhausted limits. Explicitly verify that a search miss is not treated as proof of absence; full-record review is required for that outcome.

Create ./docs/model_decisions.md at first model screening; then Modify it with observed provider/model capabilities, verified prices/date, smoke-test results, cap configuration and limitations. Acceptance: verified provenance is distinct from semantic fidelity; invalid explanations become explicit fallback outcomes with original evidence. API billing controls remain estimates rather than guarantees.

#### 7. Add bounded tool calling and saved sessions

Create ./src/trial_explorer/tools.py for the three approved validated read-only tools. Create ./src/trial_explorer/workflow.py to assemble the LangGraph flow and checkpointed state. Extend ./src/trial_explorer/store.py with session and checkpoint persistence support using the compatible LangGraph persistence integration selected during dependency installation.

Enforce at most three tool executions per request, a graph step limit, request deadlines, and the shared model call/cost budget. Unknown tools and invalid arguments stop with an explicit error. Pin the session to its snapshot; validate incoming study IDs against it. Do not reuse old generated prose as new evidence.

Create ./tests/test_tools.py for schemas and study scope and ./tests/test_workflow.py for tool dispatch, hostile source instructions, repeated tool loops, restart/resume, session isolation, and snapshot changes. A fake adapter proves control-flow behavior; separately record a live tool-calling smoke test after author prediction and spending authorization. Acceptance: the model can select only allowed operations, and loop termination remains under application control.

#### 8. Expose the local API and instrument requests

Create ./src/trial_explorer/api.py for GET /api/v1/studies, GET /api/v1/studies/{nct_id}, POST /api/v1/search, and POST /api/v1/questions. Wire the approved services without duplicating retrieval rules. Validate study IDs, session IDs, snapshot scope, question length, and comparison cardinality. Include snapshot and request IDs in responses. Bind the documented development command to localhost.

Create ./src/trial_explorer/telemetry.py for structured, redacted events with request/session IDs, stage timings, evidence IDs, outcome, model identifier, and token usage when supplied. Do not add an answer cache. Preserve C07 sessions, checkpoints and the attempt ledger; terminal-request replay control cannot serve a new question by looking up an old answer.

Create ./tests/test_api.py for response contracts, malformed/unknown IDs, filtered search without hosted credentials, provider failures, and per-study comparison attribution. Create ./tests/test_telemetry.py for required fields and credential/raw-question exclusion, and extend ./tests/test_store.py for session/ledger isolation and paid-call replay safety. Update ./README.md with working API examples and the evidence flow. Acceptance: a provider outage leaves local search usable and is visible as a generation failure, never a successful explanation.

#### 9. Evaluate and prepare a portfolio release

Extend ./src/trial_explorer/evaluate.py with question-response evaluation: outcome correctness, citation validity, manual claim-fidelity rubric, latency, and estimated/reported usage cost. Automated checks do not replace the author's manual reading of paraphrases. Preserve detailed failed cases and distinguish development tuning from the final held-out run.

Create ./.github/workflows/ci.yml for offline pytest and static checks. Modify ./pyproject.toml to define those checks. Create ./requirements.lock with exact resolved versions for the tested Python/Windows environment and document its generation and platform scope; do not claim it covers untested platforms. CI uses fake adapters and small fixtures, no provider secrets, network dataset download, or large model download. A separate live evaluation is opt-in and budgeted.

Create ./docs/results.md with measured results, case counts, reproducibility metadata, representative failures, runtime environment, and explicit limitations. Create ./docs/architecture.md to explain the implemented data path after it exists. Modify ./README.md with verified setup/run/test/evaluation commands and demo examples; ./TASKS.md with completion evidence; ./docs/learning_log.md with actual exercises and author decisions; and ./AGENTS.md to reflect the transition from EGM design to approved incremental implementation. Update ./discussion_summary.md and ./design_draft.md if reviewed findings change a contract. Modify ./.gitignore only when additional generated paths need exclusion; keep ./eval/ labels and documentation tracked.

Modify the existing ./docs/designs/clinical-trial-criteria-explorer.md with accepted resolution edits. Modify the existing ./docs/designs/SITEMAP.md only if its index entry needs updating. Finalizing this document and running a fresh EGM review are design tasks, distinct from implementing application features.

### Verification commands and required evidence

The following are planned commands, not commands already run or promises that dependencies are installed. In each coding session, wait for the author's prediction before relevant execution.

- Setup: python -m venv .venv, then .venv/Scripts/python.exe -m pip install -e ".[dev]" after dependency definitions exist. Retain a tested dependency lock once resolved.
- Feature tests: .venv/Scripts/python.exe -m pytest tests/test_normalize.py -q for the first feature; replace the selected test path with the milestone's specific tests afterward.
- Complete offline suite at release: .venv/Scripts/python.exe -m pytest -q. No paid requests or network downloads occur in this suite.
- Static checks at release: .venv/Scripts/python.exe -m ruff check . and .venv/Scripts/python.exe -m ruff format --check . after their project configuration exists.
- Application: .venv/Scripts/python.exe -m uvicorn trial_explorer.api:app --host 127.0.0.1 --port 8000 after the API milestone exists.
- Data and retrieval evaluation: the trial-explorer CLI defined in ./pyproject.toml exposes fetch, inspect-snapshot, import-snapshot, build-index, search, evaluate-retrieval, and evaluate-answers subcommands with explicit snapshot/config/case/output paths. evaluate-answers requires an explicit live-generation opt-in for hosted requests.
- Release evidence: all applicable offline tests pass; every designated unanswerable release case produces its expected uncertainty outcome; invalid citations are rejected in adversarial fixtures; actual benchmark scores and failures are reported without invented performance targets.

C01-C10 below define the precise contracts for each milestone and take precedence over less specific summaries. Do not impose a coverage percentage without evidence that it improves verification. Test difficult behavior and failure paths, including source corruption, rather than writing assertions that merely repeat the implementation.

### Reconciliation and remaining prerequisites

This plan implements the approved local-storage, local-retrieval, hosted-generation architecture. It does not select a new external interface or model provider. The author must still choose an embedding model and hosted model at their respective milestones, with measured compatibility and costs. If evidence requires a contract or architecture change, return it for a design decision before implementation.

Finalization check against discussion_summary.md: no unresolved contradictions were found. The approximately 50-study type 2 diabetes sample, public-data boundary, local retrieval and hosted generation, and incremental learning workflow remain aligned. The draft expands the predecessor with the technical contracts and file-level tasks the author separately approved, including offline CI and static checks. Model choice, pricing, and spending-cap prerequisites remain explicit; they have not been silently resolved. This check is by the drafting agent and is not a fresh-context Goldfish review.


## Detailed implementation contracts

The author accepted these contracts and all fourteen resolution actions with "auto accept" on 2026-11-08. Baseline defaults are adopted design decisions, not measured best settings. The proposal artifacts remain as historical snapshots; this document is the current design.

### C01 — First-feature normalization contract (R01)

Public function: normalize_study(raw_record: dict[str, object], retrieved_at: datetime, snapshot_id: str) -> Study. No I/O or mutation of raw_record. Study is a frozen standard-library dataclass; its annotations alone do not validate values. The normalizer explicitly checks every boundary invariant before construction. Study is an internal record, never an alternative unvalidated external-input path.

Source paths are relative to the ClinicalTrials.gov v2 study object:

- nct_id: protocolSection.identificationModule.nctId; required str matching ASCII ^NCT[0-9]{8}$ exactly. No case conversion or whitespace trimming.
- title: protocolSection.identificationModule.briefTitle; str | None, missing/null becomes None, supplied text including an empty string is retained.
- criteria_text: protocolSection.eligibilityModule.eligibilityCriteria; str | None. Preserve supplied Unicode, whitespace, operators, quantities and units exactly.
- criteria_state: Literal["missing", "null", "empty", "present"]. An absent eligibility module or absent leaf is missing; explicit null at the leaf is null; a supplied "" is empty; any nonempty string, including whitespace-only text, is present. Both missing and null have criteria_text=None, with state preserving the distinction. Whitespace-only strings are preserved but are not usable for indexing/sample selection.
- recruitment_status: protocolSection.statusModule.overallStatus; str | None. Missing/null becomes None. Supplied strings must be an exact current API OverallStatus enum value; unknown values are rejected and surfaced for schema review.
- source_updated_at: protocolSection.statusModule.lastUpdatePostDateStruct.date; ISO YYYY-MM-DD str | None, validated as a real calendar date and retained as text. It is a source date, not an invented timestamp. Missing/null becomes None.
- source_url: str computed as https://clinicaltrials.gov/study/{nct_id}, never accepted from an untrusted arbitrary URL field.
- retrieved_at: timezone-aware datetime supplied by ingestion, converted to UTC, serialized with a trailing Z and preserved microsecond precision when nonzero. Reject naive datetimes, strings or other types at this Python function boundary.
- snapshot_id: nonempty str supplied by the caller matching ^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$; immutable once stored.

raw_record, protocolSection and identificationModule must be dictionaries. Optional intermediate modules/structures may be missing/null, meaning their optional leaves are missing. A supplied non-null intermediate value of another type is malformed. Unknown source keys are ignored by normalization and retained in raw responses. Do not coerce numbers, booleans, lists or objects to strings.

Raise StudyNormalizationError, a ValueError subclass, with code and path attributes and a readable message that omits the complete source record. Codes: missing_required, invalid_type, invalid_nct_id, invalid_date, invalid_timestamp, invalid_snapshot_id, invalid_status. Validate caller timestamp/snapshot first, then required structure/ID, then optional fields in the order title, criteria, status, source date. No partially valid Study is returned after an error.

Source-status allowlist for this revision: ACTIVE_NOT_RECRUITING, APPROVED_FOR_MARKETING, AVAILABLE, COMPLETED, ENROLLING_BY_INVITATION, NO_LONGER_AVAILABLE, NOT_YET_RECRUITING, RECRUITING, SUSPENDED, TEMPORARILY_NOT_AVAILABLE, TERMINATED, UNKNOWN, WITHDRAWN, WITHHELD. Confirm against the current official schema before implementation; schema drift is a prerequisite failure rather than permission to guess.

Contract examples are synthetic, not records fetched from the registry. With a valid ID NCT00000001, absent briefTitle produces title=None. An omitted eligibilityCriteria produces criteria_state="missing" and criteria_text=None; an explicit null produces state="null"; "" produces state="empty" and criteria_text="". The string "  HbA1c >= 7%; no insulin.\n" remains byte-for-byte equivalent after UTF-8 serialization/decoding. A missing nctId raises missing_required at protocolSection.identificationModule.nctId; "nct00000001" raises invalid_nct_id. These are specification examples, not the learner's later exercise solution.

### C02 — Minimal package and learning setup (R02)

Use Python >=3.12,<3.13 for the first verified environment, matching the detected 3.12 installation. Do not claim support for additional interpreters/platforms until tested. Build with setuptools.build_meta and build requirement setuptools>=77,<85. Use src/trial_explorer package discovery and project version 0.1.0. Feature 1 has no runtime dependency; the dev extra contains pytest>=8.3,<10. Use frozen dataclasses and explicit validation rather than adding a validation framework to this first transformation. Later FastAPI boundary models may use its supported validation framework without replacing the internal source record.

Set pytest testpaths=["tests"] and import mode importlib. Do not add sys.path changes in tests. Install the project editable into .venv using python -m pip install -e ".[dev]"; invoke that environment's python for all tests. Record actually resolved package versions at setup; build/dev version bounds are compatibility choices, not a claim that an environment has been installed. Add Ruff with an explicitly recorded compatible version when static checks are introduced. The package setup is mechanical support for the normalization feature, not a second application feature.

Alternatives: Pydantic strict models would give reusable validation/schema generation but add a dependency and framework concepts now; raw dictionaries have minimal setup but leave internal structure less explicit. The proposed dataclass keeps the first lesson focused, at the cost of writing boundary checks explicitly. The author accepted this package/model choice through the EGM batch decision.

### C03 — Bounded passage search and scope (R03, R04)

The search unit is an original-source passage with study ID and provenance. One study may contribute multiple results. Ordinary search returns at most five passages, not five unique studies and not every matching study. Comparisons perform one independent search per selected study, with at most five passages per side. Search score is neither eligibility probability nor semantic confidence.

Every search response reports snapshot_id, snapshot_date, applied_filters, permitted_study_count, permitted_passage_count, limit, returned_count, result_unit="passage", and exhaustive=false. Display: "These passages match the query in the stored sample; this result is not exhaustive." Candidate counts mean eligible-to-search records, not the number of all semantically relevant matches. Collection-wide absence and completeness claims are forbidden. A selected-study absence statement requires full-record review and remains subject to fidelity evaluation.

SearchFilters has only optional nct_ids and recruitment_statuses arrays, absent/null meaning no constraint. Present arrays must be nonempty, distinct, max50 items. IDs must exist in the selected snapshot; statuses must match C01. Unknown keys/values fail validation. Match OR within each array, AND between arrays. A missing source status does not satisfy a status filter. Selected-study scope intersects filters; it never expands them. Comparison IDs are distinct and both must remain permitted. A valid filter with zero matches returns an empty result, not an error.

### C04 — Snapshot collection and partial failures (R06)

Fetch GET https://clinicaltrials.gov/api/v2/studies with format=json, markupFormat=markdown, query.cond="type 2 diabetes", pageSize=50, sort="LastUpdatePostDate:desc", and no recruitment-status restriction. Fetch at most four successful pages or stop earlier when nextPageToken is absent. Follow nextPageToken even if studies is empty; keep all query parameters identical between pages. A repeated token is a failure. The four-page cap intentionally bounds the candidate window to at most 200 returned rows; it is not a complete registry search.

Validate records through C01, retain rejected records/reasons, deduplicate usable records by NCT ID, and choose the lexicographically first 50 usable IDs from the saved window. Usable means normalization succeeds and criteria_text contains at least one non-whitespace character. For duplicate IDs choose the valid record with the latest source_updated_at (missing dates sort before dates), breaking a remaining tie by lexicographically smaller SHA256 of canonical JSON. Save duplicates and exclusions as provenance. The selection is deterministic from the saved candidate window, not guaranteed identical on future live API runs.

Use a 20-second HTTP timeout per attempt; at most three attempts per page. Retry only network timeouts/connection failures and HTTP 429/500/502/503/504, with 1s then 2s delay. If Retry-After is supplied and valid, honor it up to 30s; a larger value ends the run as partial rather than hammering the API. Fail nonretryable responses, malformed envelopes and token loops explicitly. Do not retry malformed study records; record their rejection and continue.

Persist each raw successful response and hash under data/raw/<snapshot_id>/. Create snapshot_id as "ctg_" + 32 lowercase UUID4 hex digits. Write pages atomically within a new staging directory; atomically write the final manifest last. Missing final manifest means unfinished and cannot be imported. Never overwrite an ID. Manifest schema_version=1 contains snapshot_id, UTC started_at/completed_at, exact query params, page cap/attempt limits, raw-page filenames/request-response tokens/timestamps and byte SHA256 hashes, page count, candidate count, selected IDs with raw page/row locators, rejected/duplicate counts and reason records, selection rule version, target_count=50, selected_count, target_met, stop_reason (api_end|page_cap|fetch_error), fetch_status (complete|partial), error_code/path if failed, and a SHA256 of canonical manifest content excluding its own hash. Canonical JSON for manifests and duplicate tie-breaks is UTF-8 encoding of json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False); exclude only the manifest hash field when hashing the manifest. Raw-page hashes use exact bytes, not canonical reserialization.

complete means the configured bounded run ended at api_end or page_cap without a fetch/schema/token failure; it never claims registry completeness. target_met separately records shortfall below50. partial means fetch/schema/token failure after zero or more successful pages. Preserve partial runs for inspection; ordinary import/evaluation rejects them. Never silently activate a partial snapshot. Importing a valid complete snapshot with a shortfall exposes the actual count and target_met=false; evaluation uses that actual sample size. A new fetch cannot mutate an existing frozen snapshot.

### C05 — Segmentation, evidence IDs, and SQLite (R07)

Use segmentation version paragraph-v1. Work on the original Python string using splitlines(keepends=True) and cumulative Unicode character offsets [start,end). A heading is a whole line whose trimmed content, after removing an optional Markdown # prefix and one optional trailing colon, casefolds to "inclusion criteria" or "exclusion criteria". A section runs from that heading's start to the next heading's start, or end of text; text before the first heading is an unnamed section. Within a section emit maximal consecutive groups of nonblank, non-heading lines, including their original line endings. Blank means whitespace-only content excluding the line ending. Keep bullets, nested bullets and continuation lines within the group; do not split punctuation or numeric operators.

Parent context is always the complete original enclosing section span, including its heading. Context assembly includes this parent intact, deduplicating identical parent ranges; it never drops a cross-block exception to fit a smaller prompt. If the parent cannot fit, omit that evidence with a scope warning or return review-needed rather than trim it. No heading yields an unnamed full-text parent. Heading-only/blank sections produce no passages. Missing, empty, and whitespace-only criteria produce zero passages while remaining stored at study level. No heuristic claims that this segmentation understands clinical logic.

Each Passage has snapshot_id, nct_id, passage_id, segmentation_version, source_start/end, text, heading nullable, parent_source_start/end, parent_text and search_text. text must equal criteria_text[start:end]. search_text=text at storage; C06 owns all lexical normalization so there are no competing normalizers. Parent ranges are additional exact source spans, not rewritten criteria. Compute passage_id as "p:paragraph-v1:" + snapshot_id + ":" + nct_id + ":" + decimal(start) + ":" + decimal(end). Changing segmentation creates a new explicitly versioned derived dataset/index and new labels; it does not reassign existing IDs or change raw snapshots. Search/evaluation configuration pins that derivative version.

Synthetic example: "Inclusion Criteria:\n- A\n  - B\n\n- C\n" has length35, heading span [0,20), passage spans [20,30) and [31,35), and parent span [0,35). The nested B remains with A. These are documentation examples to verify against the literal, not an exercise answer. Do not interpret an absent criterion as clinical permission.

SQLite schema version is PRAGMA user_version=1. Enable foreign_keys for every connection. snapshots: snapshot_id TEXT PRIMARY KEY NOT NULL; manifest_hash TEXT NOT NULL; retrieved_at TEXT NOT NULL; fetch_status TEXT NOT NULL; target_met INTEGER NOT NULL; manifest_json TEXT NOT NULL. studies: snapshot_id/nct_id TEXT NOT NULL, composite PRIMARY KEY(snapshot_id,nct_id), FK snapshot_id; typed Study fields stored as TEXT/NULL following C01, with source_url/retrieved_at/criteria_state NOT NULL. passages: passage_id TEXT PRIMARY KEY NOT NULL, snapshot_id/nct_id TEXT NOT NULL with composite FK to studies, segmentation_version TEXT NOT NULL; source_start/end and parent_source_start/end INTEGER NOT NULL with CHECK(start>=0 AND end>start); text,parent_text,search_text TEXT NOT NULL; heading TEXT nullable; UNIQUE(snapshot_id,nct_id,segmentation_version,source_start,source_end). Validate source bounds/substring equality in application code inside the import transaction. Store schema_version in manifests as well.

Import snapshots/studies/passages in one transaction: all succeed or none do. The same snapshot ID and matching manifest hash is an idempotent no-op only after verifying equal row counts and all stored study/passage field values for the pinned segmentation revision; same ID with another hash or conflicting row is an error. Initialize user_version=0 only if no application tables exist, creating schema and setting version1 atomically. Accept existing version1; nonempty version0 or another version fails with migration_required. Do not auto-destructively migrate. Inputs use parameterized SQL. Index manifest checks remain mandatory. Later sessions/checkpoints/budget tables are separate operational state, not mutations of source evidence.

### C06 — Deterministic retrieval and evaluation (R04, R08)

Tokenizer lexical-v1 applies Unicode NFKC to search text, maps ≤/≥ to <=/>=, casefolds, then uses Python Unicode regex \w+(?:\.\w+)*|<=|>=|[<>=%+\-/]. Use it identically for queries/passages; no stop words, stemming, synonyms or metadata boosts. Original citation text stays unchanged. Reject a query yielding no tokens.

BM25 defaults k1=1.2, b=0.75. For unique query terms sum IDF(t)*tf*(k1+1)/(tf+k1*(1-b+b*len/avgdl)), with IDF(t)=ln(1+(N-df+0.5)/(df+0.5)). Statistics cover all passages in the snapshot; filters restrict candidates without recomputing statistics. Ignore absent query terms; return only positive BM25 scores. Empty corpus yields no results. Document this formula rather than inheriting undocumented package-specific scoring behavior.

Vector search uses CPU FAISS IndexFlatIP on finite float32 vectors. L2-normalize passage/query vectors; reject zeros, dimension mismatch and nonfinite values. For filters, build a temporary exact index using only permitted existing vectors; score all of that subset before stable tie sorting, without re-embedding. Do not use global top-k followed by filtering. No unvalidated cosine threshold. Tie order for all unrounded score ties: nct_id ascending, source_start ascending, passage_id ascending.

Each retriever yields min(20, permitted_passage_count) candidates; BM25 may yield fewer positive matches. Use equal-weight reciprocal rank fusion: score(p)=sum(1/(60+rank(p))) with one-based ranks in each list and zero for missing entries. Deduplicate passage IDs, use the common tie order, then return at most5. Comparison repeats independently per side. Hash tokenizer/BM25 parameters, tie rule, candidate20, RRF60, final5, scope/configuration and embedding revision in the retrieval manifest. These are baseline defaults to evaluate, not claimed best parameters.

Each eval JSONL row: schema_version=1, case_id unique str, data_kind real|synthetic, snapshot_id, query nonempty str, mode search|study_question|comparison, selected_nct_ids (0/1/2 distinct IDs matching mode), filters SearchFilters, retrieval_checks array, expected_outcome, required_fidelity_points string array, source_verified_notes str. A retrieval_check has scope_nct_ids null/nonempty unique array, applicability positive|absent|not_applicable, relevant_evidence array of {passage_id,exact_quote}, and nonempty source_review_notes. Search/study rows have one check; comparisons have one per study and use the same literal query independently. Expected outcome for search is results; question outcomes follow C07.

Positive checks require >=1 distinct source-verified passage; absent/not_applicable checks require an empty evidence list and a stated reason. Validate labels and scope before evaluation; invalid labels fail, not silently skip. No collection-wide absent label. Keep real and synthetic aggregates separate and tune only on the development split (target15 cases), preserving the held-out split (target10) for final reporting.

Passage recall@5 per positive check = distinct relevant IDs returned in first5 / all distinct relevant IDs. Report macro mean over positive checks, every numerator/denominator, case/check counts and exclusions. Comparison contributes two checks. Zero positive checks => N/A. Citation validity = valid assessed citation occurrences / all assessed citations, requiring correct study/snapshot/ID/exact quote/offset; zero citations => N/A. Report rejected outputs/citations separately so rejection cannot hide generation failures.

Manual claim fidelity = faithful factual claim occurrences / assessed factual claim occurrences. Required subject, negation, threshold/operator, quantity/unit, scope and exceptions must all be supported. Label contradicted, unsupported and review-needed claims as not faithful; retain per-case failures and omissions against required_fidelity_points. Zero factual claims => N/A; count excluded interface text. Report expected-outcome correctness, including all unanswerable cases, separately. Set no invented quality/improvement target.

### C07 — Adapter, tools, bounded workflow, and spending state (R09)

All provider-independent types are strict typed records; reject unknown fields, implicit coercion and invalid union variants. ModelRequest contains request_id,attempt_id,snapshot_id,model_id,prompt_version,system_instruction,ordered messages (role system|user|assistant|tool, content),selected_nct_ids,allowed evidence records,tool schemas,allow_tools,max_input_tokens,max_output_tokens,remaining_deadline_ms. Only complete permitted source spans may appear as evidence. ModelReply includes Usage and exactly one tagged draft variant: tool_call {call_id,name,arguments}, or final {study_results}. Multiple/parallel tool requests are invalid. A study_result has nct_id,status and claims. A scoped answer has exactly one result for each selected study; a collection answer groups only the bounded returned studies. A Claim has text of1..1000 characters and1..5 unique evidence_ids; max20 claims total. Answered study results require >=1 claim; absence/insufficient results carry no invented claims. A model cannot assert its own full-record-reviewed marker.

Usage contains input_tokens/output_tokens nonnegative integers or null, complete bool, and any additional billable dimensions required by the selected pricing schedule. Unknown/incomplete usage is never treated as zero. ProviderFailure carries code unavailable|timeout|rate_limited|invalid_response|authentication|unsupported_capability, safe message, retryable bool, dispatch_state not_sent|sent|unknown, and usage. Reply call IDs must be unique within a request.

Adapter contract: a side-effect-free input-token/charge-bound method followed by generate(ModelRequest) -> ModelReply, or raise ProviderFailure. It does not execute tools, reserve budget or secretly retry; disable SDK retries. Before feature6, explicitly Create tests/fakes.py with ScriptedModelAdapter consuming a fixed ordered list of expected requests and replies/failures, recording immutable received requests and attempt IDs and returning each scripted item exactly once. Missing/mismatched script raises AssertionError; assert all expected steps consumed. Inject clock/ID factories and virtual elapsed time; do not sleep. Represent unknown usage and dispatched failures explicitly; no network imports, credentials or fallback provider calls. This fake verifies control flow, never live model quality.

Tool schemas reuse SearchFilters. search_criteria(query,filters) returns C03 results; fetch_study(nct_id) returns saved criteria/provenance; compare_criteria(query,nct_ids) requires exactly two permitted distinct IDs and returns separate result groups. Bind snapshot/session scope server-side, not in model arguments. Validate every tool call before execution. Tool replies contain success/error, evidence records with source IDs, full_record_available and explicit scope warnings. Bound source text to24,000 Unicode characters per result using whole parent spans; oversized full records return metadata, text=null and complete=false. The study-detail API still returns its full stored text. Only a complete source record actually delivered within the model's input budget enters the application's full-record-reviewed set.

Workflow nodes: validate_request -> acquire_session -> assemble_context -> model -> tools -> model as needed -> validate_final -> persist_terminal. Reserve spending inside the model node before each dispatch. Limit defaults: max3 actual tool executions, max4 model attempts including at most1 transient retry across the request, max16 application node entries, 30-second monotonic deadline; per-attempt timeout=min(10 seconds,remaining deadline). LangGraph recursion_limit=16 is an additional super-step guard, not the tool counter. One tool call is allowed per reply; after the third tool, disable tools in subsequent model input. Stop unknown/malformed tools before any execution; return review-needed with an error warning. Exhausted limits return insufficient-reviewed-evidence with execution-limit warning. Provider failure returns generation-unavailable with gathered evidence. Invalid final schema/citations returns review-needed. No automatic answer-repair model call.

Outcomes: answered (claims passed structure/citation checks, not clinically verified); not-stated-in-record (only a selected study whose full criteria were actually supplied/reviewed); insufficient-reviewed-evidence (no adequate support, incomplete context or limit); generation-unavailable; review-needed. Study groups use the same statuses except global generation-unavailable. For mixed comparison groups the top-level status is review-needed if any group needs review, otherwise insufficient-reviewed-evidence if any is insufficient, otherwise not-stated-in-record if all are absent, otherwise answered with the separate groups retained. Participation requests receive study-contact guidance, never an eligibility verdict. Search-only endpoints do not generate answers.

SessionState has schema_version=1, session_id UUID4, pinned snapshot_id, selected IDs, current request_id, evidence IDs, full-record-reviewed IDs, bounded history, application/tool/model counters, outcome and checkpoint IDs. Retain at most last4 user turns and4 assistant turns, subject to context budget; history is conversation context, never source evidence. Each follow-up retrieves fresh evidence from the pinned snapshot. Requests in the same session execute one at a time; a second concurrent question gets session_busy. Add sessions(session_id PK,snapshot_id FK,state_json,active_request_id nullable,cap_currency,cap_micro_usd,spent_micro_usd,reserved_micro_usd,accounting_blocked), requests(request_id PK,session_id FK,status,outcome,terminal_json nullable), and attempts(attempt_id PK,request_id FK,status,reserved_cost,actual_cost nullable,pricing_revision,usage_json) to operational SQLite storage. Use thread_id=session_id and checkpoint namespace=request_id with a persistent compatible SQLite checkpointer. Persist terminal results for replay control, not as a reusable answer cache. Resuming a terminal request performs no new model call; restarting an incomplete request follows the dispatch-ledger rule below.

Session spending amounts are user-configured, not chosen here. Before a live attempt, calculate an upper bound covering the input estimate, configured output ceiling and every billable dimension in the verified price schedule; if the bound cannot be established, keep live calls disabled. Store money as integer micro-USD, calculating with decimal arithmetic and conservative upward rounding. In BEGIN IMMEDIATE, check spent plus outstanding reservations plus new reservation <= cap, create the attempt row and update the totals atomically, then commit before any network call. Use a busy timeout of250ms and return an explicit storage-busy error if exceeded. No transaction stays open while waiting for the provider.

Before dispatch, atomically conditionally transition reserved -> dispatched; only the successful owner may invoke the adapter. A checkpoint resume must not automatically repeat a dispatched attempt; if a terminal response was stored, reuse that same request's terminal result, otherwise mark usage_unknown, retain the full reservation, and return generation-unavailable for manual inspection. This may conservatively charge a reservation even if the call was never sent. Reconcile complete usage atomically and idempotently by attempt_id, charging once and releasing only the documented difference; incomplete usage retains the full reservation. Release a whole reservation only when dispatch is definitively ruled out. If reported cost exceeds the bound, record actual cost, disable further live calls for that session, and report a cap-estimation breach. Retries get their own reservation and count against all limits. Provider-side budget controls remain necessary where supported; the ledger is not a billing guarantee.

Reset evidence, full-record-reviewed markers and counters only for a new request, not checkpoint resume. Persist request expires_at with the original30s allowance; on recovery use its remaining wall-clock time to establish a new monotonic countdown rather than granting a fresh deadline. Every terminal path, including recovery failure, clears sessions.active_request_id conditionally for that request. Do not reset session spending or snapshot on restart.

### C08 — API and CLI observables (R10)

Bind localhost only. Shared validation: question/query is a str with 1–2000 Unicode characters after checking strip() is nonempty; preserve submitted text for the model, but do not log it by default. Reject unknown JSON fields, invalid IDs/statuses, duplicate IDs, excessive arrays and unknown snapshots. snapshot_id is required for search and new sessions; existing sessions must match their pinned snapshot.

GET /api/v1/studies requires snapshot_id; accepts repeated nct_ids/recruitment_statuses filters, limit default20 range1..50 and offset default0 minimum0. Sort by nct_id ascending. Return {snapshot_id,snapshot_date,items,total,limit,offset,next_offset nullable}. GET /api/v1/studies/{nct_id}?snapshot_id=... returns the stored Study representation and criteria/provenance; no model request.

POST /api/v1/search body {snapshot_id,query,filters={},mode="hybrid"}; mode keyword|vector|hybrid selects an available configured retriever. Before vector setup, keyword works and unavailable vector/hybrid returns index_unavailable, never silent substitution. Return C03 metadata plus results[{passage_id,nct_id,text,source_start,source_end,source_url,source_updated_at,rank,score,method}]. Fixed final result limit5.

POST /api/v1/questions body {snapshot_id,question,selected_nct_ids=[],filters={},session_id=null}; zero selected IDs means bounded sample question, one means study question, two means comparison; more is invalid. An absent session creates a UUID4 session; a supplied UUID must exist. Responses contain request_id,session_id,snapshot_id,snapshot_date,outcome,study_results[{nct_id,status,claims}],citations,evidence,scope,warnings,error nullable. Citation records are assembled by the application, not arbitrary model URLs. Comparison scope retains separate evidence and statuses per selected study. Requests can never change a session's snapshot. Selection is explicit per request and stored for context; it does not silently inherit previous selection.

HTTP mapping: 200 answered or valid uncertainty/empty-search outcomes; 404 unknown snapshot/study/session; 409 snapshot_conflict or session_busy; 422 malformed request/filter; 429 budget_exhausted or local concurrency limit; 502 invalid_model_response/tool contract violation; 503 generation_unavailable/index_unavailable/storage_busy; 504 request_deadline. Error envelopes include request_id and {code,message}, plus evidence for question failures when available. Failure outcomes are never returned as successful generated explanations.

Use stdlib argparse for trial-explorer. Exact command families:

- fetch --output-root data/raw (fixed C04 query/window; reports snapshot_id and manifest path).
- inspect-snapshot --snapshot PATH (reads and reports manifest/hash/completeness; no mutation).
- import-snapshot --snapshot PATH --db PATH (complete snapshots only; partial import rejected).
- build-index --db PATH --snapshot-id ID --index-dir PATH --embedding-config PATH (vector artifacts only, after candidate/model selection).
- search --db PATH --snapshot-id ID --query TEXT --mode keyword|vector|hybrid [--index-dir PATH] [--nct-id ID repeated] [--recruitment-status VALUE repeated].
- evaluate-retrieval --db PATH --snapshot-id ID --cases PATH --output PATH --mode keyword|vector|hybrid [--index-dir PATH].
- evaluate-answers --db PATH --snapshot-id ID --cases PATH --output PATH --config PATH --allow-live-generation. No live-generation default; offline CI uses scripted adapters, not this command's production provider.

Keyword mode deterministically builds its BM25 representation in memory from imported SQLite passages using C06 defaults; it needs neither vector artifacts nor --index-dir/--embedding-config. This makes keyword search and evaluation available before the embedding milestone. All commands emit UTF-8 JSON results; warnings/errors go to stderr. Exit0 successful operation (a reported sample shortfall is still a completed fetch), exit2 argument/schema errors, exit3 fetch/provider/storage/unavailable-index operational errors, exit4 budget or explicit live opt-in missing, exit5 invalid evaluation labels. Never overwrite an existing snapshot or evaluation report path silently. index/config paths must explicitly identify the same snapshot/manifests.

### C09 — Embedding evaluation sequence (R11)

First inspect model cards, license, immutable revision, artifact size, input limits, query/document prompts and local Windows/Python support. Record a shortlist of at most2 candidates without claiming observed fit. Next obtain author approval of that shortlist and a specific resource/runtime/download budget, then download one candidate and test <=50 development passages/queries. Record sample IDs, truncation behavior, errors, load/embedding timing and resource measurements; do not use held-out labels. Finally present the measurements and obtain the final model/revision choice before full indexing. A failed sample does not authorize an unapproved second download. Metadata screening, candidate sampling and final choice are distinct decisions.

### C10 — Rationale, validation wording, and file actions (R05, R12–R14)

Engineering rationale adopted in EGM Resolve for B: keep the first project focused on retrieval, evidence evaluation and service design without making local generation installation/performance a prerequisite. Local generation remains viable; hosted generation trades that local workload for API credentials, network dependence and measured usage costs. The author accepted this current rationale in the EGM batch decision. It is not an account of the author's earlier motives or evidence that local inference failed.

Remove generated-answer caching from the first release. Keep raw snapshots, vector indexes, checkpoints, session state and the dispatch ledger; those each serve provenance, retrieval or safe execution. Measure latency and usage before reconsidering answer reuse. API claims may pass schema/citation validation but are not thereby semantically or clinically verified.

Explicit planned file actions: Create tests/fakes.py in feature6; Create docs/model_decisions.md at the first model-screening milestone, then Modify it when measurements/provider/cap choices are available; Modify the existing docs/designs/SITEMAP.md if design indexing changes; Modify the existing finalized design rather than creating it again. Preserve historical review reports unchanged, with a link to the eventual resolution record.

### References and limits of verification

Verified externally documented mechanisms are linked here; application defaults remain proposals. No runtime compatibility, dataset completeness, model quality or performance has been tested.

- [ClinicalTrials.gov v2 OpenAPI](https://clinicaltrials.gov/api/oas/v2) and [study structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure): source field paths, date/status types, pagination and supported sort fields.
- [Python dataclasses](https://docs.python.org/3.12/library/dataclasses.html): generated record methods; annotations do not automatically enforce field types.
- [Python packaging guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/) and [setuptools configuration](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html): src layout and build metadata.
- [pytest getting started](https://docs.pytest.org/en/stable/getting-started.html): environment/test commands.
- [Lucene BM25](https://lucene.apache.org/core/9_9_1/core/org/apache/lucene/search/similarities/BM25Similarity.html): reference BM25 defaults and positive IDF form; no Lucene dependency is proposed.
- [FAISS metrics](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances): cosine through normalized inner products.
- [Original RRF paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf): reciprocal-rank fusion mechanism and reference constant.
- [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) and [persistence](https://docs.langchain.com/oss/python/langgraph/persistence): super-step guard and checkpoint behavior.
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html): write-transaction mechanism for atomic spending checks.


## Next steps

All R01-R14 document corrections were accepted and applied on 2026-11-08. The unsupported demand for an upstream issue/PR link to validate the author's own decision was contested and not applied. See goldfish_review_report.md for traceability and the applied revision hash. Historical review reports and proposal artifacts remain preserved. No independent post-resolution re-audit or convergence is claimed. Next is the approved first coding feature, normalization, following the author's explanation, prediction-before-tests, exercise and next-feature approval gates. No application implementation or tests have started.

*Drafted with EGM*
