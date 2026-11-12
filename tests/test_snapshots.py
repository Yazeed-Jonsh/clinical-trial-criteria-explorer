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
