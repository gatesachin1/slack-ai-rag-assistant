"""Ingress Lambda (Function URL): verify Slack, enqueue the mention, ack within 3s.

Slack retries are no longer dropped here. A slow cold start can make Slack retry a
request we never enqueued, so every delivery is enqueued and the worker
de-duplicates on Slack's event_id.
"""

import base64
import json
import os

import boto3
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from slack_rag.config import Settings, get_secrets
from slack_rag.slack import verify_signature

MAX_BODY_BYTES = 64 * 1024

logger = Logger()
metrics = Metrics()
settings = Settings()
QUEUE_URL = os.environ["QUEUE_URL"]
sqs = boto3.client("sqs")


def _response(status: int, body: str = "") -> dict:
    return {"statusCode": status, "headers": {"Content-Type": "text/plain"}, "body": body}


def _should_handle(payload: dict, ev: dict) -> bool:
    if ev.get("type") != "app_mention" or ev.get("bot_id") or ev.get("subtype"):
        return False
    if settings.allowed_team_ids and payload.get("team_id") not in settings.allowed_team_ids:
        logger.warning("Rejected team", extra={"team_id": payload.get("team_id")})
        return False
    if settings.allowed_channel_ids and ev.get("channel") not in settings.allowed_channel_ids:
        logger.info("Ignored channel", extra={"channel": ev.get("channel")})
        return False
    return True


@logger.inject_lambda_context(clear_state=True)
@metrics.log_metrics
def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    if len(body) > MAX_BODY_BYTES:
        return _response(413)

    signing_secret = get_secrets(settings.secret_name)["signing_secret"]
    if not verify_signature(signing_secret, headers, body):
        metrics.add_metric(name="InvalidSignature", unit=MetricUnit.Count, value=1)
        return _response(401)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return _response(400)

    if payload.get("type") == "url_verification":
        return _response(200, payload.get("challenge", ""))

    ev = payload.get("event") or {}
    event_id = payload.get("event_id", "")
    logger.append_keys(slack_event_id=event_id, retry_num=headers.get("x-slack-retry-num"))
    if payload.get("type") != "event_callback" or not event_id or not _should_handle(payload, ev):
        return _response(200)

    message = {
        "event_id": event_id,
        "team_id": payload.get("team_id"),
        "channel": ev["channel"],
        "thread_ts": ev.get("thread_ts") or ev["ts"],
        "user": ev.get("user"),
        "text": ev.get("text", ""),
    }
    # Raising here returns 5xx so Slack retries the delivery.
    sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(message))
    metrics.add_metric(name="MentionsEnqueued", unit=MetricUnit.Count, value=1)
    logger.info("Mention enqueued")
    return _response(200)
