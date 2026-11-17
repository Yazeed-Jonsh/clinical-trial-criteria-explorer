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

def load_snapshot_manifest(directory: Path) -> dict:
    """Read a complete snapshot manifest and verify its hash."""
    manifest = json.loads((directory / "manifest.json").read_bytes())

    if not isinstance(manifest, dict):
        raise ValueError("Expected a manifest object")
    if type(manifest.get("schema_version")) is not int:
        raise ValueError("Invalid manifest schema version")
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported manifest schema version")
    if manifest.get("fetch_status") != "complete":
        raise ValueError("Only complete snapshots can be imported")

    stored_hash = manifest.get("manifest_sha256")
    content = {
        key: value
        for key, value in manifest.items()
        if key != "manifest_sha256"
    }
    actual_hash = _hash(canonical_json(content))

    if stored_hash != actual_hash:
        raise ValueError("Manifest hash mismatch")

    return manifest

def load_verified_pages(directory: Path, manifest: dict) -> list[dict]:
    """Read saved pages after checking their filenames and byte hashes."""
    verified_pages = []

    for number, page_info in enumerate(manifest["pages"], start=1):
        expected_filename = f"page-{number:02d}.json"

        if page_info.get("filename") != expected_filename:
            raise ValueError("Unexpected raw page filename")

        body = (directory / expected_filename).read_bytes()
        if _hash(body) != page_info.get("sha256"):
            raise ValueError(f"Raw page hash mismatch: {expected_filename}")

        page = ingest.parse_studies_page(body)
        verified_pages.append(page)

    return verified_pages

def load_selected_studies(directory: Path, *, manifest: dict | None = None) -> list[Study]:
    """Load selected studies from verified snapshot files."""
    if manifest is None:
        manifest = load_snapshot_manifest(directory)
    pages = load_verified_pages(directory, manifest)
    studies: list[Study] = []

    for selected in manifest["selected_records"]:
        page_number = selected["page"]
        row_number = selected["row"]

        if type(page_number) is not int or not 1 <= page_number <= len(pages):
            raise ValueError("Selected page is out of range")

        records = pages[page_number - 1]["studies"]
        if type(row_number) is not int or not 1 <= row_number <= len(records):
            raise ValueError("Selected row is out of range")

        raw_record = records[row_number - 1]

        page_info = manifest["pages"][page_number - 1]
        retrieved_at = datetime.fromisoformat(page_info["retrieved_at"])

        study = normalize_study(
            raw_record,
            retrieved_at=retrieved_at,
            snapshot_id=manifest["snapshot_id"],
        )

        if study.nct_id != selected["nct_id"]:
            raise ValueError("Selected study ID does not match its source record")

        if not (study.criteria_text or "").strip():
            raise ValueError("Selected study has no usable criteria")

        studies.append(study)
    selected_ids = [study.nct_id for study in studies]
    if selected_ids != sorted(set(selected_ids)):
        raise ValueError("Selected study IDs must be unique and sorted")
    if selected_ids != manifest.get("selected_ids"):
        raise ValueError("Selected IDs do not match the manifest")
    if type(manifest.get("selected_count")) is not int or manifest["selected_count"] != len(studies):
        raise ValueError("Selected count does not match loaded studies")
    if len(studies) > TARGET_COUNT:
        raise ValueError("Selection exceeds the target count")
    if type(manifest.get("target_met")) is not bool or manifest["target_met"] != (len(studies) == TARGET_COUNT):
        raise ValueError("Target flag does not match selected count")
    return studies
