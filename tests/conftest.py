import hashlib
import hmac
import json
import os
import time
from types import SimpleNamespace

import pytest

os.environ.update(
    AWS_DEFAULT_REGION="us-east-1",
    AWS_ACCESS_KEY_ID="test",
    AWS_SECRET_ACCESS_KEY="test",
    SECRET_NAME="slack-rag-bot",
    QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789012/slack-rag",
    KB_ID="KB123",
    MODEL_ARN="arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0",
    IDEMPOTENCY_TABLE="slack-rag-idempotency",
    ANSWER_FOOTER="Managed by the SRE team",
    POWERTOOLS_IDEMPOTENCY_DISABLED="true",
    POWERTOOLS_METRICS_NAMESPACE="SlackRag",
    POWERTOOLS_SERVICE_NAME="slack-rag",
)

SIGNING_SECRET = "s3cr3t"
SECRETS = {"signing_secret": SIGNING_SECRET, "bot_token": "xoxb-test"}


@pytest.fixture(autouse=True)
def fake_secrets(monkeypatch):
    import slack_rag.config as config

    monkeypatch.setattr(config.parameters, "get_secret", lambda *a, **k: SECRETS)


@pytest.fixture
def lambda_context():
    return SimpleNamespace(
        function_name="test",
        memory_limit_in_mb=256,
        invoked_function_arn="arn:aws:lambda:us-east-1:123456789012:function:test",
        aws_request_id="req-1",
        get_remaining_time_in_millis=lambda: 30_000,
    )


def signed_request(payload: dict, ts: int | None = None, secret: str = SIGNING_SECRET, **headers) -> dict:
    body = json.dumps(payload)
    ts = str(ts or int(time.time()))
    sig = "v0=" + hmac.new(secret.encode(), f"v0:{ts}:{body}".encode(), hashlib.sha256).hexdigest()
    return {
        "headers": {"X-Slack-Request-Timestamp": ts, "X-Slack-Signature": sig, **headers},
        "body": body,
        "isBase64Encoded": False,
    }
