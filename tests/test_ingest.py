"""Offline checks of the ClinicalTrials.gov request contract."""

from io import BytesIO
from urllib.parse import parse_qs, urlsplit

import pytest

from trial_explorer import ingest
from trial_explorer.ingest import build_studies_url


def test_first_page_uses_approved_query():
    url = urlsplit(build_studies_url())

    assert (url.scheme, url.netloc, url.path) == (
        "https", "clinicaltrials.gov", "/api/v2/studies"
    )
    assert parse_qs(url.query, keep_blank_values=True) == {
        "format": ["json"],
        "markupFormat": ["markdown"],
        "query.cond": ["type 2 diabetes"],
        "pageSize": ["50"],
        "sort": ["LastUpdatePostDate:desc"],
    }

def test_continuation_token_preserves_plus():
    url = urlsplit(build_studies_url("abc+123"))
    params = parse_qs(url.query)

    assert params["pageToken"] == ["abc+123"]

def test_fetch_studies_page_returns_raw_bytes(monkeypatch):
    body = b'{ "studies": [] }\n'
    response = BytesIO(body)
    calls = []

    def fake_urlopen(url, *, timeout):
        calls.append((url, timeout))
        return response

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)

    result = ingest.fetch_studies_page("abc+123")

    assert result == body
    assert calls == [(build_studies_url("abc+123"), 20)]
    assert response.closed


def test_parse_studies_page_keeps_empty_list_and_token():
    body = b'{"studies": [], "nextPageToken": "abc+123"}'

    assert ingest.parse_studies_page(body) == {
        "studies": [],
        "nextPageToken": "abc+123",
    }


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b'[]', "Expected a JSON object"),
        (b'{}', "Expected 'studies' to be a list"),
        (b'{"studies": null}', "Expected 'studies' to be a list"),
        (b'{"studies": {}}', "Expected 'studies' to be a list"),
        (b'{', "Expecting property name"),
    ],
)
def test_parse_studies_page_rejects_invalid_body(body, message):
    with pytest.raises(ValueError, match=message):
        ingest.parse_studies_page(body)


def test_parse_studies_page_accepts_missing_token():
    assert ingest.parse_studies_page(b'{"studies": []}') == {"studies": []}


@pytest.mark.parametrize("token_json", [b'null', b'123', b'""', b'"   "'])
def test_parse_studies_page_rejects_invalid_token(token_json):
    body = b'{"studies": [], "nextPageToken": ' + token_json + b'}'

    with pytest.raises(ValueError, match="nextPageToken.*non-blank string"):
        ingest.parse_studies_page(body)


def test_iter_studies_pages_follows_token_from_empty_page(monkeypatch):
    first = b'{ "studies": [], "nextPageToken": "next+1" }\n'
    second = b'{"studies": [{"example": true}]}'
    responses = iter([first, second])
    calls = []

    def fake_fetch(token):
        calls.append(token)
        return next(responses)

    monkeypatch.setattr(ingest, "fetch_studies_page", fake_fetch)

    assert list(ingest.iter_studies_pages()) == [
        (first, {"studies": [], "nextPageToken": "next+1"}),
        (second, {"studies": [{"example": True}]}),
    ]
    assert calls == [None, "next+1"]


def test_iter_studies_pages_caps_fetches_at_four(monkeypatch):
    calls = []

    def fake_fetch(token):
        calls.append(token)
        return ('{"studies": [], "nextPageToken": "%d"}' % len(calls)).encode()

    monkeypatch.setattr(ingest, "fetch_studies_page", fake_fetch)

    assert len(list(ingest.iter_studies_pages())) == 4
    assert calls == [None, "1", "2", "3"]


@pytest.mark.parametrize("tokens", [("A", "B", "A"), ("A", "B", "C", "A")])
def test_iter_studies_pages_rejects_repeated_token(monkeypatch, tokens):
    bodies = [b'{"studies": [], "nextPageToken": "%s"}' % t.encode() for t in tokens]
    responses = iter(bodies)
    calls = []

    def fake_fetch(token):
        calls.append(token)
        return next(responses)

    monkeypatch.setattr(ingest, "fetch_studies_page", fake_fetch)
    pages = ingest.iter_studies_pages()

    assert [next(pages)[0] for _ in bodies] == bodies
    with pytest.raises(ValueError, match="Repeated continuation token"):
        next(pages)

    assert calls == [None, *tokens[:-1]]


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, False), (404, False), (408, False), (429, True),
        (500, True), (501, False), (502, True), (503, True), (504, True),
    ],
)
def test_retryable_http_status_follows_policy(status, expected):
    assert ingest.is_retryable_http_status(status) is expected


@pytest.mark.parametrize(
    ("statuses", "expected_delays", "final_status"),
    [
        ((503, 429, 200), [1, 2], None),
        ((503, 503, 503), [1, 2], 503),
        ((404,), [], 404),
    ],
)
def test_fetch_studies_page_http_retries(
    monkeypatch, statuses, expected_delays, final_status
):
    from urllib.error import HTTPError

    responses = iter(statuses)
    events = []
    body = b'{"studies": []}'

    def fake_urlopen(url, *, timeout):
        events.append(("request", url, timeout))
        status = next(responses)
        if status != 200:
            raise HTTPError(url, status, "simulated failure", {}, None)
        return BytesIO(body)

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)
    monkeypatch.setattr(ingest, "sleep", lambda delay: events.append(("delay", delay)))

    if final_status is None:
        assert ingest.fetch_studies_page("next+1") == body
    else:
        with pytest.raises(HTTPError) as caught:
            ingest.fetch_studies_page("next+1")
        assert caught.value.code == final_status

    request = ("request", build_studies_url("next+1"), 20)
    expected_events = [request]
    for delay in expected_delays:
        expected_events.extend([("delay", delay), request])
    assert events == expected_events


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Fri, 13 Nov 2026 12:00:05 GMT", 5),
        ("Fri, 13 Nov 2026 11:59:55 GMT", 0),
        ("tomorrow", None),
    ],
)
def test_retry_after_seconds(value, expected):
    from datetime import UTC, datetime

    now = datetime(2026, 11, 13, 12, tzinfo=UTC)

    assert ingest.retry_after_seconds(value, now) == expected


@pytest.mark.parametrize(
    ("header", "expected_delay"),
    [("0", 0), ("5", 5), ("30", 30), ("31", None), ("invalid", 1)],
)
def test_fetch_studies_page_honors_retry_after(monkeypatch, header, expected_delay):
    from email.message import Message
    from urllib.error import HTTPError

    headers = Message()
    headers["retry-after"] = header
    error_body = BytesIO(b"server unavailable")
    error = HTTPError(build_studies_url(), 503, "simulated failure", headers, error_body)
    events = []

    def fake_urlopen(url, *, timeout):
        events.append("request")
        if len(events) == 1:
            raise error
        return BytesIO(b'{"studies": []}')

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)
    monkeypatch.setattr(ingest, "sleep", lambda delay: events.append(delay))

    if expected_delay is None:
        with pytest.raises(HTTPError) as caught:
            ingest.fetch_studies_page()
        assert caught.value is error
        assert events == ["request"]
    else:
        assert ingest.fetch_studies_page() == b'{"studies": []}'
        assert events == ["request", expected_delay, "request"]
    assert error_body.closed


@pytest.mark.parametrize("failures", ["recover", "exhaust", "certificate"])
def test_fetch_studies_page_network_retries(monkeypatch, failures):
    from socket import EAI_AGAIN, gaierror
    from ssl import SSLCertVerificationError
    from urllib.error import HTTPError, URLError

    url = build_studies_url("next+1")
    body = b'{"studies": []}'
    if failures == "recover":
        errors = [URLError(gaierror(EAI_AGAIN, "temporary DNS failure")),
                  URLError(ConnectionRefusedError("connection refused"))]
        final_error = None
    elif failures == "exhaust":
        errors = [TimeoutError("timed out"),
                  HTTPError(url, 503, "unavailable", {}, None),
                  ConnectionResetError("connection reset")]
        final_error = errors[-1]
    else:
        errors = [URLError(SSLCertVerificationError("invalid certificate"))]
        final_error = errors[-1]

    events = []
    remaining_errors = iter(errors)

    def fake_urlopen(request_url, *, timeout):
        events.append(("request", request_url, timeout))
        error = next(remaining_errors, None)
        if error is not None:
            raise error
        return BytesIO(body)

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)
    monkeypatch.setattr(ingest, "sleep", lambda delay: events.append(("delay", delay)))

    if final_error is None:
        assert ingest.fetch_studies_page("next+1") == body
    else:
        with pytest.raises(type(final_error)) as caught:
            ingest.fetch_studies_page("next+1")
        assert caught.value is final_error

    request = ("request", url, 20)
    expected = [request]
    if failures != "certificate":
        expected.extend([("delay", 1), request, ("delay", 2), request])
    assert events == expected
