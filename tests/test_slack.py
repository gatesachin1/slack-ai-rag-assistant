import io
import json
import urllib.error

import pytest

from slack_rag import slack


def _sig_headers(req):
    return {k.lower(): v for k, v in req["headers"].items()}


def test_valid_signature():
    from conftest import SIGNING_SECRET, signed_request

    req = signed_request({"a": 1})
    assert slack.verify_signature(SIGNING_SECRET, _sig_headers(req), req["body"])


@pytest.mark.parametrize(
    "mutate",
    [
        lambda h, b: (h, b + " "),  # tampered body
        lambda h, b: ({**h, "x-slack-signature": "v0=00"}, b),  # wrong signature
        lambda h, b: ({**h, "x-slack-request-timestamp": "abc"}, b),  # non-numeric ts
        lambda h, b: ({k: v for k, v in h.items() if "signature" not in k}, b),
    ],
)
def test_invalid_signature(mutate):
    from conftest import SIGNING_SECRET, signed_request

    req = signed_request({"a": 1})
    headers, body = mutate(_sig_headers(req), req["body"])
    assert not slack.verify_signature(SIGNING_SECRET, headers, body)


def test_stale_timestamp_rejected():
    from conftest import SIGNING_SECRET, signed_request

    req = signed_request({"a": 1}, ts=1_000)
    assert not slack.verify_signature(SIGNING_SECRET, _sig_headers(req), req["body"])


def test_extract_question_and_mrkdwn():
    assert slack.extract_question("<@U123ABC>  what is an SLO? ") == "what is an SLO?"
    assert slack.extract_question("") == ""
    assert slack.to_mrkdwn("use **kubectl** and **logs**") == "use *kubectl* and *logs*"


def test_truncate():
    assert slack.truncate("short") == "short"
    out = slack.truncate("x" * 100, limit=50)
    assert len(out) <= 50 and out.endswith("(truncated)")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _urlopen_returning(payload):
    return lambda req, timeout: _Resp(json.dumps(payload).encode())


def test_post_message_ok(monkeypatch):
    seen = {}

    def fake(req, timeout):
        seen["body"] = json.loads(req.data)
        return _Resp(b'{"ok": true}')

    monkeypatch.setattr(slack.urllib.request, "urlopen", fake)
    slack.post_message("xoxb", "C1", "123.4", "hi")
    assert seen["body"] == {"channel": "C1", "thread_ts": "123.4", "text": "hi", "unfurl_links": False}


def test_post_message_api_errors(monkeypatch):
    monkeypatch.setattr(
        slack.urllib.request, "urlopen", _urlopen_returning({"ok": False, "error": "ratelimited"})
    )
    with pytest.raises(slack.RetryableError):
        slack.post_message("xoxb", "C1", "1", "hi")

    monkeypatch.setattr(
        slack.urllib.request, "urlopen", _urlopen_returning({"ok": False, "error": "channel_not_found"})
    )
    with pytest.raises(RuntimeError):
        slack.post_message("xoxb", "C1", "1", "hi")


def test_post_message_http_429_is_retryable(monkeypatch):
    def fake(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(slack.urllib.request, "urlopen", fake)
    with pytest.raises(slack.RetryableError):
        slack.post_message("xoxb", "C1", "1", "hi")
