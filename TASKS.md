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
- [ ] Begin coding feature 1, normalize one record, only through the author's explanation/prediction/exercise workflow.

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

All design sections approved; Option B selected. Five-stage EGM review completed with nine fresh reviewer runs. Nineteen raw findings map to fourteen consolidated actions, all now corrected in the author-accepted design at docs/designs/clinical-trial-criteria-explorer.md. The unsupported maintainer-link subclaim was contested and skipped. The applied design hash and acceptance are recorded in goldfish_review_report.md. No post-resolution independent re-audit/convergence, dataset collection, implementation, automated application tests, or measured evaluation scores are claimed. First-feature contracts C01/C02 are defined for the next coding session.
