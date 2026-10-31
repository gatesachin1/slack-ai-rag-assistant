import base64
import json

import pytest

from conftest import signed_request
from slack_rag import ingress


@pytest.fixture
def sent(monkeypatch):
    messages = []
    monkeypatch.setattr(ingress.sqs, "send_message", lambda **kw: messages.append(kw))
    return messages


def _mention(**ev):
    return {
        "type": "event_callback",
        "event_id": "Ev123",
        "team_id": "T1",
        "event": {
            "type": "app_mention",
            "channel": "C1",
            "ts": "111.1",
            "user": "U1",
            "text": "<@UBOT> hi",
            **ev,
        },
    }


def test_rejects_bad_signature(lambda_context, sent):
    req = signed_request(_mention(), secret="wrong")
    assert ingress.handler(req, lambda_context)["statusCode"] == 401
    assert not sent


def test_url_verification(lambda_context, sent):
    resp = ingress.handler(signed_request({"type": "url_verification", "challenge": "abc"}), lambda_context)
    assert resp["statusCode"] == 200 and resp["body"] == "abc"


def test_enqueues_mention(lambda_context, sent):
    assert ingress.handler(signed_request(_mention()), lambda_context)["statusCode"] == 200
    body = json.loads(sent[0]["MessageBody"])
    assert body["event_id"] == "Ev123" and body["thread_ts"] == "111.1" and body["text"] == "<@UBOT> hi"


def test_replies_in_existing_thread(lambda_context, sent):
    ingress.handler(signed_request(_mention(thread_ts="100.0")), lambda_context)
    assert json.loads(sent[0]["MessageBody"])["thread_ts"] == "100.0"


def test_retries_are_enqueued_for_worker_dedup(lambda_context, sent):
    req = signed_request(_mention(), **{"X-Slack-Retry-Num": "1"})
    ingress.handler(req, lambda_context)
    assert len(sent) == 1


def test_base64_body(lambda_context, sent):
    req = signed_request(_mention())
    req["body"] = base64.b64encode(req["body"].encode()).decode()
    req["isBase64Encoded"] = True
    ingress.handler(req, lambda_context)
    assert len(sent) == 1


@pytest.mark.parametrize("ev", [{"bot_id": "B1"}, {"subtype": "message_changed"}, {"type": "message"}])
def test_ignores_non_user_mentions(lambda_context, sent, ev):
    assert ingress.handler(signed_request(_mention(**ev)), lambda_context)["statusCode"] == 200
    assert not sent


def test_team_allow_list(lambda_context, sent, monkeypatch):
    monkeypatch.setattr(ingress, "settings", ingress.Settings(allowed_team_ids=frozenset({"T-other"})))
    ingress.handler(signed_request(_mention()), lambda_context)
    assert not sent


def test_invalid_json(lambda_context, sent):
    req = signed_request({})
    req = {**req, "body": "not-json"}
    # Signature no longer matches the body, so this is a 401, never a crash.
    assert ingress.handler(req, lambda_context)["statusCode"] == 401
