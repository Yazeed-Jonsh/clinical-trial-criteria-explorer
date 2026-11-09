"""Pure, strict normalization of a ClinicalTrials.gov v2 study dictionary."""

import re
from datetime import UTC, date, datetime

from trial_explorer.models import CriteriaState, Study

_MISSING = object()

# Confirmed against https://clinicaltrials.gov/api/oas/v2 on 2026-11-10.
SOURCE_STATUSES = frozenset({
    "ACTIVE_NOT_RECRUITING", "APPROVED_FOR_MARKETING", "AVAILABLE",
    "COMPLETED", "ENROLLING_BY_INVITATION", "NO_LONGER_AVAILABLE",
    "NOT_YET_RECRUITING", "RECRUITING", "SUSPENDED",
    "TEMPORARILY_NOT_AVAILABLE", "TERMINATED", "UNKNOWN", "WITHDRAWN",
    "WITHHELD",
})


class StudyNormalizationError(ValueError):
    """A stable error code and source path, without echoing the source record."""

    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        super().__init__(f"{code} at {path}: {message}")


def _required_object(value: object, path: str) -> dict[str, object]:
    if value is _MISSING:
        raise StudyNormalizationError("missing_required", path, "Required object absent")
    if not isinstance(value, dict):
        raise StudyNormalizationError("invalid_type", path, "Expected an object")
    return value


def _optional_path(record: dict[str, object], *keys: str) -> object:
    """Absent/null ancestors mean a missing leaf; explicit leaf null survives."""
    current: object = record
    for index, key in enumerate(keys):
        if current is _MISSING or current is None:
            return _MISSING
        if not isinstance(current, dict):
            path = ".".join(keys[:index])
            raise StudyNormalizationError("invalid_type", path, "Expected an object")
        current = current.get(key, _MISSING)
    return current


def _optional_text(value: object, path: str) -> str | None:
    if value is _MISSING or value is None:
        return None
    if not isinstance(value, str):
        raise StudyNormalizationError("invalid_type", path, "Expected text or null")
    return value


def normalize_study(
    raw_record: dict[str, object], retrieved_at: datetime, snapshot_id: str
) -> Study:
    """Validate one record without I/O, coercion, or modifying its input.

    Raise StudyNormalizationError on invalid input. No partial Study is returned.
    Validation order follows C01 of the approved design.
    """
    if not isinstance(retrieved_at, datetime) or retrieved_at.utcoffset() is None:
        raise StudyNormalizationError(
            "invalid_timestamp", "retrieved_at", "Expected a timezone-aware datetime"
        )
    utc_retrieved_at = retrieved_at.astimezone(UTC)
    if not isinstance(snapshot_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", snapshot_id
    ):
        raise StudyNormalizationError(
            "invalid_snapshot_id", "snapshot_id", "Expected a valid snapshot identifier"
        )

    root = _required_object(raw_record, "raw_record")
    protocol = _required_object(root.get("protocolSection", _MISSING), "protocolSection")
    identity_path = "protocolSection.identificationModule"
    identity = _required_object(protocol.get("identificationModule", _MISSING), identity_path)
    nct_id = identity.get("nctId", _MISSING)
    id_path = f"{identity_path}.nctId"
    if nct_id is _MISSING:
        raise StudyNormalizationError("missing_required", id_path, "Required ID absent")
    if not isinstance(nct_id, str):
        raise StudyNormalizationError("invalid_type", id_path, "Expected text")
    if not re.fullmatch(r"NCT[0-9]{8}", nct_id):
        raise StudyNormalizationError("invalid_nct_id", id_path, "Expected NCT and eight ASCII digits")

    title = _optional_text(identity.get("briefTitle", _MISSING), f"{identity_path}.briefTitle")
    criteria_keys = ("protocolSection", "eligibilityModule", "eligibilityCriteria")
    raw_criteria = _optional_path(root, *criteria_keys)
    criteria = _optional_text(raw_criteria, ".".join(criteria_keys))
    criteria_state: CriteriaState
    if raw_criteria is _MISSING:
        criteria_state = "missing"
    elif raw_criteria is None:
        criteria_state = "null"
    elif criteria == "":
        criteria_state = "empty"
    else:
        criteria_state = "present"

    status_keys = ("protocolSection", "statusModule", "overallStatus")
    status = _optional_text(_optional_path(root, *status_keys), ".".join(status_keys))
    if status is not None and status not in SOURCE_STATUSES:
        raise StudyNormalizationError("invalid_status", ".".join(status_keys), "Unknown source status")

    date_keys = ("protocolSection", "statusModule", "lastUpdatePostDateStruct", "date")
    source_date = _optional_text(_optional_path(root, *date_keys), ".".join(date_keys))
    if source_date is not None:
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", source_date):
                raise ValueError("Expected YYYY-MM-DD")
            date.fromisoformat(source_date)
        except ValueError:
            raise StudyNormalizationError(
                "invalid_date", ".".join(date_keys), "Expected a valid YYYY-MM-DD date"
            ) from None

    return Study(
        nct_id=nct_id, title=title, criteria_text=criteria,
        criteria_state=criteria_state,
        source_url=f"https://clinicaltrials.gov/study/{nct_id}",
        source_updated_at=source_date, retrieved_at=utc_retrieved_at,
        snapshot_id=snapshot_id, recruitment_status=status,
    )
