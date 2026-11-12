"""Build requests for the approved ClinicalTrials.gov study sample."""

import json
from collections.abc import Iterator
from time import sleep
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from errno import EHOSTUNREACH, ENETUNREACH
from socket import EAI_AGAIN, gaierror
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

STUDIES_ENDPOINT = "https://clinicaltrials.gov/api/v2/studies"
PAGE_CAP = 4
MAX_ATTEMPTS = 3
HTTP_TIMEOUT_SECONDS = 20
RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})

def build_studies_url(page_token: str | None = None) -> str:
    """Return the fixed query URL, optionally for a continuation page."""
    params = {
        "format": "json",
        "markupFormat": "markdown",
        "query.cond": "type 2 diabetes",
        "pageSize": "50",
        "sort": "LastUpdatePostDate:desc",
    }
    if page_token is not None:
        params["pageToken"] = page_token

    return f"{STUDIES_ENDPOINT}?{urlencode(params)}"


def fetch_studies_page(page_token: str | None = None) -> bytes:
    """Fetch one study page and return its raw response body."""
    url = build_studies_url(page_token)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return response.read()

        except HTTPError as error:
            if attempt == MAX_ATTEMPTS or not is_retryable_http_status(error.code):
                raise
            retry_after = error.headers.get("Retry-After") if error.headers else None
            delay = retry_after_seconds(retry_after, datetime.now(UTC))
            error.close()
            if delay is not None and delay > 30:
                raise
            sleep(attempt if delay is None else delay)
        except OSError as error:
            if attempt == MAX_ATTEMPTS or not is_retryable_network_error(error):
                raise
            sleep(attempt)


def is_retryable_network_error(error: OSError) -> bool:
    """Recognize retryable transport failures, including urllib wrappers."""
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, (TimeoutError, ConnectionError)):
        return True
    if isinstance(reason, gaierror):
        return reason.errno == EAI_AGAIN
    return isinstance(reason, OSError) and reason.errno in (EHOSTUNREACH, ENETUNREACH)


def is_retryable_http_status(status: int) -> bool:
    """Return whether the HTTP status is eligible for a retry."""
    return status in RETRYABLE_HTTP_STATUSES


def retry_after_seconds(value: str | None, now: datetime) -> float | None:
    """Return the requested delay, or None for a missing or invalid header."""
    if value is None:
        return None

    value = value.strip()
    if value.isascii() and value.isdecimal():
        return float(value)

    try:
        retry_at = parsedate_to_datetime(value)
    except (ValueError, OverflowError):
        return None

    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)

    return max(0.0, (retry_at - now).total_seconds())

def parse_studies_page(body: bytes) -> dict[str, object]:
    """Parse a response body and check that it contains a studies list."""
    page = json.loads(body)

    if not isinstance(page, dict):
        raise ValueError("Expected a JSON object for the study page")

    if not isinstance(page.get("studies"), list):
        raise ValueError("Expected 'studies' to be a list")

    if "nextPageToken" in page:
        token = page["nextPageToken"]
        if not isinstance(token, str) or not token.strip():
            raise ValueError("'nextPageToken' must be a non-blank string")
    return page

class PageSchemaError(ValueError):
    """A fetched response that could not be parsed as a study page."""

    def __init__(self, body: bytes) -> None:
        super().__init__("Malformed study page")
        self.body = body


def iter_studies_pages() -> Iterator[tuple[bytes, dict[str, object]]]:
    """Fetch and parse up to four study pages."""
    token = None
    seen_tokens: set[str] = set()
    for _ in range(PAGE_CAP):
        body = fetch_studies_page(token)
        try:
            page = parse_studies_page(body)
        except ValueError as error:
            raise PageSchemaError(body) from error
        yield body, page

        next_token = page.get("nextPageToken")
        if not isinstance(next_token,str):
            break

        if next_token in seen_tokens:
            raise ValueError("Repeated continuation token")
        seen_tokens.add(next_token)

        token = next_token