# Planning context

- Author: Yazeed-Jonsh
- Date: 2026-11-07
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

Fine-tuning is outside the agreed first-project scope. The author selected Option B: local retrieval with hosted generation, including the shared SQLite, FAISS, BM25, FastAPI, and LangGraph foundation. The expanded technical plan awaits section review. Ten hours is an effort target, not evidence that all planned features are feasible.

## Alternatives

The author chose B over A with "B is better". A used local generation; B uses hosted generation and local retrieval. The documented trade-offs include local hardware requirements versus network dependency, credentials, and usage costs. The author did not give a separate rejection rationale; do not invent one. The formal Alternatives section is pending.

## EGM handoff

Use this document as the predecessor for egm-draft. The author approved Overview and Goals in chat: "yes I approve them", then chose Option B: "B is better". The student/researcher reader, approximately 50 type 2 diabetes studies, and product boundaries are accepted. Completed Technical Plan approval is next. No provider/model or spending cap is selected, and no fresh-context review has run.
