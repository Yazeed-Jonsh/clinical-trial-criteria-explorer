"""Synthetic checks for the lexical-v1 search tokenizer."""

import pytest

from trial_explorer.retrieval import bm25_score, count_terms, document_frequencies, inverse_document_frequency, rank_passages, tokenize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Age \u2265 18", ["age", ">=", "18"]),
        ("HbA1c \u2264 7.5%", ["hba1c", "<=", "7.5", "%"]),
        ("Dose 5 mg/dL", ["dose", "5", "mg", "/", "dl"]),
        ("\uff21\uff47\uff45 \uff11\uff18", ["age", "18"]),
        ("Age age AGE", ["age", "age", "age"]),
        ("No insulin", ["no", "insulin"]),
        ("", []),
        ("?!", []),
    ],
)
def test_tokenize_uses_lexical_rules(text, expected):
    assert tokenize(text) == expected


def test_tokenize_preserves_original_text():
    text = "  HbA1c \u2264 7.5%\r\n"
    original_bytes = text.encode("utf-8")

    assert tokenize(text) == ["hba1c", "<=", "7.5", "%"]
    assert text.encode("utf-8") == original_bytes


def test_count_terms_tracks_occurrences_and_total_length():
    counts = count_terms("Age age \u2265 18")

    assert counts == {"age": 2, ">=": 1, "18": 1}
    assert sum(counts.values()) == 4
    assert len(counts) == 3


def test_count_terms_returns_zero_for_missing_term():
    counts = count_terms("Age age")
    before = dict(counts)

    assert counts["insulin"] == 0
    assert dict(counts) == before


@pytest.mark.parametrize("text", ["", "?!"])
def test_count_terms_handles_text_without_tokens(text):
    counts = count_terms(text)

    assert counts == {}
    assert sum(counts.values()) == 0


def test_document_frequencies_count_passages_not_occurrences():
    passage_counts = [
        count_terms("insulin insulin age"),
        count_terms("age consent"),
    ]
    before = [dict(counts) for counts in passage_counts]

    assert document_frequencies(passage_counts) == {
        "insulin": 1, "age": 2, "consent": 1
    }
    assert [dict(counts) for counts in passage_counts] == before


def test_document_frequencies_handles_empty_corpus():
    frequencies = document_frequencies([])

    assert frequencies == {}
    assert frequencies["insulin"] == 0


def test_document_frequencies_ignores_empty_passage():
    assert document_frequencies([
        count_terms(""), count_terms("age age")
    ]) == {"age": 1}


@pytest.mark.parametrize(
    ("passage_count", "frequency", "expected"),
    [
        (10, 1, 1.992430164690206),
        (10, 8, 0.25782910930210006),
        (10, 10, 0.04652001563489291),
        (1, 1, 0.28768207245178085),
    ],
)
def test_idf_matches_known_values(passage_count, frequency, expected):
    assert inverse_document_frequency(passage_count, frequency) == pytest.approx(expected)


def test_idf_gives_rarer_terms_more_weight():
    assert inverse_document_frequency(10, 1) > inverse_document_frequency(10, 8) > 0


@pytest.mark.parametrize(
    ("passage_count", "frequency", "message"),
    [
        (0, 0, "Passage count must be positive"),
        (-1, 0, "Passage count must be positive"),
        (10, -1, "Document frequency is outside"),
        (10, 11, "Document frequency is outside"),
    ],
)
def test_idf_rejects_impossible_counts(passage_count, frequency, message):
    with pytest.raises(ValueError, match=message):
        inverse_document_frequency(passage_count, frequency)


def test_bm25_score_matches_known_numeric_result():
    from collections import Counter

    # N=10, df(age)=1, tf(age)=2, length=average_length=4.
    # With k1=1.2 the term-frequency multiplier is 4.4/3.2 = 1.375.
    score = bm25_score(
        ["age"], Counter({"age": 2, "other": 2}),
        Counter({"age": 1}), 10, 4.0,
    )

    assert score == pytest.approx(2.739591476449033)


def test_bm25_does_not_double_count_repeated_query_terms():
    counts = count_terms("age age consent")
    frequencies = document_frequencies([counts])

    single = bm25_score(["age", "consent"], counts, frequencies, 1, 3.0)
    repeated = bm25_score(
        ["consent", "age", "age", "consent"], counts, frequencies, 1, 3.0
    )

    assert repeated == single
    assert single > 0


def test_bm25_adjusts_for_passage_length():
    short = count_terms("age")
    long = count_terms("age filler filler filler filler filler filler filler filler filler")
    frequencies = document_frequencies([short, long])

    short_score = bm25_score(["age"], short, frequencies, 2, 5.5)
    long_score = bm25_score(["age"], long, frequencies, 2, 5.5)

    assert short_score > long_score > 0


@pytest.mark.parametrize(
    ("query", "text", "passage_count", "average_length"),
    [
        (["insulin"], "age consent", 1, 2.0),
        ([], "age consent", 1, 2.0),
        (["age"], "", 2, 1.0),
        (["age"], "", 0, 0.0),
        (["age"], "", 2, 0.0),
    ],
)
def test_bm25_zero_score_cases(query, text, passage_count, average_length):
    counts = count_terms(text)
    frequencies = document_frequencies([counts]) if passage_count else {}

    assert bm25_score(query, counts, frequencies, passage_count, average_length) == 0.0


@pytest.fixture
def sample_passage():
    from datetime import UTC, datetime
    from trial_explorer.normalize import normalize_study
    from trial_explorer.passages import build_passages

    study = normalize_study(
        {"protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {"eligibilityCriteria": "age"},
        }},
        datetime(2026, 11, 20, tzinfo=UTC),
        "test_snapshot",
    )
    return build_passages(study)[0]


def test_rank_passages_orders_by_score_and_excludes_nonmatches(sample_passage):
    from dataclasses import replace

    longer = replace(
        sample_passage, passage_id="long",
        text="age filler filler filler", search_text="age filler filler filler",
    )
    unrelated = replace(
        sample_passage, passage_id="unrelated", text="consent", search_text="consent",
    )
    results = rank_passages("age", [unrelated, longer, sample_passage])

    assert [passage.passage_id for passage, _ in results] == [
        sample_passage.passage_id, "long"
    ]
    assert results[0][1] > results[1][1] > 0


def test_rank_passages_resolves_ties_before_top_five(sample_passage):
    from dataclasses import replace

    passages = [
        replace(sample_passage, nct_id=f"NCT{n:08d}", passage_id=f"p{n}")
        for n in range(7, 0, -1)
    ]

    results = rank_passages("age", passages)

    assert [passage.nct_id for passage, _ in results] == [
        f"NCT{n:08d}" for n in range(1, 6)
    ]
    assert results == rank_passages("age", list(reversed(passages)))
    assert len({score for _, score in results}) == 1


def test_rank_passages_breaks_same_study_ties_by_offset_then_id(sample_passage):
    from dataclasses import replace

    passages = [
        replace(sample_passage, passage_id="b", source_start=5, source_end=8),
        replace(sample_passage, passage_id="a", source_start=5, source_end=8),
        replace(sample_passage, passage_id="z", source_start=0, source_end=3),
    ]
    assert [p.passage_id for p, _ in rank_passages("age", passages)] == ["z", "a", "b"]


def test_rank_passages_handles_empty_results(sample_passage):
    assert rank_passages("insulin", [sample_passage]) == []
    assert rank_passages("age", []) == []


@pytest.mark.parametrize("query", ["", " \t", "?!"])
def test_rank_passages_rejects_tokenless_query(query, sample_passage):
    with pytest.raises(ValueError, match="searchable tokens"):
        rank_passages(query, [sample_passage])


def test_rank_passages_rejects_mixed_snapshots(sample_passage):
    from dataclasses import replace

    with pytest.raises(ValueError, match="one snapshot"):
        rank_passages("age", [
            sample_passage, replace(sample_passage, snapshot_id="another_snapshot")
        ])


def test_filter_preserves_full_corpus_score(sample_passage):
    from dataclasses import replace

    other = replace(
        sample_passage, nct_id="NCT00000002", passage_id="other",
        text="age consent consent consent", search_text="age consent consent consent",
    )
    corpus = [sample_passage, other]
    unfiltered = rank_passages("age", corpus)

    filtered = rank_passages(
        "age", corpus, permitted_nct_ids={sample_passage.nct_id}
    )

    assert filtered == [unfiltered[0]]
    # Recomputing statistics on the subset would give a different score.
    assert filtered[0][1] != pytest.approx(rank_passages("age", [sample_passage])[0][1])


def test_filter_applies_before_top_five_cutoff(sample_passage):
    from dataclasses import replace

    corpus = [
        replace(sample_passage, nct_id=f"NCT{n:08d}", passage_id=f"p{n}")
        for n in range(1, 8)
    ]
    assert all(p.nct_id != "NCT00000007" for p, _ in rank_passages("age", corpus))

    filtered = rank_passages(
        "age", corpus, permitted_nct_ids={"NCT00000007"}
    )

    assert len(filtered) == 1
    assert filtered[0][0].nct_id == "NCT00000007"
    assert filtered[0][1] > 0


def test_filter_empty_set_permits_no_studies(sample_passage):
    assert rank_passages("age", [sample_passage], permitted_nct_ids=set()) == []
    assert rank_passages("age", [sample_passage], permitted_nct_ids=None)


def test_filter_permits_multiple_studies(sample_passage):
    from dataclasses import replace

    corpus = [
        replace(sample_passage, nct_id=f"NCT{n:08d}", passage_id=f"p{n}")
        for n in range(1, 4)
    ]
    results = rank_passages(
        "age", corpus, permitted_nct_ids={"NCT00000001", "NCT00000003"}
    )

    assert [p.nct_id for p, _ in results] == ["NCT00000001", "NCT00000003"]
