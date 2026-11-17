"""Verify SQLite connection behavior using temporary database files."""

import sqlite3
from contextlib import closing

import pytest

from trial_explorer.store import connect_database


def test_database_connection_enforces_foreign_keys_on_every_open(tmp_path):
    path = tmp_path / "trials.sqlite"

    with closing(connect_database(path)) as connection:
        assert path.is_file()
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
        connection.execute("CREATE TABLE parents (id TEXT PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE children (parent_id TEXT REFERENCES parents(id))"
        )
        connection.commit()

    with closing(connect_database(path)) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO children (parent_id) VALUES (?)", ("missing",)
            )


def test_initialize_creates_schema_and_can_run_twice(tmp_path):
    from trial_explorer.store import initialize_database

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        initialize_database(connection)
        connection.execute(
            "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?)",
            ("sample", "hash", "2026-11-18T00:00:00+00:00", "complete", 0, "{}"),
        )
        connection.commit()

        initialize_database(connection)

        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table'"
            )
        }
        assert tables == {"snapshots", "studies", "passages"}
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("SELECT snapshot_id FROM snapshots").fetchall() == [("sample",)]
        assert not connection.in_transaction


def test_initialize_rolls_back_failed_schema_creation(tmp_path, monkeypatch):
    from trial_explorer import store

    monkeypatch.setattr(store, "PASSAGES_TABLE_SQL", "INVALID SQL")
    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        with pytest.raises(sqlite3.OperationalError):
            store.initialize_database(connection)

        assert connection.execute("PRAGMA user_version").fetchone() == (0,)
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table'"
        ).fetchall() == []
        assert not connection.in_transaction


@pytest.mark.parametrize("version,existing_table", [(2, False), (0, True)])
def test_initialize_rejects_migration_without_changes(tmp_path, version, existing_table):
    from trial_explorer.store import initialize_database

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        connection.execute(f"PRAGMA user_version = {version}")
        if existing_table:
            connection.execute("CREATE TABLE existing (id INTEGER)")
        before = connection.execute("SELECT sql FROM sqlite_schema").fetchall()

        with pytest.raises(ValueError, match="migration_required"):
            initialize_database(connection)

        assert connection.execute("PRAGMA user_version").fetchone() == (version,)
        assert connection.execute("SELECT sql FROM sqlite_schema").fetchall() == before
        assert not connection.in_transaction


def test_initialize_preserves_callers_active_transaction(tmp_path):
    from trial_explorer.store import initialize_database

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        connection.execute("CREATE TABLE existing (id INTEGER)")
        connection.execute("INSERT INTO existing VALUES (1)")

        with pytest.raises(ValueError, match="idle connection"):
            initialize_database(connection)

        assert connection.in_transaction
        connection.rollback()
        assert connection.execute("SELECT * FROM existing").fetchall() == []


@pytest.fixture
def snapshot_manifest():
    return {
        "snapshot_id": "test_snapshot",
        "manifest_sha256": "a" * 64,
        "completed_at": "2026-11-18T12:00:00+00:00",
        "fetch_status": "complete",
        "target_met": False,
        "note": "Fictional: guardian's consent \u2265 18",
    }


def test_insert_snapshot_preserves_manifest_and_allows_rollback(tmp_path, snapshot_manifest):
    import json
    from trial_explorer.store import initialize_database, insert_snapshot

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        initialize_database(connection)
        connection.execute("BEGIN")
        insert_snapshot(connection, snapshot_manifest)

        row = connection.execute(
            "SELECT snapshot_id, manifest_hash, retrieved_at, fetch_status, target_met, "
            "manifest_json FROM snapshots"
        ).fetchone()
        assert row[:5] == (
            snapshot_manifest["snapshot_id"],
            snapshot_manifest["manifest_sha256"],
            snapshot_manifest["completed_at"],
            "complete",
            0,
        )
        assert json.loads(row[5]) == snapshot_manifest
        assert connection.in_transaction
        connection.rollback()
        assert connection.execute("SELECT COUNT(*) FROM snapshots").fetchone() == (0,)


@pytest.mark.parametrize("case", ["idle", "partial"])
def test_insert_snapshot_rejects_invalid_call(tmp_path, snapshot_manifest, case):
    from trial_explorer.store import initialize_database, insert_snapshot

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        initialize_database(connection)
        if case == "partial":
            connection.execute("BEGIN")
            snapshot_manifest["fetch_status"] = "partial"
        message = "active transaction" if case == "idle" else "Only complete snapshots"

        with pytest.raises(ValueError, match=message):
            insert_snapshot(connection, snapshot_manifest)

        assert connection.execute("SELECT COUNT(*) FROM snapshots").fetchone() == (0,)
        connection.rollback()


@pytest.fixture
def normalized_study():
    from datetime import UTC, datetime
    from trial_explorer.normalize import normalize_study

    return normalize_study(
        {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000001"},
                "eligibilityModule": {
                    "eligibilityCriteria": "  Age \u2265 18.\r\n- Guardian's consent required.\n"
                },
            }
        },
        retrieved_at=datetime(2026, 11, 18, tzinfo=UTC),
        snapshot_id="test_snapshot",
    )


def test_insert_study_round_trip(tmp_path, snapshot_manifest, normalized_study):
    from datetime import datetime
    from trial_explorer.store import initialize_database, insert_snapshot, insert_study

    path = tmp_path / "trials.sqlite"
    with closing(connect_database(path)) as connection:
        initialize_database(connection)
        connection.execute("BEGIN")
        insert_snapshot(connection, snapshot_manifest)
        insert_study(connection, normalized_study)
        assert connection.in_transaction
        connection.commit()

    with closing(connect_database(path)) as connection:
        row = connection.execute(
            "SELECT snapshot_id, nct_id, title, criteria_text, criteria_state, "
            "source_url, source_updated_at, retrieved_at, recruitment_status "
            "FROM studies WHERE snapshot_id = ? AND nct_id = ?",
            (normalized_study.snapshot_id, normalized_study.nct_id),
        ).fetchone()
        assert row[:7] == (
            normalized_study.snapshot_id, normalized_study.nct_id, None,
            normalized_study.criteria_text, "present", normalized_study.source_url, None,
        )
        assert datetime.fromisoformat(row[7]) == normalized_study.retrieved_at
        assert row[8] is None


@pytest.mark.parametrize("case", ["idle", "missing_snapshot", "duplicate"])
def test_insert_study_rejects_invalid_call(
    tmp_path, snapshot_manifest, normalized_study, case
):
    from trial_explorer.store import initialize_database, insert_snapshot, insert_study

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        initialize_database(connection)
        if case != "idle":
            connection.execute("BEGIN")
        if case == "duplicate":
            insert_snapshot(connection, snapshot_manifest)
            insert_study(connection, normalized_study)

        expected_error = ValueError if case == "idle" else sqlite3.IntegrityError
        with pytest.raises(expected_error):
            insert_study(connection, normalized_study)

        expected_count = 1 if case == "duplicate" else 0
        assert connection.execute("SELECT COUNT(*) FROM studies").fetchone() == (expected_count,)
        connection.rollback()
        assert connection.execute("SELECT COUNT(*) FROM studies").fetchone() == (0,)


@pytest.fixture
def stored_study_connection(tmp_path, snapshot_manifest, normalized_study):
    from trial_explorer.store import initialize_database, insert_snapshot, insert_study

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        initialize_database(connection)
        connection.execute("BEGIN")
        insert_snapshot(connection, snapshot_manifest)
        insert_study(connection, normalized_study)
        yield connection
        connection.rollback()


def test_insert_passage_round_trip(stored_study_connection, normalized_study):
    from dataclasses import asdict
    from trial_explorer.passages import build_passages
    from trial_explorer.store import insert_passage

    connection = stored_study_connection
    passage = build_passages(normalized_study)[0]
    insert_passage(connection, passage)

    cursor = connection.execute(
        "SELECT * FROM passages WHERE passage_id = ?", (passage.passage_id,)
    )
    row = cursor.fetchone()
    assert dict(zip((column[0] for column in cursor.description), row)) == asdict(passage)
    assert connection.in_transaction
    connection.rollback()
    assert connection.execute("SELECT COUNT(*) FROM passages").fetchone() == (0,)
    assert connection.execute("SELECT COUNT(*) FROM studies").fetchone() == (0,)
    assert connection.execute("SELECT COUNT(*) FROM snapshots").fetchone() == (0,)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"text": "Altered quote"}, "Passage text does not match"),
        ({"parent_text": "Altered context"}, "Parent text does not match"),
        ({"source_start": -1}, "outside their source"),
        ({"source_end": 10000}, "outside their source"),
        ({"parent_source_end": 10000}, "outside their source"),
        ({"parent_source_start": 1}, "outside their source"),
        ({"snapshot_id": "another_snapshot"}, "requires a stored study"),
    ],
)
def test_insert_passage_rejects_invalid_source(
    stored_study_connection, normalized_study, changes, message
):
    from dataclasses import replace
    from trial_explorer.passages import build_passages
    from trial_explorer.store import insert_passage

    passage = replace(build_passages(normalized_study)[0], **changes)
    with pytest.raises(ValueError, match=message):
        insert_passage(stored_study_connection, passage)
    assert stored_study_connection.execute("SELECT COUNT(*) FROM passages").fetchone() == (0,)


def test_insert_passage_rejects_duplicate_span(stored_study_connection, normalized_study):
    from dataclasses import replace
    from trial_explorer.passages import build_passages
    from trial_explorer.store import insert_passage

    passage = build_passages(normalized_study)[0]
    insert_passage(stored_study_connection, passage)
    with pytest.raises(sqlite3.IntegrityError):
        insert_passage(
            stored_study_connection, replace(passage, passage_id="another_id")
        )


def test_insert_passage_requires_active_transaction(tmp_path, normalized_study):
    from trial_explorer.passages import build_passages
    from trial_explorer.store import initialize_database, insert_passage

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        initialize_database(connection)
        with pytest.raises(ValueError, match="active transaction"):
            insert_passage(connection, build_passages(normalized_study)[0])


@pytest.fixture
def importable_snapshot(tmp_path, monkeypatch):
    import json
    from trial_explorer import ingest, snapshots

    records = [
        {"protocolSection": {
            "identificationModule": {"nctId": nct_id},
            "eligibilityModule": {
                "eligibilityCriteria": "Inclusion Criteria:\n- Age \u2265 18.\n\n- Guardian's consent.\n"
            },
        }}
        for nct_id in ("NCT00000001", "NCT00000002")
    ]
    monkeypatch.setattr(
        ingest, "fetch_studies_page",
        lambda token: json.dumps({"studies": records}).encode(),
    )
    path, _ = snapshots.collect_snapshot(tmp_path / "raw")
    return path.parent


def test_import_snapshot_commits_all_rows(tmp_path, importable_snapshot):
    from trial_explorer import store
    from trial_explorer.passages import build_passages
    from trial_explorer.snapshots import load_selected_studies

    path = tmp_path / "trials.sqlite"
    with closing(connect_database(path)) as connection:
        assert store.import_snapshot(connection, importable_snapshot) == (2, 4)
        assert not connection.in_transaction

    with closing(connect_database(path)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM snapshots").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM studies").fetchone() == (2,)
        assert connection.execute("SELECT COUNT(*) FROM passages").fetchone() == (4,)
        for study in load_selected_studies(importable_snapshot):
            assert connection.execute(
                "SELECT criteria_text FROM studies WHERE snapshot_id = ? AND nct_id = ?",
                (study.snapshot_id, study.nct_id),
            ).fetchone() == (study.criteria_text,)
            for passage in build_passages(study):
                assert connection.execute(
                    "SELECT text, parent_text FROM passages WHERE passage_id = ?",
                    (passage.passage_id,),
                ).fetchone() == (passage.text, passage.parent_text)


def test_import_snapshot_rolls_back_after_partial_inserts(
    tmp_path, importable_snapshot, monkeypatch
):
    from trial_explorer import store

    real_insert = store.insert_passage
    calls = []

    def failing_insert(connection, passage):
        calls.append(passage.passage_id)
        if len(calls) == 3:
            assert connection.execute("SELECT COUNT(*) FROM studies").fetchone() == (2,)
            assert connection.execute("SELECT COUNT(*) FROM passages").fetchone() == (2,)
            raise ValueError("simulated passage failure")
        real_insert(connection, passage)

    monkeypatch.setattr(store, "insert_passage", failing_insert)
    path = tmp_path / "trials.sqlite"
    with closing(connect_database(path)) as connection:
        with pytest.raises(ValueError, match="simulated passage failure"):
            store.import_snapshot(connection, importable_snapshot)
        assert not connection.in_transaction

    with closing(connect_database(path)) as connection:
        for table in ("snapshots", "studies", "passages"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (0,)
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)


def test_reimport_is_a_verified_no_op(tmp_path, importable_snapshot, monkeypatch):
    from trial_explorer import store

    def unexpected_insert(*args):
        pytest.fail("A verified repeat import must not insert rows")

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        assert store.import_snapshot(connection, importable_snapshot) == (2, 4)
        before = connection.total_changes
        monkeypatch.setattr(store, "insert_snapshot", unexpected_insert)
        monkeypatch.setattr(store, "insert_study", unexpected_insert)
        monkeypatch.setattr(store, "insert_passage", unexpected_insert)

        assert store.import_snapshot(connection, importable_snapshot) == (2, 4)

        assert connection.total_changes == before
        assert not connection.in_transaction


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("UPDATE snapshots SET manifest_hash = 'changed'", "Stored snapshot conflicts"),
        ("UPDATE studies SET title = 'changed'", "Stored studies conflict"),
        ("UPDATE passages SET text = 'changed'", "Stored passages conflict"),
        ("DELETE FROM passages WHERE passage_id = (SELECT MIN(passage_id) FROM passages)",
         "Stored passages conflict"),
    ],
)
def test_reimport_rejects_conflicting_rows(
    tmp_path, importable_snapshot, mutation, message
):
    from trial_explorer.store import import_snapshot

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        import_snapshot(connection, importable_snapshot)
        connection.execute(mutation)
        connection.commit()
        before = connection.total_changes

        with pytest.raises(ValueError, match=message):
            import_snapshot(connection, importable_snapshot)

        assert connection.total_changes == before
        assert not connection.in_transaction


def test_import_snapshot_cli(tmp_path, importable_snapshot, capsys):
    import json
    from trial_explorer.cli import main

    database = tmp_path / "trials.sqlite"
    arguments = [
        "import-snapshot", "--snapshot", str(importable_snapshot),
        "--db", str(database),
    ]
    for _ in range(2):
        assert main(arguments) == 0
        output = capsys.readouterr()
        assert json.loads(output.out) == {
            "database_path": str(database), "study_count": 2, "passage_count": 4
        }
        assert output.err == ""


def test_import_snapshot_cli_reports_missing_file(tmp_path, capsys):
    import json
    from trial_explorer.cli import main

    assert main([
        "import-snapshot", "--snapshot", str(tmp_path / "missing"),
        "--db", str(tmp_path / "trials.sqlite"),
    ]) == 3
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["error"] == "import_failed"


def test_read_functions_isolate_snapshots_and_preserve_source(
    tmp_path, importable_snapshot, monkeypatch
):
    import json
    from trial_explorer import ingest, snapshots, store
    from trial_explorer.passages import build_passages

    original_studies = snapshots.load_selected_studies(importable_snapshot)
    changed_text = "Exclusion Criteria:\n- Fictional exception: do not enroll.\n"
    body = json.dumps({"studies": [{"protocolSection": {
        "identificationModule": {"nctId": "NCT00000001"},
        "eligibilityModule": {"eligibilityCriteria": changed_text},
    }}]}).encode()
    monkeypatch.setattr(ingest, "fetch_studies_page", lambda token: body)
    second_path, _ = snapshots.collect_snapshot(tmp_path / "raw")
    changed_study = snapshots.load_selected_studies(second_path.parent)[0]

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        store.import_snapshot(connection, importable_snapshot)
        store.import_snapshot(connection, second_path.parent)
        for expected in [*original_studies, changed_study]:
            assert store.get_study(connection, expected.snapshot_id, expected.nct_id) == expected
            assert store.get_passages(connection, expected.snapshot_id, expected.nct_id) == build_passages(expected)
        original = original_studies[0]
        assert store.get_study(connection, original.snapshot_id, original.nct_id).criteria_text != changed_text
        assert store.get_study(connection, "missing", original.nct_id) is None
        assert store.get_passages(connection, "missing", original.nct_id) == []
        assert store.get_study(connection, original.snapshot_id, "NCT99999999") is None
        assert store.get_passages(connection, original.snapshot_id, "NCT99999999") == []
        assert store.get_study(connection, "' OR 1=1 --", original.nct_id) is None
        assert connection.execute("SELECT COUNT(*) FROM snapshots").fetchone() == (2,)
        # Cursor-specific mapping must preserve the connection's tuple API.
        assert connection.row_factory is None


def test_failed_new_import_preserves_existing_snapshot(
    tmp_path, importable_snapshot, monkeypatch
):
    import json
    from trial_explorer import ingest, snapshots, store

    with closing(connect_database(tmp_path / "trials.sqlite")) as connection:
        store.import_snapshot(connection, importable_snapshot)
        original = snapshots.load_selected_studies(importable_snapshot)
        before = connection.iterdump()
        before = list(before)
        monkeypatch.setattr(ingest, "fetch_studies_page", lambda token: json.dumps({
            "studies": [{"protocolSection": {
                "identificationModule": {"nctId": "NCT00000003"},
                "eligibilityModule": {"eligibilityCriteria": "New criteria"},
            }}]
        }).encode())
        path, _ = snapshots.collect_snapshot(tmp_path / "raw")

        def fail(connection, passage):
            raise ValueError("simulated failure")

        monkeypatch.setattr(store, "insert_passage", fail)
        with pytest.raises(ValueError, match="simulated failure"):
            store.import_snapshot(connection, path.parent)
        assert list(connection.iterdump()) == before
        assert store.get_study(connection, original[0].snapshot_id, original[0].nct_id) == original[0]


@pytest.mark.parametrize("command", ["read-study", "read-passages"])
def test_read_cli_returns_snapshot_evidence(tmp_path, importable_snapshot, capsys, command):
    import json
    from trial_explorer import cli, store, snapshots

    database = tmp_path / "trials.sqlite"
    with closing(connect_database(database)) as connection:
        store.import_snapshot(connection, importable_snapshot)
    expected = snapshots.load_selected_studies(importable_snapshot)[0]
    arguments = [
        command, "--db", str(database), "--snapshot-id", expected.snapshot_id,
        "--nct-id", expected.nct_id,
    ]
    if command == "read-passages":
        arguments.extend(["--limit", "1"])
    before = database.read_bytes()

    assert cli.main(arguments) == 0
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert output.err == ""
    assert result["snapshot_id"] == expected.snapshot_id
    assert result["nct_id"] == expected.nct_id
    if command == "read-study":
        assert result["criteria_text"] == expected.criteria_text
        assert result["retrieved_at"] == expected.retrieved_at.isoformat()
    else:
        assert result["total"] == 2
        assert result["returned_count"] == len(result["items"]) == 1
        passage = result["items"][0]
        assert expected.criteria_text[passage["source_start"]:passage["source_end"]] == passage["text"]
    assert database.read_bytes() == before


def test_read_cli_missing_database_does_not_create_file(tmp_path, capsys):
    import json
    from trial_explorer.cli import main

    path = tmp_path / "missing.sqlite"
    assert main([
        "read-study", "--db", str(path),
        "--snapshot-id", "missing", "--nct-id", "NCT00000001",
    ]) == 3
    assert json.loads(capsys.readouterr().err)["error"] == "read_failed"
    assert not path.exists()


def test_read_cli_reports_absent_study(tmp_path, capsys):
    import json
    from trial_explorer import cli, store

    path = tmp_path / "trials.sqlite"
    with closing(connect_database(path)) as connection:
        store.initialize_database(connection)
    assert cli.main([
        "read-study", "--db", str(path),
        "--snapshot-id", "missing", "--nct-id", "NCT00000001",
    ]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["error"] == "study_not_found"
