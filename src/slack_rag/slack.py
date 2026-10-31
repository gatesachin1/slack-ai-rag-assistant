"""Slack primitives: request signature verification, text helpers, chat.postMessage."""

import hashlib
import hmac
import json
import re
import time
import urllib.error
import urllib.request

MAX_SKEW_SECONDS = 300
# chat.postMessage truncates text at 40k chars; stay well under it.
MAX_MESSAGE_CHARS = 38_000
_MENTION = re.compile(r"<@[A-Z0-9]+>")
_BOLD = re.compile(r"\*\*(.+?)\*\*")


class RetryableError(Exception):
    """A transient failure; the message should be retried by SQS."""


def verify_signature(signing_secret: str, headers: dict, body: str, now: float | None = None) -> bool:
    """Validate X-Slack-Signature and reject stale timestamps (replay protection)."""
    ts = headers.get("x-slack-request-timestamp", "")
    sig = headers.get("x-slack-signature", "")
    if not ts.isdigit() or not sig:
        return False
    if abs((now or time.time()) - int(ts)) > MAX_SKEW_SECONDS:
        return False
    base = f"v0:{ts}:{body}".encode()
    expected = "v0=" + hmac.new(signing_secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def extract_question(text: str) -> str:
    """Strip bot mentions and surrounding whitespace from a mention's text."""
    return _MENTION.sub("", text or "").strip()


def to_mrkdwn(text: str) -> str:
    """Bedrock returns Markdown; Slack mrkdwn uses single '*' for bold."""
    return _BOLD.sub(r"*\1*", text)


def truncate(text: str, limit: int = MAX_MESSAGE_CHARS) -> str:
    return text if len(text) <= limit else text[: limit - 20].rstrip() + "\n…(truncated)"


def post_message(bot_token: str, channel: str, thread_ts: str, text: str, timeout: float = 10) -> None:
    """Reply in a thread. Raises RetryableError on throttling / 5xx / network errors."""
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(
            {"channel": channel, "thread_ts": thread_ts, "text": text, "unfurl_links": False}
        ).encode(),
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https URL
            result = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 429 or exc.code >= 500:
            raise RetryableError(f"Slack HTTP {exc.code}") from exc
        raise
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RetryableError(f"Slack unreachable: {exc}") from exc

    # Slack returns HTTP 200 with ok=false for API-level errors.
    if not result.get("ok"):
        error = result.get("error", "unknown_error")
        if error in {"ratelimited", "internal_error", "service_unavailable", "request_timeout"}:
            raise RetryableError(f"Slack API error: {error}")
        raise RuntimeError(f"Slack API error: {error}")
