# Clinical Trial Criteria Explorer

Explore public clinical trial eligibility criteria with traceable source evidence.

The project currently collects ClinicalTrials.gov records, preserves raw responses, extracts exact-text passages, and stores verified snapshots in SQLite. Retrieval and generated explanations are planned next. Study teams determine participation eligibility.

## Current capabilities

- Fetch up to four pages of type 2 diabetes studies, with timeouts and bounded retries.
- Normalize records, deduplicate by NCT ID, and select up to 50 usable studies.
- Preserve raw responses and a manifest with query parameters, timestamps, file hashes, and selected source locations.
- Split criteria into paragraphs while retaining full parent sections, original character offsets, and stable passage IDs.
- Import complete snapshots into SQLite in one transaction. Repeated imports verify stored values before succeeding without duplicate writes.
- Read a study and its ordered passages within an explicit snapshot.

Selection is deterministic within the saved candidate window. This bounded sample is not an exhaustive registry search.

## Setup

Use Python 3.12. Create a virtual environment, activate it, and install the project with test dependencies:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
```

The activation path above is for Git Bash with standard Windows Python. Linux, macOS, and MSYS2 environments use `source .venv/bin/activate`.

The application currently uses Python's standard library, including SQLite. Pytest supplies the automated tests.

## Collect a snapshot

```bash
python -m trial_explorer.cli fetch --output-root data/raw
```

The command reports a new snapshot ID and manifest path. Each snapshot contains the original response bytes and a final `manifest.json`. The manifest links selected NCT IDs to one-based raw page and row locations.

A successful bounded run has `fetch_status="complete"`, with stop reason `api_end` or `page_cap`. `target_met` separately indicates whether 50 usable studies were found. A request or response failure preserves a partial snapshot and exits with code 3. A directory without a final manifest is unfinished.

Live collection requires internet access and a Python environment with a valid TLS trust store.

## Import into SQLite

Create the output directory, then replace `SNAPSHOT_ID` with the ID returned by the fetch command:

```bash
mkdir -p data/processed
python -m trial_explorer.cli import-snapshot \
  --snapshot data/raw/SNAPSHOT_ID \
  --db data/processed/trials.sqlite
```

The importer verifies the manifest hash, raw page hashes, selected study locations, and normalization rules. It then stores snapshot provenance, studies, and passages together. Passage and parent text must match exact source slices. A failed insertion rolls back the complete import. Reimporting requires matching snapshot metadata and all stored study and passage values.

Exit codes are 0 for success, 2 for invalid snapshot data, and 3 for file or database failures. Downloaded records and local SQLite databases are ignored by Git.

## Read stored evidence

Read one study from Git Bash:

```bash
python -m trial_explorer.cli read-study \
  --db data/processed/trials.sqlite \
  --snapshot-id SNAPSHOT_ID --nct-id NCT00000001
```

Read its first passage, including parent context and original-text offsets:

```bash
python -m trial_explorer.cli read-passages \
  --db data/processed/trials.sqlite \
  --snapshot-id SNAPSHOT_ID --nct-id NCT00000001 --limit 1
```

Use IDs present in your imported snapshot. Omit `--limit` to read all its passages in source order. Both commands open SQLite read-only and print formatted JSON. Missing studies exit 2 with `study_not_found`. Database failures exit 3.

Each passage retains its full enclosing section so exceptions can remain available during later context assembly.

## Data flow

`ClinicalTrials.gov → raw pages and manifest → normalized studies → exact-text passages → SQLite → CLI reads`

- `ingest.py` builds requests, handles retries, and follows continuation tokens.
- `normalize.py` validates source records and preserves their criteria text.
- `snapshots.py` collects snapshots, records selection provenance, and verifies saved inputs.
- `passages.py` extracts paragraphs with original-text offsets and parent context.
- `store.py` manages versioned SQLite tables, transactional imports, and snapshot-scoped reads.
- `cli.py` exposes the fetch, import, and read commands.

## Planned work

Keyword retrieval, embeddings and hybrid search, cited RAG responses, evaluation, and an API service.

## Verification

```bash
python -m pytest -q
```

Verified result: **158 tests passed**. Synthetic tests cover normalization, request and retry behavior, snapshot integrity, passage boundaries and IDs, transactional rollback, duplicate handling, CLI import, and isolation between snapshots.

A separate live collection retrieved 200 records from four pages and selected 50 studies. Import produced 190 passages. File and manifest hashes, database integrity, foreign keys, and every passage's exact source slices were verified. Live collection counts can change as the registry updates.

## Source

- [ClinicalTrials.gov API documentation](https://clinicaltrials.gov/data-api/api)
- [Study data structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure)
- [Participation and eligibility questions](https://clinicaltrials.gov/find-studies/for-patients/common-questions)
