import sqlite3
from datetime import datetime
from pathlib import Path
from trial_explorer.models import Passage, Study
from trial_explorer.passages import build_passages
from trial_explorer.snapshots import (
    canonical_json,
    load_selected_studies,
    load_snapshot_manifest,
)
from dataclasses import asdict


SNAPSHOTS_TABLE_SQL = """
CREATE TABLE snapshots (
    snapshot_id TEXT PRIMARY KEY NOT NULL,
    manifest_hash TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    fetch_status TEXT NOT NULL,
    target_met INTEGER NOT NULL,
    manifest_json TEXT NOT NULL
)
"""
STUDIES_TABLE_SQL = """
CREATE TABLE studies (
    snapshot_id TEXT NOT NULL,
    nct_id TEXT NOT NULL,
    title TEXT,
    criteria_text TEXT,
    criteria_state TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_updated_at TEXT,
    retrieved_at TEXT NOT NULL,
    recruitment_status TEXT,
    PRIMARY KEY (snapshot_id, nct_id),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(snapshot_id)
)
"""

PASSAGES_TABLE_SQL = """
CREATE TABLE passages (
    passage_id TEXT PRIMARY KEY NOT NULL,
    snapshot_id TEXT NOT NULL,
    nct_id TEXT NOT NULL,
    segmentation_version TEXT NOT NULL,
    source_start INTEGER NOT NULL,
    source_end INTEGER NOT NULL,
    text TEXT NOT NULL,
    heading TEXT,
    parent_source_start INTEGER NOT NULL,
    parent_source_end INTEGER NOT NULL,
    parent_text TEXT NOT NULL,
    search_text TEXT NOT NULL,
    FOREIGN KEY (snapshot_id, nct_id)
        REFERENCES studies(snapshot_id, nct_id),
    CHECK (source_start >= 0 AND source_end > source_start),
    CHECK (
        parent_source_start >= 0
        AND parent_source_end > parent_source_start
    ),
    UNIQUE (
        snapshot_id, nct_id, segmentation_version,
        source_start, source_end
    )
)
"""

def connect_database(path: Path) -> sqlite3.Connection:
    """Open a database connection with foreign keys enabled."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def initialize_database(connection: sqlite3.Connection) -> None:
    """Create schema version 1 in an empty database."""
    if connection.in_transaction:
        raise ValueError("Schema initialization requires an idle connection")

    connection.execute("BEGIN IMMEDIATE")
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version == 1:
            connection.commit()
            return
        if version != 0:
            raise ValueError("migration_required")

        existing_table = connection.execute(
            "SELECT name FROM sqlite_schema "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
        ).fetchone()
        if existing_table is not None:
            raise ValueError("migration_required")

        connection.execute(SNAPSHOTS_TABLE_SQL)
        connection.execute(STUDIES_TABLE_SQL)
        connection.execute(PASSAGES_TABLE_SQL)
        connection.execute("PRAGMA user_version = 1")
        connection.commit()

    except Exception:
        connection.rollback()
        raise

def insert_snapshot(connection: sqlite3.Connection, manifest: dict) -> None:
    """Insert a verified snapshot within the caller's transaction."""
    if not connection.in_transaction:
        raise ValueError("Snapshot insertion requires an active transaction")
    if manifest["fetch_status"] != "complete":
        raise ValueError("Only complete snapshots can be imported")

    connection.execute(
        """
        INSERT INTO snapshots (
            snapshot_id, manifest_hash, retrieved_at,
            fetch_status, target_met, manifest_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            manifest["snapshot_id"],
            manifest["manifest_sha256"],
            manifest["completed_at"],
            manifest["fetch_status"],
            int(manifest["target_met"]),
            canonical_json(manifest).decode("utf-8"),
        ),
    )

def insert_study(connection: sqlite3.Connection, study: Study) -> None:
    """Insert a normalized study within the caller's transaction."""
    if not connection.in_transaction:
        raise ValueError("Study insertion requires an active transaction")

    connection.execute(
        """
        INSERT INTO studies (
            snapshot_id, nct_id, title, criteria_text, criteria_state,
            source_url, source_updated_at, retrieved_at, recruitment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            study.snapshot_id,
            study.nct_id,
            study.title,
            study.criteria_text,
            study.criteria_state,
            study.source_url,
            study.source_updated_at,
            study.retrieved_at.isoformat(),
            study.recruitment_status,
        ),
    )

def validate_passage_source(
    connection: sqlite3.Connection, passage: Passage
) -> None:
    """Check passage and parent spans against the stored study."""
    row = connection.execute(
        """
        SELECT criteria_text FROM studies
        WHERE snapshot_id = ? AND nct_id = ?
        """,
        (passage.snapshot_id, passage.nct_id),
    ).fetchone()

    if row is None or row[0] is None:
        raise ValueError("Passage requires a stored study with criteria")

    criteria = row[0]
    if not (
        0 <= passage.parent_source_start
        <= passage.source_start
        < passage.source_end
        <= passage.parent_source_end
        <= len(criteria)
    ):
        raise ValueError("Passage spans are outside their source")

    if criteria[passage.source_start:passage.source_end] != passage.text:
        raise ValueError("Passage text does not match its source")

    if (
        criteria[passage.parent_source_start:passage.parent_source_end]
        != passage.parent_text
    ):
        raise ValueError("Parent text does not match its source")

def insert_passage(connection: sqlite3.Connection, passage: Passage) -> None:
    """Validate and insert a passage within the caller's transaction."""
    if not connection.in_transaction:
        raise ValueError("Passage insertion requires an active transaction")

    validate_passage_source(connection, passage)

    connection.execute(
        """
        INSERT INTO passages (
            passage_id, snapshot_id, nct_id, segmentation_version,
            source_start, source_end, text, heading,
            parent_source_start, parent_source_end, parent_text,
            search_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            passage.passage_id,
            passage.snapshot_id,
            passage.nct_id,
            passage.segmentation_version,
            passage.source_start,
            passage.source_end,
            passage.text,
            passage.heading,
            passage.parent_source_start,
            passage.parent_source_end,
            passage.parent_text,
            passage.search_text,
        ),
    )

def verify_existing_records(
    connection: sqlite3.Connection, manifest: dict, studies: list[Study]
) -> None:
    """Require stored study and passage rows to match the source records."""
    expected_studies = []
    expected_passages = []

    for study in studies:
        row = asdict(study)
        row["retrieved_at"] = study.retrieved_at.isoformat()
        expected_studies.append(row)
        expected_passages.extend(
            asdict(passage) for passage in build_passages(study)
        )
    for table, expected in (
        ("studies", expected_studies),
        ("passages", expected_passages),
    ):
        cursor = connection.execute(
            f"SELECT * FROM {table} WHERE snapshot_id = ?",
            (manifest["snapshot_id"],),
        )
        columns = [column[0] for column in cursor.description]
        actual = [
            dict(zip(columns, values))
            for values in cursor.fetchall()
        ]

        if sorted(canonical_json(row) for row in actual) != sorted(
            canonical_json(row) for row in expected
        ):
            raise ValueError(f"Stored {table} conflict with the snapshot")

def import_snapshot(
    connection: sqlite3.Connection, directory: Path
) -> tuple[int, int]:
    """Import a new snapshot and return study and passage counts."""
    if connection.in_transaction:
        raise ValueError("Snapshot import requires an idle connection")

    manifest = load_snapshot_manifest(directory)
    studies = load_selected_studies(directory, manifest=manifest)
    initialize_database(connection)

    connection.execute("BEGIN IMMEDIATE")
    try:
        existing = connection.execute(
            """
            SELECT manifest_hash, retrieved_at, fetch_status,
                   target_met, manifest_json
            FROM snapshots WHERE snapshot_id = ?
            """,
            (manifest["snapshot_id"],),
        ).fetchone()

        if existing is not None:
            expected = (
                manifest["manifest_sha256"],
                manifest["completed_at"],
                manifest["fetch_status"],
                int(manifest["target_met"]),
                canonical_json(manifest).decode("utf-8"),
            )
            if existing != expected:
                raise ValueError("Stored snapshot conflicts with the manifest")

            verify_existing_records(connection, manifest, studies)
            passage_count = sum(
                len(build_passages(study)) for study in studies
            )
            connection.commit()
            return len(studies), passage_count

        insert_snapshot(connection, manifest)
        passage_count = 0

        for study in studies:
            insert_study(connection, study)

            for passage in build_passages(study):
                insert_passage(connection, passage)
                passage_count += 1

        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return len(studies), passage_count


def get_study(
    connection: sqlite3.Connection, snapshot_id: str, nct_id: str
) -> Study | None:
    """Return one study in the requested snapshot, or None if absent."""
    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row
    row = cursor.execute(
        """
        SELECT nct_id, title, criteria_text, criteria_state, source_url,
               source_updated_at, retrieved_at, snapshot_id, recruitment_status
        FROM studies WHERE snapshot_id = ? AND nct_id = ?
        """,
        (snapshot_id, nct_id),
    ).fetchone()
    if row is None:
        return None
    values = dict(row)
    values["retrieved_at"] = datetime.fromisoformat(values["retrieved_at"])
    return Study(**values)


def get_passages(
    connection: sqlite3.Connection, snapshot_id: str, nct_id: str
) -> list[Passage]:
    """Return a study's passages in original-text order within one snapshot."""
    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row
    rows = cursor.execute(
        """
        SELECT passage_id, snapshot_id, nct_id, segmentation_version,
               source_start, source_end, text, heading, parent_source_start,
               parent_source_end, parent_text, search_text
        FROM passages WHERE snapshot_id = ? AND nct_id = ?
        ORDER BY source_start, source_end, passage_id
        """,
        (snapshot_id, nct_id),
    ).fetchall()
    return [Passage(**dict(row)) for row in rows]
