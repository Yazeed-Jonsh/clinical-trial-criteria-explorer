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
