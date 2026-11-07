# Clinical Trial Criteria Explorer

- Author: Yazeed-Jonsh
- Status: Approved by author; fresh EGM review pending
- Date: 2026-11-07
- Predecessor: [discussion_summary.md](../../discussion_summary.md)
- EGM stage: drafting complete; handoff to fresh-context review

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
- G2 — Search: return ranked study results with evidence snippets and IDs. A small labeled question set measures whether relevant evidence appears in the first five results. Set a performance target after measuring the baseline.
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
4. Which studies in this sample explicitly mention kidney-related exclusion criteria? Cite each matching passage; do not infer eligibility.
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

Apply structured study filters before selecting retrieval candidates. Search both the BM25 and vector indexes within that permitted study set. Merge rankings using reciprocal rank fusion, then remove duplicate passages. An initial search returns at most five ranked passages. Treat that limit as an initial configuration to evaluate, not an optimized value.

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

Responses include the snapshot ID/date and source evidence. Question responses add outcome, claims when verified, citations, and a request ID. Reject malformed IDs, unknown studies/snapshots, empty questions, and inputs beyond documented limits. Provider outages are explicit service failures with available source evidence. Interactive API documentation is the first interface; a custom frontend is a later enhancement.

### Cost, privacy, and operational limits

Keep credentials in environment variables excluded from Git. Only public trial excerpts and intended non-sensitive demo questions are sent to the provider. The application is not designed for personal patient narratives; the demo instructs readers to use fictional examples. A text filter cannot guarantee that a user has not entered private information.

Before enabling live generation, record provider/model, model context limit, verified current input/output prices, maximum input/output tokens, request deadline, and a user-agreed session spending cap. Refuse live calls until these are configured. Reserve a conservative upper cost bound before each attempted call, including retries; reconcile reported usage afterward and retain the reservation when usage is unknown. Do not claim an application counter is a provider billing guarantee. Use provider-side limits where available.

Bound retries for transient errors; every retry consumes the request call and cost allowance. Cache successful answers only under a key containing the snapshot, question scope, model, prompt version, and retrieval configuration. Log request IDs, workflow steps, evidence IDs, durations, outcome, model identifier, and token usage when returned. Avoid logging credentials or complete user questions by default.

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

Decision: rejected by the author in favor of B, expressed as "B is better". The author supplied no separate technical rejection rationale. The documented engineering trade-off is local hardware and inference constraints versus hosted credentials, network dependency, and usage charges; this describes the options rather than inventing the author's reasoning.

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

- ./pyproject.toml — declare the package, supported Python range, editable installation, pytest configuration, and dependency groups. Begin with only the dependencies required by this feature; introduce the larger stack at its corresponding milestone after compatibility checks.
- ./src/trial_explorer/__init__.py — make the package importable; do not trigger network calls or database creation on import.
- ./src/trial_explorer/models.py — define Study with nct_id, title, criteria_text, source_url, source_updated_at, retrieved_at, snapshot_id, and recruitment_status. Require a valid NCT identifier; retain missing optional values explicitly. Distinguish a missing criteria field from a present empty string. Preserve the original supplied text exactly.
- ./src/trial_explorer/normalize.py — implement normalize_study(raw_record, retrieved_at, snapshot_id). Read only documented source fields, validate required identifiers, construct a source URL from the validated ID, and return Study. Report malformed fields instead of guessing or silently coercing them.
- ./tests/test_normalize.py — cover one valid record, missing optional metadata, missing criteria, empty criteria, malformed ID, malformed nested fields, and exact preservation of negation, units, and whitespace. Use small fictional dictionaries in this test module and label them as synthetic.

Modify ./README.md with the first actually working installation and test commands, ./TASKS.md with observed feature progress, and create ./docs/learning_log.md to record explanation, author prediction, test result, exercise attempt, and next-feature approval. Exercise: add one new synthetic edge-case test after the author sees the implemented transformation; do not supply the answer in advance.

Acceptance: normalization is reproducible without credentials or network access; optional missing data stays missing; the original criteria string is unchanged. Ask the author to predict how a missing optional field differs from a missing NCT ID before running the tests.

#### 2. Collect a reproducible public snapshot

Create ./src/trial_explorer/ingest.py to fetch ClinicalTrials.gov records with pagination, explicit timeouts, bounded retries, deduplication by NCT ID, and the agreed condition query. Verify the current source schema and pagination behavior against official documentation before implementing. Route every record through normalization and report rejected records with reasons.

Create ./src/trial_explorer/snapshots.py to write immutable snapshots under ./data/raw/<snapshot_id>/ and a manifest containing the exact query, selected NCT IDs, retrieval timestamp, response hashes, selection rule, and rejected-record count. Refuse to overwrite a snapshot ID. Preserve raw responses separately from normalized records. Select records in a documented order so the sample can be explained; never claim this sample is representative of all trials.

Create ./src/trial_explorer/cli.py with explicit fetch and inspect-snapshot commands. Add the package command entry point to ./pyproject.toml. Create ./tests/test_ingest.py for stubbed multi-page responses, duplicates, timeouts, and partial failures, and ./tests/test_snapshots.py for hash consistency, manifest accuracy, and overwrite refusal. Stubbed HTTP responses must never run real network calls in ordinary tests.

Create ./docs/data_provenance.md to document the actual query, selection, schema mapping, snapshot regeneration, and observed missing fields. Keep downloaded data ignored by Git. Update ./README.md and ./TASKS.md. Acceptance: a frozen manifest identifies every saved record; partial collection is explicit and a failed fetch is never labeled a complete snapshot.

#### 3. Store evidence and preserve its location

Extend ./src/trial_explorer/models.py with Passage carrying snapshot_id, nct_id, passage_id, heading, parent context, original-text offsets, original text, and separate search text.

Create ./src/trial_explorer/passages.py to segment eligibility text at criterion boundaries while retaining headings and exceptions. Character offsets refer to the exact stored Python string, not encoded byte offsets. Group ambiguous nested criteria rather than severing their qualifiers. Stable passage IDs include the snapshot, study, and offsets.

Create ./src/trial_explorer/store.py to create a versioned SQLite schema, insert snapshots/studies/passages transactionally, enforce composite snapshot/study relationships, and expose parameterized read queries. Treat original snapshots as immutable. Return explicit absent records rather than empty invented studies. Store generated output separately from source evidence.

Create ./tests/test_passages.py for exact substring reconstruction, Unicode, parent context, headings, exceptions, and stable IDs. Create ./tests/test_store.py for round trips, rollback, duplicate handling, and isolation between snapshots. Use temporary SQLite files in tests. Extend ./src/trial_explorer/cli.py with an explicit import-snapshot command and update documentation. Acceptance: every passage resolves to the original text in exactly one snapshot/study pair.

#### 4. Establish keyword search and a labeled baseline

Create ./src/trial_explorer/retrieval.py with a shared search contract returning passage IDs, rank, search method, and provenance. Implement BM25 first. Validate allowed study filters and return at most the configured result limit. Unsupported filters produce a validation error; they must not silently broaden the search.

Create ./eval/cases.dev.jsonl and ./eval/cases.heldout.jsonl only after the author has inspected real source records. Target 15 development cases and 10 held-out cases, including unanswerable, ambiguous, and comparison examples. Every case records snapshot ID, selected study IDs, expected evidence IDs or explicitly absent evidence, expected outcome, and source-verified notes. Synthetic cases remain clearly labeled and separate from real-record measurements. Do not use hosted model guesses as ground truth.

Create ./src/trial_explorer/evaluate.py to read these cases, compute evidence recall at five for cases with positive evidence, exclude explicitly inapplicable cases with counts, and write per-case results with configuration and snapshot hashes. Keep held-out labels out of retrieval tuning. Create ./tests/test_retrieval.py for filtering and deterministic ranking behavior, and ./tests/test_evaluate.py for manually calculable metric cases and zero-denominator handling.

Extend ./src/trial_explorer/cli.py with search and evaluate-retrieval commands. Create ./docs/evaluation.md for case construction, rubric, development/held-out separation, and actual baseline results. Acceptance: baseline scores have denominators and reproducible inputs; no expected improvement is fabricated.

#### 5. Add embeddings and combined retrieval

Create ./src/trial_explorer/embeddings.py with a local embedding adapter and ./src/trial_explorer/indexes.py for the FAISS index, passage mapping, and manifest checks. Before model downloads, choose and record an embedding model/revision using its official model card, license, Windows/Python compatibility, memory needs, and a short measured sample. This selection is a recorded prerequisite, not an implicit dependency choice.

Update ./src/trial_explorer/retrieval.py with vector retrieval and reciprocal rank fusion. Start with a simple exact vector index for the small sample and normalized vectors consistent with its similarity metric. Persist the model revision, vector dimension, normalization, passage mapping, chunking configuration, and snapshot hash. Refuse stale or mismatched indexes. Apply study constraints to candidate selection so irrelevant top results cannot crowd out an allowed study.

Create ./tests/test_indexes.py for save/load consistency, stale manifest rejection, and correct ID mapping. Extend ./tests/test_retrieval.py with exact tiny vectors, fusion behavior, ties, and filter isolation. Tiny vectors verify retrieval logic without downloading a model. Test actual embeddings separately and label that result. Update dependencies and CLI index-building commands. Compare keyword-only, vector-only, and combined retrieval on the same cases, saving actual results in ./docs/evaluation.md.

#### 6. Build cited question responses with a hosted adapter

Create ./src/trial_explorer/config.py for validated runtime settings and ./src/trial_explorer/providers/__init__.py for a package boundary. Create ./src/trial_explorer/providers/base.py defining the hosted adapter contract and ./src/trial_explorer/providers/hosted.py for the single provider selected by the author. Implement no provider-specific calls until the provider/model decision, current prices/data handling, token limits, and spending cap have been recorded in ./docs/model_decisions.md. Local work and fake-adapter tests can proceed before this decision.

Create ./src/trial_explorer/prompts.py for versioned instructions that distinguish source data from executable instructions. Create ./src/trial_explorer/answers.py to assemble bounded context, ask for structured claims, and assign the approved response outcomes. Create ./src/trial_explorer/citations.py to resolve permitted evidence IDs and verify exact quotes, source offsets, study scope, and snapshot provenance. Extend ./src/trial_explorer/models.py with request, claim, citation, and outcome schemas.

Create ./src/trial_explorer/budget.py for per-request token/call allowances and session cost reservations, including retries and unknown usage. Disable live generation unless all required pricing and limit settings exist. Create ./.env.example with empty credential fields and documented configuration names; keep actual credentials untracked. All default tests use a fake adapter defined in ./tests/fakes.py.

Create ./tests/test_answers.py for unsupported claims, no evidence, failed generation, context truncation boundaries, and comparison scope; ./tests/test_citations.py for wrong IDs/quotes/snapshots and preserved source wording; and ./tests/test_budget.py for reservation, reconciliation, unknown usage, and exhausted limits. Explicitly verify that a search miss is not treated as proof of absence; full-record review is required for that outcome.

Update ./docs/model_decisions.md with actual provider/model capabilities, verified prices and date, smoke-test observations, cost configuration, and limitations once chosen. Acceptance: verified provenance is distinct from semantic fidelity; invalid explanations become explicit fallback outcomes with original evidence. API billing controls remain estimates rather than guarantees.

#### 7. Add bounded tool calling and saved sessions

Create ./src/trial_explorer/tools.py for the three approved validated read-only tools. Create ./src/trial_explorer/workflow.py to assemble the LangGraph flow and checkpointed state. Extend ./src/trial_explorer/store.py with session and checkpoint persistence support using the compatible LangGraph persistence integration selected during dependency installation.

Enforce at most three tool executions per request, a graph step limit, request deadlines, and the shared model call/cost budget. Unknown tools and invalid arguments stop with an explicit error. Pin the session to its snapshot; validate incoming study IDs against it. Do not reuse old generated prose as new evidence.

Create ./tests/test_tools.py for schemas and study scope and ./tests/test_workflow.py for tool dispatch, hostile source instructions, repeated tool loops, restart/resume, session isolation, and snapshot changes. A fake adapter proves control-flow behavior; separately record a live tool-calling smoke test after author prediction and spending authorization. Acceptance: the model can select only allowed operations, and loop termination remains under application control.

#### 8. Expose the local API and instrument requests

Create ./src/trial_explorer/api.py for GET /api/v1/studies, GET /api/v1/studies/{nct_id}, POST /api/v1/search, and POST /api/v1/questions. Wire the approved services without duplicating retrieval rules. Validate study IDs, session IDs, snapshot scope, question length, and comparison cardinality. Include snapshot and request IDs in responses. Bind the documented development command to localhost.

Create ./src/trial_explorer/telemetry.py for structured, redacted events with request/session IDs, stage timings, evidence IDs, outcome, model identifier, and token usage when supplied. Extend ./src/trial_explorer/store.py with the approved successful-answer cache. Key it on snapshot, question scope, model, prompt version, retrieval configuration, and relevant session context; cached output cannot leak between sessions with different context. Do not cache failed generations.

Create ./tests/test_api.py for response contracts, malformed/unknown IDs, filtered search without hosted credentials, provider failures, and per-study comparison attribution. Create ./tests/test_telemetry.py for required fields and credential/raw-question exclusion, and extend ./tests/test_store.py for cache invalidation and isolation. Update ./README.md with working API examples and the evidence flow. Acceptance: a provider outage leaves local search usable and is visible as a generation failure, never a successful explanation.

#### 9. Evaluate and prepare a portfolio release

Extend ./src/trial_explorer/evaluate.py with question-response evaluation: outcome correctness, citation validity, manual claim-fidelity rubric, latency, and estimated/reported usage cost. Automated checks do not replace the author's manual reading of paraphrases. Preserve detailed failed cases and distinguish development tuning from the final held-out run.

Create ./.github/workflows/ci.yml for offline pytest and static checks. Modify ./pyproject.toml to define those checks. Create ./requirements.lock with exact resolved versions for the tested Python/Windows environment and document its generation and platform scope; do not claim it covers untested platforms. CI uses fake adapters and small fixtures, no provider secrets, network dataset download, or large model download. A separate live evaluation is opt-in and budgeted.

Create ./docs/results.md with measured results, case counts, reproducibility metadata, representative failures, runtime environment, and explicit limitations. Create ./docs/architecture.md to explain the implemented data path after it exists. Modify ./README.md with verified setup/run/test/evaluation commands and demo examples; ./TASKS.md with completion evidence; ./docs/learning_log.md with actual exercises and author decisions; and ./AGENTS.md to reflect the transition from EGM design to approved incremental implementation. Update ./discussion_summary.md and ./design_draft.md if reviewed findings change a contract. Modify ./.gitignore only when additional generated paths need exclusion; keep ./eval/ labels and documentation tracked.

Finalize the design as ./docs/designs/clinical-trial-criteria-explorer.md after reconciliation with the predecessor and author approval of its destination. Create ./docs/designs/SITEMAP.md to point to it if a design index is useful at finalization. Finalizing this document and running a fresh EGM review are design tasks, distinct from implementing application features.

### Verification commands and required evidence

The following are planned commands, not commands already run or promises that dependencies are installed. In each coding session, wait for the author's prediction before relevant execution.

- Setup: python -m venv .venv, then .venv/Scripts/python.exe -m pip install -e ".[dev]" after dependency definitions exist. Retain a tested dependency lock once resolved.
- Feature tests: .venv/Scripts/python.exe -m pytest tests/test_normalize.py -q for the first feature; replace the selected test path with the milestone's specific tests afterward.
- Complete offline suite at release: .venv/Scripts/python.exe -m pytest -q. No paid requests or network downloads occur in this suite.
- Static checks at release: .venv/Scripts/python.exe -m ruff check . and .venv/Scripts/python.exe -m ruff format --check . after their project configuration exists.
- Application: .venv/Scripts/python.exe -m uvicorn trial_explorer.api:app --host 127.0.0.1 --port 8000 after the API milestone exists.
- Data and retrieval evaluation: the trial-explorer CLI defined in ./pyproject.toml exposes fetch, inspect-snapshot, import-snapshot, build-index, search, evaluate-retrieval, and evaluate-answers subcommands with explicit snapshot/config/case/output paths. evaluate-answers requires an explicit live-generation opt-in for hosted requests.
- Release evidence: all applicable offline tests pass; every designated unanswerable release case produces its expected uncertainty outcome; invalid citations are rejected in adversarial fixtures; actual benchmark scores and failures are reported without invented performance targets.

Do not impose a coverage percentage without evidence that it improves verification. Test difficult behavior and failure paths, including source corruption, rather than writing assertions that merely repeat the implementation.

### Reconciliation and remaining prerequisites

This plan implements the approved local-storage, local-retrieval, hosted-generation architecture. It does not select a new external interface or model provider. The author must still choose an embedding model and hosted model at their respective milestones, with measured compatibility and costs. If evidence requires a contract or architecture change, return it for a design decision before implementation.

Finalization check against discussion_summary.md: no unresolved contradictions were found. The approximately 50-study type 2 diabetes sample, public-data boundary, local retrieval and hosted generation, and incremental learning workflow remain aligned. The draft expands the predecessor with the technical contracts and file-level tasks the author separately approved, including offline CI and static checks. Model choice, pricing, and spending-cap prerequisites remain explicit; they have not been silently resolved. This check is by the drafting agent and is not a fresh-context Goldfish review.

## Next sections

The author confirmed ./docs/designs/clinical-trial-criteria-explorer.md as the final design destination. The next step is EGM's fresh-context review of that finalized document. No EGM Goldfish review has run, no implementation tests have run, and no code has been written.

*Drafted with EGM*
