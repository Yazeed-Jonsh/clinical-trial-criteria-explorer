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

## Keyword search

```bash
python -m trial_explorer.cli search \
  --db data/processed/trials.sqlite \
  --snapshot-id SNAPSHOT_ID --query "minimum age" --mode keyword
```

Add `--nct-id NCT_ID` or `--recruitment-status RECRUITING` to narrow the search. Repeat either flag for multiple values. Values within each filter use OR; the two filters combine with AND. IDs must exist in the requested snapshot. Duplicate, unknown, or excessive filter values fail validation. A valid combination matching zero studies returns an empty result.

BM25 uses lexical-v1 Unicode normalization, preserves numeric comparisons and decimals, and uses k1=1.2 and b=0.75. For each distinct query term, its contribution is `IDF * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / average_length))`, with `IDF = ln(1 + (N - df + 0.5) / (df + 0.5))`. Statistics use all passages in the snapshot. Filters restrict candidates before the top-five cutoff. Equal scores sort by study ID, source offset, and passage ID.

Responses include scores, exact source text, parent context, source links, applied filters, and permitted study/passage counts. Search scores express keyword relevance. Initial retrieval evaluation is described below.

## Build a vector index

With the `vector` dependencies installed and the local MiniLM model downloaded, run:

```bash
python -m trial_explorer.cli build-index \
  --db data/processed/trials.sqlite \
  --snapshot-id SNAPSHOT_ID --model-dir MODEL_DIR \
  --index-dir indexes/SNAPSHOT_ID/minilm
```

Use the downloaded revision directory containing `tokenizer.json` and `onnx/model.onnx` as `MODEL_DIR`.
The command requires a new output directory and reports the passage IDs that exceeded the model's token limit.

Hybrid search is available through `search --mode hybrid --index-dir INDEX_DIR --model-dir MODEL_DIR`.
Use `--mode vector` with the same directories to rank by FAISS cosine similarity alone.
It requires the optional `vector` dependencies, a locally built FAISS index, and the matching MiniLM revision.
BM25 and FAISS each contribute up to 20 candidates after study filters are applied.
Reciprocal rank fusion adds `1 / (60 + rank)` for each list containing a passage and returns the top five.
On nine positive development checks, all three modes achieved macro recall@5 of 0.889.
Keyword and hybrid missed the weight-stability passage. Vector found it but missed the 90-day GLP-1 passage.
The CLI benchmark measured median search latency across 27 positive calls per mode: 10.66 ms for keyword, 588.06 ms for vector, and 646.84 ms for hybrid.
These local timings include model and index setup on each vector or hybrid call and exclude CLI startup and JSON printing.
The held-out split remains reserved.

## Evaluate retrieval

```bash
python -m trial_explorer.cli evaluate-retrieval \
  --db data/processed/trials.sqlite \
  --snapshot-id SNAPSHOT_ID \
  --cases eval/dev.jsonl \
  --output data/processed/keyword-evaluation.json --mode keyword --repeats 3
```

Each JSONL case labels source passage IDs and exact quotes. All cases are validated against the database before retrieval runs. The report includes hits, missing evidence, numerators, denominators, and recall@5. Comparison checks run independently for each study. Absent and not-applicable checks are excluded from positive recall and reported explicitly. Real and synthetic aggregates are separate. Zero positive checks produce a null score.

To compare modes, rerun the command with `--mode vector` and `--mode hybrid`, using the same cases and snapshot. Add `--index-dir INDEX_DIR --model-dir MODEL_DIR` for both modes and use a distinct output filename for each run. `--repeats 3` records three search timings per check. The summary median uses only positive checks and includes model and index setup where applicable.

The report records the source manifest hash, case hash, and search configuration. Existing output files are never overwritten. Invalid labels exit 5. File or database errors exit 3. Generated reports remain local under the ignored data directory.

The final Day 5 development baseline contains **9 real-record cases and 10 retrieval checks**, including three snapshot-wide searches. **Macro recall@5 was 0.889 across 9 positive checks**; one absence check was excluded. Eight positive checks found all their labeled evidence. The weight-stability query retrieved the correct study but missed its labeled threshold passage. The newer global labels were added after exploratory searches and are development diagnostics.

The final report is generated locally at `data/processed/keyword-evaluation-development-final.json`. To reproduce it, use that path as `--output` on the evaluation command above, choosing a new filename if it already exists.

**10 held-out real-record cases** are stored in `eval/cases.heldout.jsonl`. Their source quotes, scope, and schema were validated, but retrieval has not been run on them. `eval/heldout.lock.json` records their file SHA-256 and source snapshot hash. Reserve this split for final evaluation and use only `eval/dev.jsonl` while improving retrieval.

The development set remains at nine cases by author choice, below the original target of fifteen. The author approved the first age label and requested skipping additional independent label review. Other labels were source-checked by the assistant. These sample sizes, label-review limits, and development-time exploration constrain conclusions about retrieval quality. Absence cases are not measured by positive recall@5.

## Data flow

`ClinicalTrials.gov → raw pages and manifest → normalized studies → exact-text passages → SQLite → CLI reads`

- `ingest.py` builds requests, handles retries, and follows continuation tokens.
- `normalize.py` validates source records and preserves their criteria text.
- `snapshots.py` collects snapshots, records selection provenance, and verifies saved inputs.
- `passages.py` extracts paragraphs with original-text offsets and parent context.
- `store.py` manages versioned SQLite tables, transactional imports, and snapshot-scoped reads.
- `cli.py` exposes the fetch, import, and read commands.

## Planned work

Embeddings and hybrid search, cited RAG responses, evaluation, and an API service.

## Verification

```bash
python -m pytest -q
```

Verified result: **280 tests passed**. Synthetic tests cover normalization, request and retry behavior, snapshot integrity, passage boundaries and IDs, transactional rollback, duplicate handling, CLI import, snapshot isolation, BM25 ranking, and search filter behavior.

A separate live collection retrieved 200 records from four pages and selected 50 studies. Import produced 190 passages. File and manifest hashes, database integrity, foreign keys, and every passage's exact source slices were verified. Live collection counts can change as the registry updates.

## Source

- [ClinicalTrials.gov API documentation](https://clinicaltrials.gov/data-api/api)
- [Study data structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure)
- [Participation and eligibility questions](https://clinicaltrials.gov/find-studies/for-patients/common-questions)
