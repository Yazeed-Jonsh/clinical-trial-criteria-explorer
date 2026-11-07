# Stage 9 — Implementation Readiness

Three fresh-context reviewers completed one report-only pass. Target docs/designs/clinical-trial-criteria-explorer.md, DetailedRange 208–336; full target read to establish existing contracts. No edits applied. No implementation tests run. Overall readiness reviewer verdict: not ready under EGM's zero-decision standard, including the immediate normalization feature. Later explicitly gated provider choices do not prevent normalization.

## Readiness — /root/egm_readiness

I9-1 — Major — First-feature normalization contract incomplete. Lines 228–230.

Study lists fields but does not define their types/nullability, timestamps, source-field paths, accepted NCT syntax, or malformed-input errors. Source verification is deferred until feature 2 (238). Before feature 1, specify the exact mapping, validation, source URL template, and exception/result contract with expected examples.

I9-2 — Major — First-feature environment choices delegated. Lines 226, 316–317.

Python range, build backend, model representation/dependency choice, and development dependencies remain unspecified, so the editable install and tests have no predetermined configuration. Select the minimal first-feature setup; retain later compatibility gates for later dependencies.

I9-3 — Major — Snapshot selection/failure semantics unspecified. Lines 238–244.

The actual condition query, ordering, usable-record rule, stop condition near 50 records, manifest schema, snapshot-ID generation, retry limits, and persistence of failed/partial fetches are not defined. Specify these before feature 2; not a blocker for feature 1.

I9-4 — Major — Passage and storage contracts require design work. Lines 248–254.

Segmentation, ambiguous grouping, ID encoding, SQL schema, uniqueness/conflict behavior, and version handling allow incompatible implementations. Supply deterministic offset/segmentation examples, ID formula, schema and transaction/conflict rules before feature 3.

I9-5 — Major — Retrieval/evaluation behavior not predetermined. Lines 258–272.

BM25 tokenization/scoring, ties, fusion constant, candidate depths and permitted filters are absent. Evaluation cases lack an explicit query field; recall@5 does not define its unit or equation. Specify inputs/configuration, ordering, query-containing case schema, metric and exclusions before features 4–5. Embedding selection can remain a staged prerequisite.

I9-6 — Major — Provider-independent response/workflow contracts missing. Lines 276–292.

Provider selection may be deferred, but offline fakes still need adapter/request/claim/tool/state schemas and errors. Graph/call limits and unknown-tool versus fallback transitions remain incomplete. Cost reservations lack atomicity and concurrent session-cap behavior. Specify interfaces, state transitions, default limits and reservation transactions before features 6–7; prices and provider-specific limits may remain gated.

I9-7 — Major — API/CLI names lack executable contracts. Lines 296–300, 321.

Request/response schemas, defaults, filters, pagination, session creation/resumption, HTTP errors, input bounds and CLI option syntax are absent. Specify contracts and concrete examples before feature 8, and CLI signatures before earlier CLI introduction.

Required reads completed: installed implementation_readiness persona, implementation-readiness standard, full target (with supplementary read to recover output truncation), discussion_summary.md. No other documents, URLs, writes or tests.

## Codebase details — /root/egm_codebase

K9-1 — Major — First-feature contract has no existing implementation to fill its gaps. Lines 226–230, 238.

Confirms I9-1: define source-key mapping, types/nullability, identifiers, missing/null/empty criteria distinction, and error contract before normalization. Synthetic fixtures must reflect that contract.

K9-2 — Major — Shared fake-adapter test infrastructure lacks a contract. Lines 276–284, 292.

tests/fakes.py is referenced without an explicit creation action or interface. Neither it nor providers/base.py has signatures or response/error/usage sequencing rules. Explicitly create the fake and define deterministic scripted multi-call responses, provider failures, unknown usage, and prohibition of network access. Applies to features 6–9.

K9-3 — Nit — File-action labels drifted during finalization. Lines 276, 284, 310.

docs/designs/SITEMAP.md now exists, making its planned Create action stale. docs/model_decisions.md is absent but only receives record/update instructions. Mark the sitemap Modify if needed and the model-decision document Create at its prerequisite milestone.

Reads/searches completed: codebase_details persona, implementation-readiness standard, full target, discussion_summary.md, and .gitignore as configuration for the source inventory. rg inventory and searches for normalization, Study, fake adapters, pytest, project config and LangGraph found no implementation source. Proposed file absence is not a finding. Other documentation was inventoried without being read. No other reports, URLs, history, writes or tests.

## Implementation style — /root/egm_implementation_style

T9-1 — Major — Embedding selection/download sequence is circular. Line 268.

The plan asks to choose the model before downloads using a measured sample, without distinguishing a provisional candidate from final selection. Sequence metadata/compatibility screening, a bounded candidate download/sample benchmark, and recorded final selection explicitly.

The initial return omitted the supplied predecessor read and was not counted complete. On follow-up the reviewer read discussion_summary.md in full and returned the same finding. Final required reads completed: style persona, entire target, predecessor. No other documents, reports, URLs, history, writes or tests.

## Execution evidence

Plugin root: C:/Users/hp/.codex/plugins/cache/openai-curated-remote/egm/0.1.1. All reviewers used fork_turns=none; host instruction-file exclusion remains unverified. No missing reviewers remain. This is an audit, not a remediation/convergence claim.
