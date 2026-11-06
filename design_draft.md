# Clinical Trial Criteria Explorer

- Author: Yazeed-Jonsh
- Status: Draft; Overview and Goals approved; architecture options awaiting author selection
- Date: 2026-11-07
- Predecessor: [discussion_summary.md](discussion_summary.md)
- EGM stage: technical planning; implementation plan pending

Author approved Overview and Goals in chat: "yes I approve them". This approval covers the reader, the approximately 50-study type 2 diabetes sample, and product boundaries. It does not approve the technical options below.

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
- Select retrieval, storage, model, and interface choices in the next design stage after checking local resources and cost constraints.
- Define the evaluation set and how the author will review criteria fidelity. A developer review is not clinical validation.

## Technical Plan — options for author selection

This section proposes two complete starting architectures. Neither has been selected. Both retain the approved behavior and evaluation goals. Exact model and package versions will be checked during implementation; no dependency has been installed.

### Shared proposed foundation

Use Python, a local SQLite database for study metadata and source passages, local text embeddings with a FAISS index for vector retrieval, and BM25 keyword retrieval. Combine ranked results rather than directly adding scores on different scales. Build the keyword baseline before the combined retriever so its effect can be measured.

Keep the original eligibility text and stable passage IDs. Search text may be normalized, but citations must resolve to original source text and the correct study snapshot. Split text at criterion boundaries and retain parent context where a list depends on a heading or exception.

Use a FastAPI service with a /api/v1 prefix and its interactive API documentation for the initial interface. Add a bounded LangGraph workflow with explicitly allowed search, study-detail, and comparison tools after the basic retrieval pipeline works. Save selected study IDs and workflow state per session. Previous generated answers are not evidence for later answers.

Validate structured model responses against permitted evidence IDs. Reject invented IDs, return source wording where a generated explanation cannot be supported, and expose uncertainty. Matching a citation proves that the passage exists, not that the paraphrase is medically faithful; the labeled evaluation must inspect meaning as well.

These are proposed components in both options and are included in the author's architecture choice. If any shared component needs a different approach, revise this section before selection.

### Option A — Local retrieval and local generation

Mechanism: download an embedding model and a small text-generation model, then run search and generation on this computer. After initial downloads and data collection, serving the stored sample can work without an external model API. The generation adapter must support explicit tool requests; reject a candidate that cannot pass the tool-calling smoke test.

Trade-offs: no model API usage charges and full local control, but model downloads consume storage and running generation consumes memory and CPU or GPU resources. Small models may struggle with long criteria, negation, or structured tool responses.

Failure conditions: insufficient memory, unacceptable measured latency, inability to perform tool calls reliably, or poor criteria fidelity. Confirm hardware and benchmark a candidate before committing to it. A failure does not silently switch to a paid provider; bring the evidence back for an architecture revision.

### Option B — Local retrieval with hosted generation

Mechanism: store studies and embeddings locally, retrieve the relevant passages locally, and send only the question and selected public passages to a hosted model. The hosted model returns structured tool requests or an evidence-linked response. Keep the model behind an adapter so data collection and retrieval tests do not require network calls.

Trade-offs: avoids local generation hardware requirements, but adds API credentials, network dependency, provider limits, and usage costs. Quality still requires measurement. Select the provider and model, verify pricing and data handling, and agree on a spending cap before live requests.

Failure conditions: unavailable credentials, exhausted budget, timeouts, rate limits, or failed fidelity tests. Use bounded retries; return retrieved evidence with an explicit generation-unavailable result when the service fails. This fallback is distinct from a generated explanation.

### Proposed flow under either option

ClinicalTrials.gov snapshot -> original source text and metadata -> criterion passages -> keyword and vector indexes -> combined retrieval -> selected evidence -> model adapter -> citation checks -> response.

The generation adapter runs locally in A and calls a hosted service in B. Both options keep tests and local retrieval usable when generation is unavailable.

### Cost and feasibility evidence

- Python 3.12.7 was detected on this machine.
- Windows denied the memory, CPU, and GPU queries. Hardware capacity and local inference performance remain unverified.
- No models, packages, or study records have been downloaded. No costs or latency measurements have been recorded.
- At this sample size the proposed tools serve learning goals; the benchmark must establish whether combined retrieval improves on keyword search.

### Technical references checked during planning

- [FAISS documentation](https://faiss.ai/): vector similarity search, Python wrappers, and CPU installation.
- [SQLite appropriate uses](https://www.sqlite.org/whentouse.html): local application storage and its concurrency trade-offs.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): session checkpoints and state scoped to a thread.

## Next sections

After the author chooses an architecture, complete the technical plan and its section review. Then evaluate alternatives and write detailed file-level implementation tasks through the EGM gates. No EGM Goldfish review has run.

*Drafted with EGM*
