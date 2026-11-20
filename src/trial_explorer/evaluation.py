import json
import sqlite3
from pathlib import Path
from hashlib import sha256

from trial_explorer.normalize import SOURCE_STATUSES
from trial_explorer.retrieval import TOKEN_PATTERN, tokenize, validate_filter_values
from trial_explorer.search import keyword_search
from trial_explorer.snapshots import canonical_json
from trial_explorer.store import get_snapshot_passages, validate_passage_source

def passage_recall_at_five(
    retrieved_ids: list[str], relevant_ids: set[str]
) -> float:
    """Measure how much labeled evidence appears in the first five results."""
    if not relevant_ids:
        raise ValueError("A positive retrieval check needs relevant evidence")

    returned = set(retrieved_ids[:5])
    found = returned & relevant_ids

    return len(found) / len(relevant_ids)

def load_evaluation_cases(path: Path) -> list[dict]:
    """Read evaluation cases and check their basic identity fields."""
    cases = []
    seen_ids: set[str] = set()

    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue

            try:
                case = json.loads(line)
            except ValueError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}"
                ) from error
            if not isinstance(case, dict):
                raise ValueError(f"Expected an object on line {line_number}")

            case_id = case.get("case_id")
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError(f"Missing case ID on line {line_number}")
            if case_id in seen_ids:
                raise ValueError(f"Duplicate case ID: {case_id}")

            query = case.get("query")
            if (
                not isinstance(query, str)
                or not query.strip()
                or len(query) > 2000
            ):
                raise ValueError(f"Invalid query in case {case_id}")

            seen_ids.add(case_id)
            cases.append(case)

    if not cases:
        raise ValueError("Evaluation file contains no cases")

    return cases

def _require_fields(value: object, fields: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"Invalid fields in {label}")


def _require_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-blank text")


def validate_evaluation_case(connection: sqlite3.Connection, case: dict) -> None:
    """Validate a case's schema, study scope, and exact stored evidence."""
    _require_fields(case, {
        "schema_version", "case_id", "data_kind", "snapshot_id", "query", "mode",
        "selected_nct_ids", "filters", "retrieval_checks", "expected_outcome",
        "required_fidelity_points", "source_verified_notes",
    }, "case")
    if type(case["schema_version"]) is not int or case["schema_version"] != 1:
        raise ValueError("Unsupported evaluation schema version")
    _require_text(case["case_id"], "Case ID")
    if case["data_kind"] not in ("real", "synthetic"):
        raise ValueError("Invalid data_kind")
    _require_text(case["snapshot_id"], "Snapshot ID")
    _require_text(case["query"], "Query")
    if len(case["query"]) > 2000 or not tokenize(case["query"]):
        raise ValueError("Invalid searchable query")
    _require_text(case["source_verified_notes"], "Source verification notes")
    points = case["required_fidelity_points"]
    if not isinstance(points, list):
        raise ValueError("Fidelity points must be a list")
    for point in points:
        _require_text(point, "Fidelity point")

    snapshot = connection.execute(
        "SELECT fetch_status FROM snapshots WHERE snapshot_id = ?",
        (case["snapshot_id"],),
    ).fetchone()
    if snapshot is None or snapshot[0] != "complete":
        raise ValueError("Evaluation requires a complete stored snapshot")
    studies = connection.execute(
        "SELECT nct_id, recruitment_status FROM studies WHERE snapshot_id = ?",
        (case["snapshot_id"],),
    ).fetchall()
    known_ids = {row[0] for row in studies}
    mode = case["mode"]
    if mode not in ("search", "study_question", "comparison"):
        raise ValueError("Invalid evaluation mode")
    selected = case["selected_nct_ids"]
    required_count = {"search": 0, "study_question": 1, "comparison": 2}[mode]
    if not isinstance(selected, list) or len(selected) != required_count:
        raise ValueError("Selected study count does not match mode")
    if selected:
        validate_filter_values(selected, known_ids, "selected_nct_ids")

    filters = case["filters"]
    if not isinstance(filters, dict) or set(filters) - {"nct_ids", "recruitment_statuses"}:
        raise ValueError("Invalid filter fields")
    filter_ids = validate_filter_values(filters.get("nct_ids"), known_ids, "nct_ids")
    statuses = validate_filter_values(
        filters.get("recruitment_statuses"), SOURCE_STATUSES, "recruitment_statuses"
    )
    permitted = {
        nct_id for nct_id, status in studies
        if (filter_ids is None or nct_id in filter_ids)
        and (statuses is None or status in statuses)
    }
    if not set(selected).issubset(permitted):
        raise ValueError("Selected studies are outside the permitted scope")
    expected = case["expected_outcome"]
    outcomes = {
        "answered", "not-stated-in-record", "insufficient-reviewed-evidence",
        "generation-unavailable", "review-needed",
    }
    if (mode == "search" and expected != "results") or (
        mode != "search" and (not isinstance(expected, str) or expected not in outcomes)
    ):
        raise ValueError("Invalid expected outcome")

    checks = case["retrieval_checks"]
    check_count = 2 if mode == "comparison" else 1
    if not isinstance(checks, list) or len(checks) != check_count:
        raise ValueError("Retrieval check count does not match mode")
    passages = {p.passage_id: p for p in get_snapshot_passages(connection, case["snapshot_id"])}
    scoped_studies = []
    for check in checks:
        _require_fields(check, {
            "scope_nct_ids", "applicability", "relevant_evidence", "source_review_notes",
        }, "retrieval check")
        _require_text(check["source_review_notes"], "Source review notes")
        scope = validate_filter_values(check["scope_nct_ids"], known_ids, "scope_nct_ids")
        if scope is not None and not scope.issubset(permitted):
            raise ValueError("Retrieval check is outside the permitted scope")
        if mode != "search":
            if scope is None or len(scope) != 1 or not scope.issubset(set(selected)):
                raise ValueError("Each question check must scope one selected study")
            scoped_studies.extend(scope)
        applicability = check["applicability"]
        if applicability not in ("positive", "absent", "not_applicable"):
            raise ValueError("Invalid applicability")
        evidence = check["relevant_evidence"]
        if not isinstance(evidence, list):
            raise ValueError("Relevant evidence must be a list")
        if applicability == "positive" and not evidence:
            raise ValueError("Positive checks require relevant evidence")
        if applicability != "positive" and evidence:
            raise ValueError("Excluded checks must have empty evidence")
        if applicability == "absent" and scope is None:
            raise ValueError("Collection-wide absence labels are forbidden")
        seen = set()
        for item in evidence:
            _require_fields(item, {"passage_id", "exact_quote"}, "evidence")
            _require_text(item["passage_id"], "Passage ID")
            _require_text(item["exact_quote"], "Exact quote")
            passage_id = item["passage_id"]
            if passage_id in seen:
                raise ValueError("Duplicate relevant passage")
            seen.add(passage_id)
            passage = passages.get(passage_id)
            if passage is None:
                raise ValueError("Unknown passage in the case snapshot")
            if passage.nct_id not in (permitted if scope is None else scope):
                raise ValueError("Relevant passage is outside the check scope")
            if item["exact_quote"] not in passage.text:
                raise ValueError("Exact quote does not match the labeled passage")
            validate_passage_source(connection, passage)
    if mode != "search" and set(scoped_studies) != set(selected):
        raise ValueError("Question checks must cover each selected study")


def evaluate_retrieval(
    connection: sqlite3.Connection, cases: list[dict], snapshot_id: str
) -> dict:
    """Validate all labels, then measure keyword passage recall per check."""
    if not cases:
        raise ValueError("Evaluation requires at least one case")
    seen_ids = set()
    for case in cases:
        validate_evaluation_case(connection, case)
        if case["snapshot_id"] != snapshot_id:
            raise ValueError("Case snapshot does not match evaluation snapshot")
        if case["case_id"] in seen_ids:
            raise ValueError("Duplicate evaluation case ID")
        seen_ids.add(case["case_id"])

    results = []
    for case in cases:
        for index, check in enumerate(case["retrieval_checks"], 1):
            scope = check["scope_nct_ids"]
            filters = dict(case["filters"])
            if case["mode"] != "search" and scope is not None:
                filters["nct_ids"] = scope
            response = keyword_search(
                connection, snapshot_id, case["query"],
                nct_ids=filters.get("nct_ids"),
                recruitment_statuses=filters.get("recruitment_statuses"),
            )
            retrieved = [item["passage_id"] for item in response["results"]]
            relevant = {item["passage_id"] for item in check["relevant_evidence"]}
            found = relevant.intersection(retrieved[:5])
            positive = check["applicability"] == "positive"
            results.append({
                "case_id": case["case_id"], "data_kind": case["data_kind"],
                "query": case["query"], "mode": case["mode"], "check_index": index,
                "scope_nct_ids": scope, "applied_filters": response["applied_filters"],
                "applicability": check["applicability"],
                "source_review_notes": check["source_review_notes"],
                "source_verified_notes": case["source_verified_notes"],
                "retrieved_ids": retrieved, "relevant_ids": sorted(relevant),
                "found_ids": sorted(found), "missing_ids": sorted(relevant - found),
                "numerator": len(found) if positive else None,
                "denominator": len(relevant) if positive else None,
                "recall_at_5": passage_recall_at_five(retrieved, relevant) if positive else None,
                "excluded_reason": None if positive else check["applicability"],
            })

    summaries = {}
    for kind in ("real", "synthetic"):
        group = [row for row in results if row["data_kind"] == kind]
        positive_rows = [row for row in group if row["applicability"] == "positive"]
        summaries[kind] = {
            "case_count": len({row["case_id"] for row in group}),
            "check_count": len(group),
            "positive_check_count": len(positive_rows),
            "excluded_check_count": len(group) - len(positive_rows),
            "macro_recall_at_5": (
                sum(row["recall_at_5"] for row in positive_rows) / len(positive_rows)
                if positive_rows else None
            ),
        }

    manifest_hash = connection.execute(
        "SELECT manifest_hash FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
    ).fetchone()[0]
    configuration = {
        "method": "keyword", "tokenizer_version": "lexical-v1",
        "unicode_normalization": "NFKC", "casefold": True,
        "operator_mapping": {"\u2264": "<=", "\u2265": ">="},
        "token_pattern": TOKEN_PATTERN.pattern, "stopwords": [], "stemming": False,
        "k1": 1.2, "b": 0.75,
        "idf_formula": "ln(1+(N-df+0.5)/(df+0.5))",
        "statistics_scope": "full_snapshot",
        "tie_order": ["score_desc", "nct_id", "source_start", "passage_id"],
        "candidate_limit": 20, "rrf_k": 60, "final_limit": 5,
        "segmentation_version": "paragraph-v1",
        "embedding_revision": None,
    }
    return {
        "schema_version": 1, "snapshot_id": snapshot_id,
        "snapshot_manifest_sha256": manifest_hash,
        "cases_sha256": sha256(canonical_json(cases)).hexdigest(),
        "configuration": configuration,
        "configuration_sha256": sha256(canonical_json(configuration)).hexdigest(),
        "case_count": len(cases), "check_count": len(results),
        "summaries": summaries, "checks": results,
        "metric": "distinct relevant passages in first 5 / distinct labeled relevant passages",
        "aggregation": "mean of positive-check recalls, grouped by data_kind",
        "limitations": "Measures retrieval against supplied labels. Label completeness and relevance require source review.",
    }
