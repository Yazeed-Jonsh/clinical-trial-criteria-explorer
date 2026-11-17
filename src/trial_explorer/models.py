"""Internal records: external data must enter through normalization."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

CriteriaState = Literal["missing", "null", "empty", "present"]


@dataclass(frozen=True)
class Study:
    """A normalized source record, not an assessment of eligibility.

    Type annotations describe the record but do not validate constructor inputs.
    Use normalize_study for untrusted input. Datetime serialization belongs to
    the later persistence boundary; retrieved_at is UTC inside this record.
    """

    nct_id: str
    title: str | None
    criteria_text: str | None
    criteria_state: CriteriaState
    source_url: str
    source_updated_at: str | None
    retrieved_at: datetime
    snapshot_id: str
    recruitment_status: str | None

@dataclass(frozen=True)
class Passage:
    """An exact span of eligibility text and its enclosing section."""

    snapshot_id: str
    nct_id: str
    passage_id: str
    segmentation_version: str

    source_start: int
    source_end: int
    text: str
    heading: str | None
    parent_source_start: int
    parent_source_end: int
    parent_text: str
    search_text: str
