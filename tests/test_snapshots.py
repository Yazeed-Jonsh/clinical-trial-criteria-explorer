import json
from datetime import datetime
from hashlib import sha256
from urllib.error import URLError

import pytest

from trial_explorer import cli, ingest, snapshots


def study(nct_id, date="2026-01-01", criteria="Eligible"):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct_id},
        "eligibilityModule": {"eligibilityCriteria": criteria},
        "statusModule": {"lastUpdatePostDateStruct": {"date": date}},
    }}


def test_fetch_writes_complete_snapshot(tmp_path, monkeypatch, capsys):
    rows = [study(f"NCT{number:08d}") for number in range(52, 0, -1)]
    rows += [study("NCT00000001", "2026-02-01"), study("NCT00000053", criteria="  "), {}]
    raw = json.dumps({"studies": rows}).encode() + b"\n"
    monkeypatch.setattr(ingest, "fetch_studies_page", lambda token: raw)

    assert cli.main(["fetch", "--output-root", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    directory = tmp_path / result["snapshot_id"]
    manifest = json.loads((directory / "manifest.json").read_bytes())
    assert result["fetch_status"] == "complete"
    assert manifest["stop_reason"] == "api_end"
    assert manifest["target_met"]
    assert manifest["selected_ids"] == [f"NCT{number:08d}" for number in range(1, 51)]
    assert manifest["selected_records"][0] == {"nct_id": "NCT00000001", "page": 1, "row": 53}
    assert manifest["duplicate_count"] == 1
    assert manifest["rejected_count"] == 2
    assert datetime.fromisoformat(manifest["started_at"]) <= datetime.fromisoformat(
        manifest["pages"][0]["retrieved_at"]
    ) <= datetime.fromisoformat(manifest["completed_at"])
    assert (directory / "page-01.json").read_bytes() == raw
    assert manifest["pages"][0]["sha256"] == sha256(raw).hexdigest()
    assert manifest.pop("manifest_sha256") == sha256(snapshots.canonical_json(manifest)).hexdigest()


@pytest.mark.parametrize(
    ("second", "error_code", "page_count"),
    [
        (None, "network_error", 1),
        (b"invalid json", "invalid_page", 2),
        (b'{"studies": [], "nextPageToken": "next"}', "repeated_token", 2),
    ],
)
def test_fetch_preserves_partial_snapshot(tmp_path, monkeypatch, capsys, second, error_code, page_count):
    first = b'{"studies": [], "nextPageToken": "next"}'

    def fake_fetch(token):
        if token is None:
            return first
        assert token == "next"
        if second is None:
            raise URLError(TimeoutError())
        return second

    monkeypatch.setattr(ingest, "fetch_studies_page", fake_fetch)
    assert cli.main(["fetch", "--output-root", str(tmp_path)]) == 3
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["fetch_status"] == "partial"
    assert json.loads(captured.err)["error"] == error_code
    directory = tmp_path / result["snapshot_id"]
    manifest = json.loads((directory / "manifest.json").read_bytes())
    assert manifest["stop_reason"] == "fetch_error"
    assert manifest["page_count"] == page_count
    assert (directory / "page-01.json").read_bytes() == first
    if second is not None:
        assert (directory / "page-02.json").read_bytes() == second


def test_snapshot_refuses_existing_id(tmp_path, monkeypatch):
    from uuid import UUID

    identifier = UUID(int=0)
    directory = tmp_path / f"ctg_{identifier.hex}"
    directory.mkdir()
    manifest = directory / "manifest.json"
    manifest.write_bytes(b"original")
    monkeypatch.setattr(snapshots, "uuid4", lambda: identifier)

    with pytest.raises(FileExistsError):
        snapshots.collect_snapshot(tmp_path)
    assert manifest.read_bytes() == b"original"


@pytest.mark.parametrize("case", ["valid", "edited", "partial"])
def test_load_snapshot_manifest_validates_saved_run(tmp_path, monkeypatch, case):
    def fake_fetch(token):
        if case == "partial":
            raise URLError(TimeoutError("simulated timeout"))
        return b'{"studies": []}'

    monkeypatch.setattr(ingest, "fetch_studies_page", fake_fetch)
    path, manifest = snapshots.collect_snapshot(tmp_path)
    original_bytes = path.read_bytes()

    if case == "valid":
        assert snapshots.load_snapshot_manifest(path.parent) == manifest
        assert path.read_bytes() == original_bytes
        assert manifest["selected_count"] == 0
        assert manifest["target_met"] is False
    elif case == "edited":
        manifest["selected_count"] = 1
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="Manifest hash mismatch"):
            snapshots.load_snapshot_manifest(path.parent)
    else:
        with pytest.raises(ValueError, match="Only complete snapshots"):
            snapshots.load_snapshot_manifest(path.parent)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ([], "Expected a manifest object"),
        ({"schema_version": True}, "Invalid manifest schema version"),
        ({"schema_version": 2}, "Unsupported manifest schema version"),
    ],
)
def test_load_snapshot_manifest_rejects_unsupported_format(tmp_path, body, message):
    (tmp_path / "manifest.json").write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        snapshots.load_snapshot_manifest(tmp_path)


@pytest.mark.parametrize("case", ["valid", "altered", "unexpected_filename"])
def test_load_verified_pages_checks_saved_bytes(tmp_path, monkeypatch, case):
    body = b'{ "studies": [] }\n'
    monkeypatch.setattr(ingest, "fetch_studies_page", lambda token: body)
    path, _ = snapshots.collect_snapshot(tmp_path)
    manifest = snapshots.load_snapshot_manifest(path.parent)

    if case == "valid":
        assert snapshots.load_verified_pages(path.parent, manifest) == [{"studies": []}]
        assert (path.parent / "page-01.json").read_bytes() == body
    elif case == "altered":
        (path.parent / "page-01.json").write_bytes(b'{"studies": []}')
        with pytest.raises(ValueError, match="Raw page hash mismatch"):
            snapshots.load_verified_pages(path.parent, manifest)
    else:
        manifest["pages"][0]["filename"] = "../another-file.json"
        with pytest.raises(ValueError, match="Unexpected raw page filename"):
            snapshots.load_verified_pages(path.parent, manifest)


@pytest.fixture
def saved_selection(tmp_path, monkeypatch):
    criteria = "Inclusion Criteria:\n- Age \u2265 18.\n"
    body = json.dumps({"studies": [study("NCT00000001", criteria=criteria)]}).encode()
    monkeypatch.setattr(ingest, "fetch_studies_page", lambda token: body)
    path, manifest = snapshots.collect_snapshot(tmp_path)
    return path, manifest, criteria


def test_load_selected_studies_preserves_source_and_provenance(saved_selection):
    path, manifest, criteria = saved_selection

    loaded = snapshots.load_selected_studies(path.parent)

    assert len(loaded) == 1
    assert loaded[0].nct_id == "NCT00000001"
    assert loaded[0].criteria_text == criteria
    assert loaded[0].snapshot_id == manifest["snapshot_id"]
    assert loaded[0].retrieved_at == datetime.fromisoformat(manifest["pages"][0]["retrieved_at"])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("nct_id", "NCT00000002", "Selected study ID"),
        ("page", 0, "Selected page"),
        ("page", 2, "Selected page"),
        ("page", True, "Selected page"),
        ("row", 0, "Selected row"),
        ("row", 2, "Selected row"),
        ("row", True, "Selected row"),
    ],
)
def test_load_selected_studies_rejects_bad_locator(saved_selection, field, value, message):
    path, manifest, _ = saved_selection
    manifest["selected_records"][0][field] = value
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = sha256(snapshots.canonical_json(manifest)).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        snapshots.load_selected_studies(path.parent)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("selected_ids", [], "Selected IDs"),
        ("selected_count", 2, "Selected count"),
        ("target_met", True, "Target flag"),
    ],
)
def test_selection_metadata_must_match_loaded_records(saved_selection, field, value, message):
    path, manifest, _ = saved_selection
    manifest[field] = value
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = sha256(snapshots.canonical_json(manifest)).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        snapshots.load_selected_studies(path.parent)
