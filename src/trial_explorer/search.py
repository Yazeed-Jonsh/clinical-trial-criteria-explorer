"""Snapshot-scoped keyword retrieval shared by CLI and evaluation."""

import sqlite3
from dataclasses import asdict

from trial_explorer.normalize import SOURCE_STATUSES
from trial_explorer.retrieval import rank_passages, validate_filter_values
from trial_explorer.store import get_passages, get_study, get_snapshot_passages

def keyword_search(
    connection: sqlite3.Connection, snapshot_id: str, query: str,
    *, nct_ids: list[str] | None = None,
    recruitment_statuses: list[str] | None = None,
) -> dict:
    """Search one stored snapshot and return ranked evidence."""
    passages = get_snapshot_passages(connection, snapshot_id)
    if not isinstance(query, str) or not 1 <= len(query) <= 2000 or not query.strip():
        raise ValueError("Query must contain 1 to 2000 characters and non-blank text")
    study_rows = connection.execute(
        "SELECT nct_id, recruitment_status FROM studies WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchall()
    requested_ids = validate_filter_values(nct_ids, {row[0] for row in study_rows}, "nct_ids")
    requested_statuses = validate_filter_values(
        recruitment_statuses, SOURCE_STATUSES, "recruitment_statuses"
    )
    permitted_ids = {
        nct_id for nct_id, status in study_rows
        if (requested_ids is None or nct_id in requested_ids)
        and (requested_statuses is None or status in requested_statuses)
    }
    matches = rank_passages(query, passages, permitted_nct_ids=permitted_ids)
    applied_filters = {}
    if nct_ids is not None:
        applied_filters["nct_ids"] = nct_ids
    if recruitment_statuses is not None:
        applied_filters["recruitment_statuses"] = recruitment_statuses
    results = []

    for rank, (passage, score) in enumerate(matches, start=1):
        study = get_study(connection, snapshot_id, passage.nct_id)
        if study is None:
            raise ValueError("Passage references a missing study")

        results.append({
            **asdict(passage),
            "rank": rank,
            "score": score,
            "method": "keyword",
            "source_url": study.source_url,
            "source_updated_at": study.source_updated_at,
        })

    snapshot_date = connection.execute(
        "SELECT retrieved_at FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()[0]
    return {
        "snapshot_id": snapshot_id,
        "snapshot_date": snapshot_date,
        "applied_filters": applied_filters,
        "permitted_study_count": len(permitted_ids),
        "permitted_passage_count": sum(p.nct_id in permitted_ids for p in passages),
        "limit": 5,
        "returned_count": len(results),
        "result_unit": "passage",
        "exhaustive": False,
        "scope": "These passages match the query in the stored sample; this result is not exhaustive.",
        "results": results,
    }
