# Planning context

- Author: Yazeed-Jonsh
- Date: 2026-11-07
- Last updated: 2026-11-08
- Source: the author's project planning conversation.
- Review state: conversation notes, not a completed EGM Goldfish review.

## Agreed intent

Build Clinical Trial Criteria Explorer first, then Repository Archaeologist. Learn by building small increments and publish reproducible evidence on GitHub to support applications for AI engineering roles.

## Constraints

- Aim for ten days with about one hour of work per day; additional time is possible.
- Prefer public data and free or inexpensive tools.
- Explain concepts and implementation decisions during each session.
- Follow an agentic software development lifecycle and use the EGM plugin.
- Preserve actual results; do not invent metrics or claim unfinished skills.

## Working scope from the Day 1 proposal

- Search trials, explain criteria, compare two trials, and cite supporting text.
- Start with about 50 type 2 diabetes studies. These are working defaults from the assistant's proposal, rather than an independently chosen clinical research cohort.
- Preserve study IDs, original criteria, update dates, and source links.
- Return an explicit missing-information response when evidence is absent.
- Use fictional examples for testing. Direct participation questions to the study contact.

## Planned learning

API ingestion, text preparation, embeddings, vector and keyword retrieval, filters, RAG, tool calling, state and context management, FastAPI, automated tests, evaluation, and observability.

Fine-tuning is outside the agreed first-project scope. The author selected Option B: local retrieval with hosted generation, including the shared SQLite, FAISS, BM25, FastAPI, and LangGraph foundation. The author approved the expanded Technical Plan with "yes I approve it". Ten hours is an effort target, not evidence that all planned features are feasible.

## Alternatives

The author chose B over A with "B is better". A used local generation; B uses hosted generation and local retrieval. No separate historical reason was supplied. In the later EGM resolution the author accepted a current engineering rationale: focus the first project on retrieval/evaluation without making local generation setup/performance a prerequisite, while controlling hosted credentials/network/cost obligations. This does not establish that local inference failed or invent the original motive. The existing ClinicalTrials.gov interface remains the product baseline.

## EGM handoff

This document was the predecessor for EGM drafting. The author approved Overview and Goals, selected Option B, approved Technical Plan, Alternatives, Detailed Implementation, and the final destination. A five-stage fresh-context review subsequently produced fourteen consolidated actions. The author accepted the complete EGM Resolve corrections with "auto accept" on 2026-11-08. Those corrections are applied to docs/designs/clinical-trial-criteria-explorer.md and synchronized to the working draft. See goldfish_review_report.md for traceability and the applied hash. No provider/model or spending cap is selected, and no independent post-resolution re-audit is claimed.

## Author's coding-session requirements

Explain purpose, architecture, and concepts before coding. Implement one small feature at a time. Wait for the author's prediction before running relevant tests. Explain changed files and data flow, provide one exercise without its solution, and use debugging hints before complete fixes. Include meaningful tests, evaluation, and documentation. Wait for explicit author approval before starting the next feature. These requirements apply during implementation and are saved in AGENTS.md.
