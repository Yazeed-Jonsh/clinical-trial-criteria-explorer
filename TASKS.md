# Tasks and learning record

## Day 1 — Define the product

- [x] Preserve the planning conversation as predecessor notes.
- [x] Draft Overview, Problem, Goals, and boundaries using EGM.
- [x] Write five starter evaluation question templates.
- [x] Create documentation and agent instructions.
- [x] Author reviews Overview and Goals: approved in chat, "yes I approve them".
- [x] Author selects Option B: local retrieval with hosted generation, "B is better".
- [x] Draft technical plan after the section review.
- [x] Author reviews the completed Technical Plan: approved in chat, "yes I approve it".
- [x] Draft Alternatives Considered from predecessor notes.
- [x] Author reviews Alternatives Considered: approved in chat.
- [x] Draft detailed file-level implementation tasks and verification commands.
- [x] Author reviews Detailed Implementation: "yes I approve the detailed implementation plan".
- [x] Reconcile the approved design against predecessor notes; no unresolved contradictions found.
- [x] Confirm the final destination and save the finalized design through EGM's finalization gate.
- [x] Finish Day 1 drafting with an approved scope and a committed documentation milestone.
- [x] Run a fresh-context EGM review of docs/designs/clinical-trial-criteria-explorer.md: five stages, nine reviewers, report-only pass completed.
- [x] Resolve all fourteen actions through EGM Resolve: author accepted the complete change set with "auto accept"; applied to design and recorded in goldfish_review_report.md.
- [x] Preserve historical review/proposal artifacts and synchronize the current design and working draft.
- [x] Begin coding feature 1 after explanation and the author's prediction: normalization, internal record, packaging and synthetic tests written.
- [x] Inventory existing dependencies before downloads; reuse local build tools/packaging and install only missing test dependencies with author permission.
- [x] Install the package editable and run normalization tests: 39 passed in0.57s on Python3.12.7; author prediction confirmed.
- [x] Record data flow, environment/package versions, actual results and limitations.
- [x] Complete the guided empty-title exercise: author added the explained test; 40 cases passed in0.54s.
- [ ] Obtain explicit author approval before feature 2.

## Approved coding sequence after design

1. Normalize one API-shaped record without I/O or model dependencies.
2. Collect and freeze the bounded public study sample.
3. Store studies and source-located passages transactionally.
4. Measure keyword retrieval on labeled questions.
5. Add local embeddings and combined retrieval.
6. Produce cited hosted-model responses with uncertainty and budget controls.
7. Add bounded tool calling and persisted workflow state.
8. Expose the versioned local API and structured logs.
9. Run final held-out evaluation and prepare reproducible portfolio documentation.

Each feature requires the author's approval before starting the next. The original ten one-hour sessions are an effort target; record additional time rather than compressing learning or claiming unfinished work.

## Learning note for Day 1

A specification describes observable behavior. Acceptance criteria make that behavior checkable. An architecture explains the mechanism that will implement it. A question template becomes an evaluation case only after it has a verified source, expected answer, and scoring rule.

Author exercise: explain why an unstated criterion does not establish that a participant meets it. Answer during the section review.

## Evidence

All design sections approved; Option B selected; all fourteen EGM corrections applied. The pure normalization feature implementing C01/C02 is now verified with 39 passing synthetic cases; the author's missing-title versus missing-ID prediction matched actual behavior. Environment details are in docs/learning_log.md. No live dataset, retrieval/model evaluation, or later feature is implemented. Exercise and next-feature approval are pending. No independent post-resolution EGM re-audit/convergence is claimed.

## Day 3 evidence

The reusable fetch command produced a complete live snapshot at the four-page cap. It fetched 200 candidates and selected 50. The 86 passing offline tests include complete and partial collection, byte preservation, and snapshot ID collision checks. Snapshot ingestion into SQLite remains a separate milestone.
