"""Collect an immutable, bounded ClinicalTrials.gov snapshot."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

from trial_explorer import ingest
from trial_explorer.models import Study
from trial_explorer.normalize import StudyNormalizationError, normalize_study

TARGET_COUNT = 50


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _hash(data: bytes) -> str:
    return sha256(data).hexdigest()


def _write_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("xb") as output:
        output.write(data)
    temporary.replace(path)


def _save_page(directory, pages, body, request_token, page, retrieved_at):
    number = len(pages) + 1
    filename = f"page-{number:02d}.json"
    _write_atomic(directory / filename, body)
    pages.append({
        "page": number,
        "filename": filename,
        "retrieved_at": retrieved_at.isoformat(),
        "request_page_token": request_token,
        "response_next_page_token": page.get("nextPageToken") if page is not None else None,
        "candidate_count": len(page["studies"]) if page is not None else 0,
        "sha256": _hash(body),
        "byte_count": len(body),
        "parsed": page is not None,
    })


def collect_snapshot(output_root: Path) -> tuple[Path, dict]:
    """Write a new snapshot and return its manifest path and contents."""
    started_at = datetime.now(UTC)
    snapshot_id = f"ctg_{uuid4().hex}"
    directory = output_root / snapshot_id
    # Reserve the ID. Without a final manifest this directory is unfinished.
    directory.mkdir(parents=True, exist_ok=False)
    pages = []
    rejected = []
    duplicates = []
    winners: dict[str, tuple[Study, str, dict]] = {}
    request_token = None
    failure = None
    iterator = ingest.iter_studies_pages()

    while True:
        try:
            body, page = next(iterator)
        except StopIteration:
            break
        except ingest.PageSchemaError as error:
            _save_page(directory, pages, error.body, request_token, None, datetime.now(UTC))
            failure = ("invalid_page", f"pages[{len(pages)}]")
            break
        except (OSError, HTTPException) as error:
            code = f"http_{error.code}" if isinstance(error, HTTPError) else "network_error"
            if isinstance(error, HTTPError):
                error.close()
            failure = (code, f"pages[{len(pages) + 1}]")
            break
        except ValueError:
            failure = ("repeated_token", f"pages[{len(pages)}].nextPageToken")
            break

        retrieved_at = datetime.now(UTC)
        _save_page(directory, pages, body, request_token, page, retrieved_at)
        request_token = page.get("nextPageToken")
        for row, record in enumerate(page["studies"], 1):
            locator = {"page": len(pages), "row": row}
            try:
                study = normalize_study(record, retrieved_at, snapshot_id)
            except StudyNormalizationError as error:
                rejected.append({**locator, "code": error.code, "path": error.path})
                continue
            if not (study.criteria_text or "").strip():
                rejected.append({**locator, "code": "blank_criteria", "nct_id": study.nct_id})
                continue
            try:
                record_hash = _hash(canonical_json(record))
            except (ValueError, UnicodeError):
                rejected.append({**locator, "code": "invalid_canonical_json", "nct_id": study.nct_id})
                continue

            prior = winners.get(study.nct_id)
            if prior is not None:
                previous, previous_hash, previous_locator = prior
                old_date = previous.source_updated_at or ""
                new_date = study.source_updated_at or ""
                replace = new_date > old_date or (new_date == old_date and record_hash < previous_hash)
                duplicates.append({
                    "nct_id": study.nct_id,
                    **(previous_locator if replace else locator),
                })
                if not replace:
                    continue
            winners[study.nct_id] = study, record_hash, locator

    selected_ids = sorted(winners)[:TARGET_COUNT]
    url = urlsplit(ingest.build_studies_url())
    manifest = {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "endpoint": ingest.STUDIES_ENDPOINT,
        "method": "GET",
        "query_params": dict(parse_qsl(url.query)),
        "page_cap": ingest.PAGE_CAP,
        "max_attempts_per_page": ingest.MAX_ATTEMPTS,
        "http_timeout_seconds": ingest.HTTP_TIMEOUT_SECONDS,
        "pages": pages,
        "page_count": len(pages),
        "candidate_count": sum(page["candidate_count"] for page in pages),
        "unique_usable_count": len(winners),
        "selected_ids": selected_ids,
        "selected_records": [
            {"nct_id": nct_id, **winners[nct_id][2]} for nct_id in selected_ids
        ],
        "rejected_count": len(rejected),
        "rejections": rejected,
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
        "selection_rule_version": "c04-v1",
        "target_count": TARGET_COUNT,
        "selected_count": len(selected_ids),
        "target_met": len(selected_ids) == TARGET_COUNT,
        "stop_reason": "page_cap" if request_token is not None else "api_end",
        "fetch_status": "complete",
    }
    if failure is not None:
        manifest.update(
            fetch_status="partial", stop_reason="fetch_error",
            error_code=failure[0], error_path=failure[1],
        )

    manifest["manifest_sha256"] = _hash(canonical_json(manifest))
    path = directory / "manifest.json"
    _write_atomic(path, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode())
    return path, manifest
