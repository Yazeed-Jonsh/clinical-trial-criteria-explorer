"""End-to-end keyword search filters using synthetic snapshot records."""

import json
from contextlib import closing

import pytest

from trial_explorer import cli, ingest, snapshots, store


@pytest.fixture
def search_database(tmp_path, monkeypatch):
    records = []
    for number, status in enumerate(("RECRUITING", "COMPLETED", None), 1):
        protocol = {
            "identificationModule": {"nctId": f"NCT{number:08d}"},
            "eligibilityModule": {"eligibilityCriteria": "Age at least 18."},
        }
        if status is not None:
            protocol["statusModule"] = {"overallStatus": status}
        records.append({"protocolSection": protocol})
    body = json.dumps({"studies": records}).encode()
    monkeypatch.setattr(ingest, "fetch_studies_page", lambda token: body)
    path, manifest = snapshots.collect_snapshot(tmp_path / "raw")
    database = tmp_path / "trials.sqlite"
    with closing(store.connect_database(database)) as connection:
        store.import_snapshot(connection, path.parent)
    return database, manifest["snapshot_id"]


@pytest.mark.parametrize(
    ("filters", "expected_ids"),
    [
        ([], [1, 2, 3]),
        (["--nct-id", "NCT00000001"], [1]),
        (["--nct-id", "NCT00000001", "--nct-id", "NCT00000002"], [1, 2]),
        (["--recruitment-status", "RECRUITING"], [1]),
        (["--recruitment-status", "COMPLETED"], [2]),
        (["--recruitment-status", "RECRUITING", "--recruitment-status", "COMPLETED"], [1, 2]),
        (["--nct-id", "NCT00000001", "--nct-id", "NCT00000002",
          "--recruitment-status", "COMPLETED"], [2]),
        (["--nct-id", "NCT00000001", "--recruitment-status", "COMPLETED"], []),
    ],
)
def test_search_cli_filter_semantics(search_database, capsys, filters, expected_ids):
    database, snapshot_id = search_database
    arguments = [
        "search", "--db", str(database), "--snapshot-id", snapshot_id,
        "--query", "age", "--mode", "keyword",
    ]
    before = database.read_bytes()
    assert cli.main(arguments) == 0
    baseline = json.loads(capsys.readouterr().out)
    baseline_scores = {item["passage_id"]: item["score"] for item in baseline["results"]}

    assert cli.main(arguments + filters) == 0
    output = capsys.readouterr()
    response = json.loads(output.out)

    assert output.err == ""
    expected = [f"NCT{number:08d}" for number in expected_ids]
    assert [item["nct_id"] for item in response["results"]] == expected
    assert response["permitted_study_count"] == len(expected)
    assert response["permitted_passage_count"] == len(expected)
    assert response["returned_count"] == len(expected)
    assert response["exhaustive"] is False
    assert response["scope"]
    expected_filters = {}
    for option, key in (("--nct-id", "nct_ids"), ("--recruitment-status", "recruitment_statuses")):
        values = [filters[i + 1] for i, value in enumerate(filters) if value == option]
        if values:
            expected_filters[key] = values
    assert response["applied_filters"] == expected_filters
    for result in response["results"]:
        assert result["score"] == baseline_scores[result["passage_id"]]
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "filters",
    [
        ["--nct-id", "NCT99999999"],
        ["--nct-id", ""],
        ["--nct-id", "NCT00000001", "--nct-id", "NCT00000001"],
        ["--recruitment-status", "INVALID"],
        ["--recruitment-status", "RECRUITING", "--recruitment-status", "RECRUITING"],
        ["--nct-id", "NCT00000001"] * 51,
    ],
)
def test_search_cli_rejects_invalid_filters(search_database, capsys, filters):
    database, snapshot_id = search_database
    assert cli.main([
        "search", "--db", str(database), "--snapshot-id", snapshot_id,
        "--query", "age", *filters,
    ]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["error"] == "invalid_search"


@pytest.mark.parametrize("field", ["nct_ids", "recruitment_statuses"])
def test_search_helper_rejects_explicit_empty_filter(search_database, field):
    database, snapshot_id = search_database
    with closing(store.connect_database(database)) as connection:
        with pytest.raises(ValueError, match="1 to 50"):
            cli.keyword_search(connection, snapshot_id, "age", **{field: []})


def test_search_cli_rejects_overlong_query(search_database, capsys):
    database, snapshot_id = search_database
    assert cli.main([
        "search", "--db", str(database), "--snapshot-id", snapshot_id,
        "--query", "a" * 2001,
    ]) == 2
    assert json.loads(capsys.readouterr().err)["error"] == "invalid_search"
