# Clinical Trial Criteria Explorer

A learning project by Yazeed-Jonsh for exploring public clinical trial eligibility criteria with traceable evidence.

The planned application searches trial records, explains inclusion and exclusion criteria, and compares two studies. Each explanation points back to its supporting source text. Study teams determine participation eligibility.

## Current work

Day 3 snapshot collection is implemented and verified. The live command collected four pages and selected 50 usable studies. See the [learning log](docs/learning_log.md) for verification details.

- [Discussion context](discussion_summary.md): decisions and constraints from the planning conversation.
- [Approved design](docs/designs/clinical-trial-criteria-explorer.md): includes all fourteen accepted EGM corrections and exact implementation contracts.
- [EGM resolution](goldfish_review_report.md): accepted actions, contested subclaim, and applied design hash.
- [Consolidated EGM review](consolidated_review_report.md): historical findings against the earlier design revision; resolved in the linked resolution record.
- [Working draft](design_draft.md): synchronized copy with links adjusted for the project root.
- [Tasks and learning record](TASKS.md): progress and completion evidence.
- [Agent instructions](AGENTS.md): how coding sessions should work.

## Planned data

ClinicalTrials.gov public study records. The approved scope is about 50 type 2 diabetes studies selected from a saved bounded candidate window. The API source paths and supported query have been checked for the design; live collection and data-quality measurements follow normalization as a separately approved feature. Saved records retain identifiers and retrieval dates.

References:

- [API documentation](https://clinicaltrials.gov/data-api/api)
- [Study data structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure)
- [Participation and eligibility questions](https://clinicaltrials.gov/find-studies/for-patients/common-questions)

## Development approach

Use EGM to develop and review the design. Implement one small task at a time, verify observable behavior, review the change, and record evidence before committing a milestone. Budget: ten sessions of about one hour; actual effort will be recorded.

## Normalization data flow

`nested source dictionary -> normalize_study -> explicit field validation -> frozen Study`

[models.py](src/trial_explorer/models.py) defines the internal record. [normalize.py](src/trial_explorer/normalize.py) checks required IDs, optional text, source dates/statuses, snapshot IDs and timezone-aware retrieval timestamps. It preserves criteria text exactly and raises a typed error rather than returning a partial record. Dataclass annotations do not validate inputs on their own; untrusted data enters through the normalizer.

All [normalization tests](tests/test_normalize.py) use synthetic inputs. They verify boundary behavior and text preservation, not clinical validity or live-registry integration.

## Setup and tests

The project requires Python3.12. For a standalone environment, create a virtual environment and install the editable package with its development dependencies using that environment's interpreter: `python -m pip install -e ".[dev]"`. Then run `python -m pytest tests/test_normalize.py -q`. Standard Windows Python uses `.venv/Scripts/python.exe`; this computer's MSYS2 Python uses `.venv/bin/python.exe`.

This device reuses already-installed compatible build tools and `packaging` from Codex's bundled Python to avoid downloading copies. From PowerShell in the project directory, reproduce the verified test invocation with:

```powershell
$env:PYTHONPATH = 'C:\Users\hp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages'
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\bin\python.exe -m pytest tests/test_normalize.py -q
```

That local tooling path is an environment optimization, not an application dependency. If it moves, inventory compatible local packages again or use the standalone installation above. Tests do not modify sys.path or depend on a machine-specific path in source code.

Verified result: `40 passed in 0.54s`. Dependencies were installed with caching disabled and temporary files directed to `.venv/tmp` on D: because C: was short of space. Existing setuptools/wheel/packaging were reused; the project was installed editable with `--no-index --no-deps --no-build-isolation`. No global/tool-managed packages were altered. Exact versions and the earlier installation failures are recorded in the learning log.

## Collect a fresh snapshot

Run this from the project root with a Python 3.12 environment that trusts the site's TLS certificate chain:

```powershell
python -m trial_explorer.cli fetch --output-root data/raw
```

An installed package also provides the equivalent `trial-explorer fetch --output-root data/raw` command. Each invocation creates a new snapshot directory containing the original page bytes and a final `manifest.json`. The manifest records the query, page hashes, UTC timestamps, and selected NCT IDs with one-based raw page and row locations. The selection comes from at most four pages. The generated data is ignored by Git.

A completed fetch exits 0, including when fewer than 50 usable records are available. An HTTP, transport, or response error produces a partial manifest and exits 3. If writing fails before the final manifest is published, the directory is unfinished. On this machine the live run used Windows CPython with the Windows certificate store, after the MSYS2 environment rejected the TLS chain.
