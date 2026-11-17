"""Check how synthetic criteria lines are classified."""
import pytest
from datetime import UTC, datetime
from trial_explorer.normalize import normalize_study
from trial_explorer.passages import build_passages
from trial_explorer.passages import criteria_heading, iter_criteria_sections, iter_paragraph_spans


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("  ## Inclusion Criteria:\r\n", "inclusion criteria"),
        ("EXCLUSION CRITERIA\n", "exclusion criteria"),
        ("See inclusion criteria below.\n", None),
        ("- Exclusion Criteria:\n", None),
        ("Inclusion Criteria::", None),
    ],
)
def test_criteria_heading_matches_whole_line(line, expected):
    assert criteria_heading(line) == expected


def test_sections_start_at_first_heading():
    inclusion = "Inclusion Criteria:\r\n- A\r\n"
    exclusion = "## Exclusion Criteria:\n- B"
    text = inclusion + exclusion

    assert list(iter_criteria_sections(text)) == [
        (0, len(inclusion), "inclusion criteria"),
        (len(inclusion), len(text), "exclusion criteria"),
    ]


def test_sections_keep_unnamed_text_before_heading():
    text = "Age \u2265 18\r\nExclusion Criteria:\n- B"

    sections = list(iter_criteria_sections(text))

    assert sections == [(0, 10, None), (10, len(text), "exclusion criteria")]
    assert [text[start:end] for start, end, _ in sections] == [
        "Age \u2265 18\r\n",
        "Exclusion Criteria:\n- B",
    ]


def test_paragraph_spans_preserve_nested_lines_and_original_offsets():
    prefix = "Introduction\n"
    heading = "Inclusion Criteria:\r\n"
    first = "- Age \u2265 18.\r\n  - Bring proof of age.\r\n"
    blank = " \t\r\n"
    final = "- Exception: Ages 16-17 with guardian consent."
    text = prefix + heading + first + blank + final
    start = len(prefix)
    first_start = start + len(heading)
    final_start = first_start + len(first) + len(blank)

    spans = list(iter_paragraph_spans(text, start, len(text)))

    assert spans == [(first_start, first_start + len(first)), (final_start, len(text))]
    assert [text[a:b] for a, b in spans] == [first, final]


@pytest.mark.parametrize("text", ["", " \t\r\n", "Inclusion Criteria:\n\n"])
def test_paragraph_spans_skip_sections_without_content(text):
    assert list(iter_paragraph_spans(text, 0, len(text))) == []


def test_paragraph_spans_respect_section_end():
    first = "Inclusion Criteria:\n- A\n"
    text = first + "Exclusion Criteria:\n- B\n"

    assert list(iter_paragraph_spans(text, 0, len(first))) == [(20, len(first))]

def test_build_passages_keeps_exception_in_parent():
    text = (
        "Inclusion Criteria:\n"
        "- Age at least 18.\n"
        "\n"
        "- Exception: Ages 16-17 with guardian consent."
    )
    raw = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {"eligibilityCriteria": text},
        }
    }
    study = normalize_study(
        raw,
        retrieved_at=datetime(2026, 11, 17, tzinfo=UTC),
        snapshot_id="test_snapshot",
    )

    passages = build_passages(study)

    assert len(passages) == 2
    assert passages[0].text == "- Age at least 18.\n"
    assert passages[1].text == "- Exception: Ages 16-17 with guardian consent."
    for passage in passages:
        assert passage.parent_text == text
        assert passage.heading == "inclusion criteria"
        assert text[passage.source_start:passage.source_end] == passage.text
        assert text[passage.parent_source_start:passage.parent_source_end] == passage.parent_text


def test_passage_ids_are_stable_and_snapshot_specific():
    from dataclasses import replace

    raw = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {
                "eligibilityCriteria": "Inclusion Criteria:\n- A\n\n- B\n"
            },
        }
    }
    study = normalize_study(
        raw,
        retrieved_at=datetime(2026, 11, 17, tzinfo=UTC),
        snapshot_id="snapshot_a",
    )

    first_ids = [p.passage_id for p in build_passages(study)]
    repeated_ids = [p.passage_id for p in build_passages(study)]
    other_ids = [
        p.passage_id
        for p in build_passages(replace(study, snapshot_id="snapshot_b"))
    ]

    assert len(first_ids) == len(set(first_ids)) == 2
    assert first_ids == repeated_ids
    assert set(first_ids).isdisjoint(other_ids)
    assert first_ids == [
        "p:paragraph-v1:snapshot_a:NCT00000001:20:24",
        "p:paragraph-v1:snapshot_a:NCT00000001:25:29",
    ]
