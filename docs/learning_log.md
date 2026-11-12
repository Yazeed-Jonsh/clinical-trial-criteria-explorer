# Learning log

## Day 2 — Normalize one record (2026-11-10)

Feature state: implementation verified with 39 passing synthetic test cases. The initial disk/network setup blockers are cleared for this test run. Exercise and next-feature approval remain pending; do not mark the learning workflow complete.

Author prediction: normalization can succeed without the optional briefTitle; a missing required nctId must prevent a valid record. Observed result matches: test_missing_optional_title_is_none passes with title=None; test_missing_required_id_is_error passes with StudyNormalizationError(code="missing_required"). The normalizer raises an error rather than silently discarding a record; the later ingestion feature will decide how to record that rejection.

Explanation: nested dictionaries hold API input; the normalizer validates that boundary and constructs a frozen Study dataclass. Dataclass annotations do not enforce runtime types. The function does no I/O and preserves the original criteria text. Required-field failures raise a typed exception rather than silently discarding a record; ingestion can later catch and record that failure.

Files: pyproject.toml defines the minimal editable package and pytest dependency; models.py holds the internal record; normalize.py holds explicit validation; tests/test_normalize.py contains synthetic behavior/failure cases. Source paths/status values/date format were checked against the official ClinicalTrials.gov OpenAPI on 2026-11-10.

Environment: Python 3.12.7 at C:/msys64/ucrt64/bin/python.exe. This MSYS2 build creates .venv/bin/python.exe, not .venv/Scripts/python.exe. The first install command using Scripts failed without installing. The corrected install attempt could not launch because the execution helper could not write its setup log (Windows error112: insufficient disk space). A read-only disk-space diagnostic also failed to initialize for the same reason.

Verification completed after the author authorized missing-package downloads. The initial retry hit restricted network access; the author stopped it to request a local dependency inventory. The next authorized download hit the full default temporary drive. A process-local TEMP/TMP override to .venv/tmp on D: plus --no-cache-dir resolved that installation failure; no files were deleted. Existing build tools/packaging were exposed through process-local PYTHONPATH, not copied or globally modified. The editable project install used --no-index --no-deps --no-build-isolation, so it downloaded no build dependencies. See README for the exact test environment invocation.

Observed test command: .venv/bin/python.exe -m pytest tests/test_normalize.py -q with the documented local PYTHONPATH. Result: 39 passed in0.57s on Python3.12.7. These cases include exact text/input preservation, optional/required fields, criteria presence states, invalid nested objects/IDs/statuses/dates/timestamps/snapshot IDs, timezone conversion, deterministic error precedence, and frozen fields. No live data or model quality was evaluated.

Installed into project .venv: pytest9.2.0, colorama0.4.6, iniconfig2.3.1, pluggy1.7.0, pygments2.21.0. Reused from Codex's existing Python site-packages: setuptools84.1.0, wheel0.48.0, packaging26.3. The interpreter prefix was confirmed as this project's .venv. No pip upgrade was requested or performed.

Exercise completed with guidance: after hints and further teaching, the author added the supplied empty-title example and explicitly requested execution. All 40 cases passed in0.54s, including test_supplied_empty_title. This is guided completion, not independent test authoring. No separate empty-title prediction was supplied before the explicit run request. Next-feature approval remains pending.

Dependency inventory after the author freed space: the project environment contains pip24.2 but no pytest/setuptools/wheel; its pip cache is empty. Global MSYS2 Python has no pip, pytest or setuptools. The Windows Python launcher reports no registered Python installations. Codex's bundled CPython3.12.14 has setuptools84.1.0, wheel0.48.0 and packaging26.3, but no pytest, pluggy, iniconfig, colorama or pygments. No compatible pytest was found in the checked installations/cache locations; this is not a claim that every folder on the device was searched. The resumed installation failed on restricted network access; its escalated retry was rejected before execution. No dependencies were downloaded by these checks. The author's instruction to inventory local dependencies before downloading is saved in AGENTS.md.

## Day 3 - Build the study request (2026-11-13)

The author approved starting Day 3. First increment: build the fixed C04 URL with Python's standard-library URL encoder. URL construction is independent of HTTP so the first-page request contract can be tested offline. No dependencies were added and no study records were fetched. Test prediction and execution are pending. Exercise: add a continuation-token test with reserved characters; attempt pending.

The author requested hands-on implementation guidance in place of prediction quizzes. They wrote the continuation-token test with line-by-line guidance. Both offline URL tests passed in 0.10s; no HTTP requests were made by the tests. The next increment, fetching one page, has not started.

The author approved fetching one page and implemented fetch_studies_page with line-by-line guidance. At the author's request, added an offline pytest check using monkeypatch and BytesIO. It verifies the continuation URL and timeout argument, exact response bytes, and response closure. Full suite: 43 passed in 1.28s. No live request or package installation. Parsing and validation have not started.

The author implemented parse_studies_page with line-by-line guidance. Added offline checks that a valid empty studies list preserves the continuation token and that invalid JSON, a non-object, and missing or wrongly typed studies fields fail. Full suite: 49 passed in 0.39s. The parser does not yet validate tokens or individual studies. Pagination has not started.

The author implemented continuation-token validation with line-by-line guidance. Offline tests verify that an absent token is allowed, a valid token is preserved, and null, numeric, empty, or whitespace-only tokens are rejected. Full suite: 54 passed in 0.42s. No live request; pagination has not started.

The author implemented the bounded iter_studies_pages generator with line-by-line guidance. Two offline tests verify it follows a token from an empty page, preserves raw bytes beside the parsed page, stops at an absent token, and makes at most four requests. Full suite: 56 passed in 0.29s. No live request. Repeated-token detection remains pending.

The author implemented repeated-token detection with a set. Two offline cases verify that a repeated token on page three or four raises after yielding the page bytes, with no duplicate fetch. Full suite: 58 passed in 0.19s. Retries and snapshot persistence have not started.

The author implemented the HTTP status retry policy using a frozenset. Nine offline cases verify the five allowed statuses and representative exclusions, including HTTP 408 and 501. Full suite: 67 passed in 0.56s. The fetcher still makes one attempt; retry execution and timing have not been implemented.

The author implemented bounded HTTP retries. Three offline cases confirm recovery after 503 and 429, propagation after the third 503, and immediate propagation of 404. The tests verify the same URL and 20-second timeout argument for each request and record the one- and two-second delays with a fake sleep. Full suite: 70 passed in 0.34s. Retry-After and connection failure handling are pending.

The author wrote the Retry-After parser and asked for help completing the fetcher integration. Eight offline cases cover HTTP dates, numeric delays, invalid values, zero, and the 30-second boundary. The fetcher propagates an HTTP error for a longer delay. Full suite: 78 passed in 0.91s. Network failure retries and partial snapshot persistence remain pending.

At the author's request, added retries for timeouts and transient connection failures in the existing three-attempt loop. Offline cases verify wrapped network recovery, a shared HTTP/network retry budget, and immediate propagation of a certificate error. Full suite: 81 passed in 0.51s.

Live selection run ctg_6c569c594b98486aa71bdab81af2dadb fetched four pages and 200 candidates. All 200 normalized and had nonblank criteria. No duplicate NCT IDs or rejected rows appeared. Selected the first 50 unique IDs in ascending order and checked each selected ID and exact criteria text against its saved raw page and row. Used the installed Windows CPython runtime after MSYS2 Python rejected the TLS certificate chain. Raw pages and processed selection are ignored by Git. A final snapshot manifest has not been written.
The live run manifest was reconstructed from the four preserved raw pages and selection outputs. Verified all page hashes, the manifest hash, and selected source locators. Exact start and completion timestamps were not captured by the original run; the manifest records them as null and includes observed page retrieval times.
Day 3 gap closed by request: the reusable fetch command produced complete live snapshot ctg_2fada7d5e2754fc19f8329f1e89d7a73 (four pages, 200 candidates, 50 selected). Verified UTC timestamp ordering, raw page and manifest hashes, and each selected source locator. Offline suite: 86 passed in 0.74s.
