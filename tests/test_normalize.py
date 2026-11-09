"""Synthetic fixtures only: these are not fetched clinical study records."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from trial_explorer.normalize import StudyNormalizationError, normalize_study

NOW = datetime(2026, 11, 10, 12, 30, 0, 123456, tzinfo=UTC)
SNAPSHOT = "synthetic_day2"


@pytest.fixture
def record():
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Synthetic trial"},
            "eligibilityModule": {"eligibilityCriteria": "  HbA1c >= 7%; no insulin.\r\n"},
            "statusModule": {
                "overallStatus": "RECRUITING",
                "lastUpdatePostDateStruct": {"date": "2026-11-01"},
            },
        }
    }


def test_valid_record_preserves_source_and_input(record):
    before = deepcopy(record)
    study = normalize_study(record, NOW, SNAPSHOT)
    assert study.nct_id == "NCT00000001"
    assert study.title == "Synthetic trial"
    assert study.criteria_text == "  HbA1c >= 7%; no insulin.\r\n"
    assert study.criteria_state == "present"
    assert study.source_url == "https://clinicaltrials.gov/study/NCT00000001"
    assert study.source_updated_at == "2026-11-01"
    assert study.recruitment_status == "RECRUITING"
    assert study.retrieved_at == NOW
    assert study.snapshot_id == SNAPSHOT
    assert record == before


def test_missing_optional_title_is_none(record):
    del record["protocolSection"]["identificationModule"]["briefTitle"]
    assert normalize_study(record, NOW, SNAPSHOT).title is None


def test_missing_required_id_is_error(record):
    del record["protocolSection"]["identificationModule"]["nctId"]
    with pytest.raises(StudyNormalizationError) as error:
        normalize_study(record, NOW, SNAPSHOT)
    assert error.value.code == "missing_required"
    assert error.value.path == "protocolSection.identificationModule.nctId"
    assert "HbA1c" not in str(error.value)


@pytest.mark.parametrize("value,state", [(None, "null"), ("", "empty"), (" \t", "present")])
def test_criteria_presence_is_distinct(record, value, state):
    record["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = value
    study = normalize_study(record, NOW, SNAPSHOT)
    assert study.criteria_text == value
    assert study.criteria_state == state


def test_missing_criteria_leaf(record):
    record["protocolSection"]["eligibilityModule"] = {}
    study = normalize_study(record, NOW, SNAPSHOT)
    assert study.criteria_text is None and study.criteria_state == "missing"


@pytest.mark.parametrize("module", [None, {}])
def test_optional_ancestor_can_be_null_or_empty(record, module):
    record["protocolSection"]["eligibilityModule"] = module
    assert normalize_study(record, NOW, SNAPSHOT).criteria_state == "missing"


def test_only_required_source_fields(record):
    minimal = {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}
    study = normalize_study(minimal, NOW, SNAPSHOT)
    assert study.title is None and study.recruitment_status is None
    assert study.source_updated_at is None and study.criteria_state == "missing"


@pytest.mark.parametrize("value", ["nct00000001", "NCT0000001", "NCT00000001\n", " NCT00000001", "NCT１２３４５６７８"])
def test_id_is_not_repaired(record, value):
    record["protocolSection"]["identificationModule"]["nctId"] = value
    with pytest.raises(StudyNormalizationError, match="invalid_nct_id"):
        normalize_study(record, NOW, SNAPSHOT)


@pytest.mark.parametrize("value", [12, True, [], {}])
def test_optional_text_is_not_coerced(record, value):
    record["protocolSection"]["identificationModule"]["briefTitle"] = value
    with pytest.raises(StudyNormalizationError) as error:
        normalize_study(record, NOW, SNAPSHOT)
    assert error.value.code == "invalid_type"
    assert error.value.path.endswith("briefTitle")


@pytest.mark.parametrize("module", ["eligibilityModule", "statusModule"])
def test_malformed_nested_object_reports_its_path(record, module):
    record["protocolSection"][module] = []
    with pytest.raises(StudyNormalizationError) as error:
        normalize_study(record, NOW, SNAPSHOT)
    assert error.value.path == f"protocolSection.{module}"


@pytest.mark.parametrize("raw,code,path", [
    ([], "invalid_type", "raw_record"),
    ({}, "missing_required", "protocolSection"),
    ({"protocolSection": None}, "invalid_type", "protocolSection"),
    ({"protocolSection": {}}, "missing_required", "protocolSection.identificationModule"),
])
def test_invalid_required_structure(raw, code, path):
    with pytest.raises(StudyNormalizationError) as error:
        normalize_study(raw, NOW, SNAPSHOT)
    assert (error.value.code, error.value.path) == (code, path)


@pytest.mark.parametrize("value", ["2026-02-30", "2026-11", "20261101", "2026-11-01T00:00:00Z"])
def test_source_date_must_be_real_and_complete(record, value):
    record["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"] = value
    with pytest.raises(StudyNormalizationError, match="invalid_date"):
        normalize_study(record, NOW, SNAPSHOT)


def test_unknown_status_is_not_guessed(record):
    record["protocolSection"]["statusModule"]["overallStatus"] = "recruiting"
    with pytest.raises(StudyNormalizationError, match="invalid_status"):
        normalize_study(record, NOW, SNAPSHOT)


def test_timestamp_converts_to_utc_and_preserves_microseconds(record):
    local = NOW.astimezone(timezone(timedelta(hours=3)))
    study = normalize_study(record, local, SNAPSHOT)
    assert study.retrieved_at == NOW
    assert study.retrieved_at.tzinfo is UTC
    assert study.retrieved_at.microsecond == 123456


@pytest.mark.parametrize("timestamp", [datetime(2026, 11, 10), "2026-11-10T12:30:00Z", None])
def test_invalid_timestamp_precedes_other_source_errors(timestamp):
    with pytest.raises(StudyNormalizationError) as error:
        normalize_study({}, timestamp, SNAPSHOT)
    assert error.value.code == "invalid_timestamp"


@pytest.mark.parametrize("snapshot", ["", "../data", "x" * 81, 1])
def test_invalid_snapshot_precedes_source_validation(snapshot):
    with pytest.raises(StudyNormalizationError, match="invalid_snapshot_id"):
        normalize_study({}, NOW, snapshot)


def test_record_fields_cannot_be_reassigned(record):
    study = normalize_study(record, NOW, SNAPSHOT)
    with pytest.raises(FrozenInstanceError):
        study.nct_id = "NCT00000002"
