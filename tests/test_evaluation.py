"""Synthetic checks of passage recall@5 arithmetic."""

import pytest

from trial_explorer.evaluation import load_evaluation_cases, passage_recall_at_five


@pytest.mark.parametrize(
    ("retrieved", "relevant", "expected"),
    [
        (["a", "b"], {"a", "b"}, 1.0),
        (["a", "b", "x"], {"a", "b", "c"}, 2 / 3),
        (["x", "y"], {"a"}, 0.0),
        ([], {"a"}, 0.0),
        (["a", "a", "a"], {"a", "b"}, 0.5),
        (["x1", "x2", "x3", "x4", "x5", "a"], {"a"}, 0.0),
        (["x1", "x2", "x3", "x4", "a", "b"], {"a", "b"}, 0.5),
    ],
)
def test_passage_recall_at_five(retrieved, relevant, expected):
    assert passage_recall_at_five(retrieved, relevant) == pytest.approx(expected)


def test_passage_recall_requires_positive_evidence():
    with pytest.raises(ValueError, match="needs relevant evidence"):
        passage_recall_at_five(["a"], set())


def test_load_evaluation_cases_reads_jsonl_and_preserves_fields(tmp_path):
    import json

    cases = [
        {"case_id": "first", "query": "Age \u2265 18?", "data_kind": "synthetic"},
        {"case_id": "second", "query": "Consent?", "data_kind": "synthetic"},
    ]
    path = tmp_path / "cases.jsonl"
    path.write_text(
        "\n" + "\n\n".join(json.dumps(case) for case in cases) + "\n",
        encoding="utf-8",
    )

    assert load_evaluation_cases(path) == cases


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{", "Invalid JSON on line 1"),
        ('{"case_id":"first","query":"age"}\n{', "Invalid JSON on line 2"),
        ("[]", "Expected an object"),
        ('{"query":"age"}', "Missing case ID"),
        ('{"case_id":" ","query":"age"}', "Missing case ID"),
        ('{"case_id":"first","query":"age"}\n{"case_id":"first","query":"consent"}',
         "Duplicate case ID"),
        ('{"case_id":"first"}', "Invalid query"),
        ('{"case_id":"first","query":null}', "Invalid query"),
        ('{"case_id":"first","query":" "}', "Invalid query"),
        ("", "contains no cases"),
        ("\n \t\n", "contains no cases"),
    ],
)
def test_load_evaluation_cases_rejects_invalid_input(tmp_path, content, message):
    path = tmp_path / "cases.jsonl"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_evaluation_cases(path)


def test_load_evaluation_cases_rejects_overlong_query(tmp_path):
    import json

    path = tmp_path / "cases.jsonl"
    path.write_text(
        json.dumps({"case_id": "first", "query": "a" * 2001}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Invalid query"):
        load_evaluation_cases(path)


@pytest.fixture
def labeled_database(tmp_path, monkeypatch):
    import json
    from contextlib import closing
    from trial_explorer import ingest, snapshots, store

    records = [
        {"protocolSection": {
            "identificationModule": {"nctId": nct_id},
            "eligibilityModule": {"eligibilityCriteria": text},
            "statusModule": {"overallStatus": "RECRUITING"},
        }}
        for nct_id, text in (
            ("NCT00000001", "Age at least 18.\n"),
            ("NCT00000002", "Consent is required.\n"),
        )
    ]
    monkeypatch.setattr(
        ingest, "fetch_studies_page", lambda token: json.dumps({"studies": records}).encode()
    )
    path, manifest = snapshots.collect_snapshot(tmp_path / "raw")
    with closing(store.connect_database(tmp_path / "trials.sqlite")) as connection:
        store.import_snapshot(connection, path.parent)
        passages = store.get_snapshot_passages(connection, manifest["snapshot_id"])
        case = {
            "schema_version": 1, "case_id": "synthetic_age",
            "data_kind": "synthetic", "snapshot_id": manifest["snapshot_id"],
            "query": "minimum age", "mode": "search", "selected_nct_ids": [],
            "filters": {"nct_ids": ["NCT00000001"]},
            "retrieval_checks": [{
                "scope_nct_ids": ["NCT00000001"], "applicability": "positive",
                "relevant_evidence": [{
                    "passage_id": passages[0].passage_id,
                    "exact_quote": "Age at least 18.",
                }],
                "source_review_notes": "Synthetic age threshold in the first study.",
            }],
            "expected_outcome": "results", "required_fidelity_points": ["Age at least 18."],
            "source_verified_notes": "Synthetic fixture with fixed source text.",
        }
        yield connection, case, passages


def test_validate_evaluation_case_accepts_verified_evidence(labeled_database):
    from copy import deepcopy
    from trial_explorer.evaluation import validate_evaluation_case

    connection, case, _ = labeled_database
    before = deepcopy(case)
    assert validate_evaluation_case(connection, case) is None
    assert case == before


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", True, "schema version"),
        ("snapshot_id", "missing", "complete stored snapshot"),
        ("data_kind", "guessed", "data_kind"),
        ("source_verified_notes", "", "verification notes"),
        ("query", "?!", "searchable query"),
        ("filters", {"unsupported": []}, "filter fields"),
        ("filters", {"nct_ids": ["NCT99999999"]}, "Unknown nct_ids"),
        ("filters", {"nct_ids": []}, "1 to 50"),
        ("filters", {"recruitment_statuses": ["INVALID"]}, "Unknown recruitment_statuses"),
        ("selected_nct_ids", ["NCT00000001"], "count does not match"),
        ("expected_outcome", "answered", "expected outcome"),
    ],
)
def test_validate_evaluation_case_rejects_bad_metadata(labeled_database, field, value, message):
    from trial_explorer.evaluation import validate_evaluation_case

    connection, case, _ = labeled_database
    case[field] = value
    with pytest.raises(ValueError, match=message):
        validate_evaluation_case(connection, case)


@pytest.mark.parametrize("defect", [
    "quote", "unknown_passage", "duplicate", "wrong_scope",
    "empty_positive", "absence_with_evidence", "collection_absence",
    "outside_filter", "stored_text",
])
def test_validate_evaluation_case_rejects_invalid_evidence(labeled_database, defect):
    from trial_explorer.evaluation import validate_evaluation_case

    connection, case, passages = labeled_database
    check = case["retrieval_checks"][0]
    evidence = check["relevant_evidence"][0]
    if defect == "quote":
        evidence["exact_quote"] = "Age at least 21."
    elif defect == "unknown_passage":
        evidence["passage_id"] = "p:other_snapshot:NCT00000001:0:1"
    elif defect == "duplicate":
        check["relevant_evidence"].append(dict(evidence))
    elif defect == "wrong_scope":
        case["filters"] = {}
        evidence["passage_id"] = passages[1].passage_id
        evidence["exact_quote"] = passages[1].text
    elif defect == "empty_positive":
        check["relevant_evidence"] = []
    elif defect == "absence_with_evidence":
        check["applicability"] = "absent"
    elif defect == "collection_absence":
        check.update(scope_nct_ids=None, applicability="absent", relevant_evidence=[])
    elif defect == "outside_filter":
        check["scope_nct_ids"] = ["NCT00000002"]
    else:
        connection.execute(
            "UPDATE studies SET criteria_text = ? WHERE snapshot_id = ? AND nct_id = ?",
            ("Changed source", case["snapshot_id"], "NCT00000001"),
        )
    with pytest.raises(ValueError):
        validate_evaluation_case(connection, case)


def test_validate_evaluation_case_accepts_scoped_absence(labeled_database):
    from trial_explorer.evaluation import validate_evaluation_case

    connection, case, _ = labeled_database
    case["retrieval_checks"][0].update(
        applicability="absent", relevant_evidence=[],
        source_review_notes="Synthetic full record contains no fictional marker.",
    )
    assert validate_evaluation_case(connection, case) is None


def test_validate_evaluation_case_checks_comparison_sides(labeled_database):
    from copy import deepcopy
    from trial_explorer.evaluation import validate_evaluation_case

    connection, case, passages = labeled_database
    case.update(
        mode="comparison", selected_nct_ids=["NCT00000001", "NCT00000002"],
        filters={}, expected_outcome="answered",
    )
    second = deepcopy(case["retrieval_checks"][0])
    second.update(
        scope_nct_ids=["NCT00000002"],
        relevant_evidence=[{"passage_id": passages[1].passage_id, "exact_quote": passages[1].text}],
    )
    case["retrieval_checks"].append(second)
    assert validate_evaluation_case(connection, case) is None

    case["retrieval_checks"][1] = deepcopy(case["retrieval_checks"][0])
    with pytest.raises(ValueError, match="cover each selected study"):
        validate_evaluation_case(connection, case)


def test_evaluate_retrieval_reports_hits_misses_and_separate_groups(labeled_database):
    from copy import deepcopy
    from trial_explorer.evaluation import evaluate_retrieval

    connection, case, _ = labeled_database
    missed = deepcopy(case)
    missed.update(case_id="real_miss", data_kind="real", query="consent")
    excluded = deepcopy(case)
    excluded["case_id"] = "synthetic_absence"
    excluded["retrieval_checks"][0].update(applicability="absent", relevant_evidence=[])

    report = evaluate_retrieval(connection, [case, missed, excluded], case["snapshot_id"])

    assert report["case_count"] == report["check_count"] == 3
    hit, miss, absent = report["checks"]
    assert (hit["numerator"], hit["denominator"], hit["recall_at_5"]) == (1, 1, 1)
    assert (miss["numerator"], miss["denominator"], miss["recall_at_5"]) == (0, 1, 0)
    assert miss["missing_ids"] == miss["relevant_ids"]
    assert absent["recall_at_5"] is None
    assert absent["excluded_reason"] == "absent"
    assert report["summaries"]["real"]["macro_recall_at_5"] == 0
    assert report["summaries"]["synthetic"]["macro_recall_at_5"] == 1
    assert report["summaries"]["synthetic"]["excluded_check_count"] == 1


def test_evaluate_retrieval_uses_search_filters_and_reports_partial_recall(labeled_database):
    from trial_explorer.evaluation import evaluate_retrieval

    connection, case, passages = labeled_database
    case["filters"] = {}
    case["retrieval_checks"][0].update(
        scope_nct_ids=None,
        relevant_evidence=[
            {"passage_id": p.passage_id, "exact_quote": p.text} for p in passages
        ],
    )
    report = evaluate_retrieval(connection, [case], case["snapshot_id"])

    assert report["checks"][0]["denominator"] == 2
    assert report["checks"][0]["recall_at_5"] == 0.5


def test_evaluate_retrieval_validates_all_labels_before_search(labeled_database, monkeypatch):
    from copy import deepcopy
    from trial_explorer import evaluation

    connection, case, _ = labeled_database
    invalid = deepcopy(case)
    invalid["case_id"] = "invalid_second"
    invalid["retrieval_checks"][0]["relevant_evidence"][0]["exact_quote"] = "incorrect quote"

    def forbidden_search(*args, **kwargs):
        pytest.fail("Search ran before all cases were validated")

    monkeypatch.setattr(evaluation, "keyword_search", forbidden_search)
    with pytest.raises(ValueError, match="Exact quote"):
        evaluation.evaluate_retrieval(connection, [case, invalid], case["snapshot_id"])


def test_evaluate_retrieval_rejects_snapshot_mismatch(labeled_database):
    from trial_explorer.evaluation import evaluate_retrieval

    connection, case, _ = labeled_database
    with pytest.raises(ValueError, match="does not match"):
        evaluate_retrieval(connection, [case], "another_snapshot")


def test_evaluation_with_no_positive_checks_has_no_recall_score(labeled_database):
    from trial_explorer.evaluation import evaluate_retrieval

    connection, case, _ = labeled_database
    case["retrieval_checks"][0].update(applicability="not_applicable", relevant_evidence=[])
    report = evaluate_retrieval(connection, [case], case["snapshot_id"])

    assert report["summaries"]["synthetic"]["positive_check_count"] == 0
    assert report["summaries"]["synthetic"]["macro_recall_at_5"] is None


def test_evaluate_cli_writes_report_and_refuses_overwrite(labeled_database, tmp_path, capsys):
    import json
    from trial_explorer.cli import main

    connection, case, _ = labeled_database
    database = connection.execute("PRAGMA database_list").fetchone()[2]
    cases = tmp_path / "cases.jsonl"
    cases.write_text(json.dumps(case) + "\n", encoding="utf-8")
    output = tmp_path / "report.json"
    arguments = [
        "evaluate-retrieval", "--db", database, "--snapshot-id", case["snapshot_id"],
        "--cases", str(cases), "--output", str(output), "--mode", "keyword",
    ]

    assert main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["case_count"] == 1
    saved = output.read_bytes()
    report = json.loads(saved)
    assert report["summaries"]["synthetic"]["macro_recall_at_5"] == 1
    assert len(report["configuration_sha256"]) == 64
    assert main(arguments) == 3
    assert json.loads(capsys.readouterr().err)["error"] == "evaluation_failed"
    assert output.read_bytes() == saved


def test_evaluate_cli_rejects_labels_without_creating_report(labeled_database, tmp_path, capsys):
    import json
    from trial_explorer.cli import main

    connection, case, _ = labeled_database
    database = connection.execute("PRAGMA database_list").fetchone()[2]
    case["retrieval_checks"][0]["relevant_evidence"][0]["exact_quote"] = "incorrect"
    cases = tmp_path / "cases.jsonl"
    cases.write_text(json.dumps(case) + "\n", encoding="utf-8")
    output = tmp_path / "report.json"

    assert main([
        "evaluate-retrieval", "--db", database, "--snapshot-id", case["snapshot_id"],
        "--cases", str(cases), "--output", str(output),
    ]) == 5
    assert json.loads(capsys.readouterr().err)["error"] == "invalid_evaluation_labels"
    assert not output.exists()


def test_evaluation_runs_comparison_checks_independently(labeled_database):
    from copy import deepcopy
    from trial_explorer.evaluation import evaluate_retrieval

    connection, case, passages = labeled_database
    case.update(
        mode="comparison", selected_nct_ids=["NCT00000001", "NCT00000002"],
        filters={}, expected_outcome="answered",
    )
    second = deepcopy(case["retrieval_checks"][0])
    second.update(
        scope_nct_ids=["NCT00000002"],
        relevant_evidence=[{"passage_id": passages[1].passage_id, "exact_quote": passages[1].text}],
    )
    case["retrieval_checks"].append(second)

    report = evaluate_retrieval(connection, [case], case["snapshot_id"])

    assert report["check_count"] == 2
    assert [check["recall_at_5"] for check in report["checks"]] == [1, 0]
    assert report["summaries"]["synthetic"]["macro_recall_at_5"] == 0.5
    assert report["checks"][0]["applied_filters"]["nct_ids"] == ["NCT00000001"]
    assert report["checks"][1]["applied_filters"]["nct_ids"] == ["NCT00000002"]


@pytest.mark.parametrize("mode", ["vector", "hybrid"])
def test_evaluate_cli_propagates_mode_and_records_repeated_timings(
    labeled_database, tmp_path, capsys, monkeypatch, mode,
):
    import json
    from trial_explorer import cli, evaluation

    connection, case, _ = labeled_database
    database = connection.execute("PRAGMA database_list").fetchone()[2]
    cases = tmp_path / "cases.jsonl"
    cases.write_text(json.dumps(case) + "\n", encoding="utf-8")
    index = tmp_path / "index"
    index.mkdir()
    (index / "manifest.json").write_text("{}", encoding="utf-8")
    model = tmp_path / "revision"
    report_path = tmp_path / "report.json"
    label = case["retrieval_checks"][0]["relevant_evidence"][0]["passage_id"]

    def search(connection, snapshot_id, query, **options):
        assert (options["mode"], options["index_dir"], options["model_dir"]) == (
            mode, index, model,
        )
        return {"results": [{"passage_id": label}], "applied_filters": {}}

    times = iter([1, 2, 3, 5, 6, 9])
    monkeypatch.setattr(evaluation, "keyword_search", search)
    monkeypatch.setattr(evaluation, "perf_counter", lambda: next(times))
    assert cli.main([
        "evaluate-retrieval", "--db", database, "--snapshot-id", case["snapshot_id"],
        "--cases", str(cases), "--output", str(report_path), "--mode", mode,
        "--index-dir", str(index), "--model-dir", str(model), "--repeats", "3",
    ]) == 0
    report = json.loads(report_path.read_bytes())
    assert json.loads(capsys.readouterr().out)["summaries"] == report["summaries"]
    assert report["configuration"]["method"] == mode
    assert report["configuration"]["embedding_revision"] == "revision"
    assert report["checks"][0]["recall_at_5"] == 1
    assert report["checks"][0]["missing_ids"] == []
    assert report["summaries"]["synthetic"]["timed_positive_calls"] == 3
    assert report["summaries"]["synthetic"]["median_search_latency_ms"] == 2000
