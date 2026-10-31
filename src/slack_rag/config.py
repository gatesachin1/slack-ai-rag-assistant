"""Runtime configuration, read once per execution environment.

Required values fail fast at cold start with a clear error instead of a KeyError
buried in a request path. Secrets are cached with a TTL so rotation is picked up
without a redeploy.
"""

import os
from dataclasses import dataclass, field

from aws_lambda_powertools.utilities import parameters

SECRET_CACHE_SECONDS = 300


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _env(name: str, default: str = ""):
    return field(default_factory=lambda: os.environ.get(name, default).strip())


def _int(name: str, default: int):
    return field(default_factory=lambda: int(os.environ.get(name, default)))


def _csv(name: str):
    return field(
        default_factory=lambda: frozenset(v.strip() for v in os.environ.get(name, "").split(",") if v.strip())
    )


@dataclass(frozen=True)
class Settings:
    secret_name: str = field(default_factory=lambda: _required("SECRET_NAME"))
    # Optional allow-lists. Empty means "allow all".
    allowed_team_ids: frozenset[str] = _csv("ALLOWED_TEAM_IDS")
    allowed_channel_ids: frozenset[str] = _csv("ALLOWED_CHANNEL_IDS")


@dataclass(frozen=True)
class WorkerSettings(Settings):
    kb_id: str = field(default_factory=lambda: _required("KB_ID"))
    model_arn: str = field(default_factory=lambda: _required("MODEL_ARN"))
    idempotency_table: str = field(default_factory=lambda: _required("IDEMPOTENCY_TABLE"))
    guardrail_id: str = _env("GUARDRAIL_ID")
    guardrail_version: str = _env("GUARDRAIL_VERSION", "DRAFT")
    number_of_results: int = _int("KB_NUMBER_OF_RESULTS", 5)
    max_question_chars: int = _int("MAX_QUESTION_CHARS", 1000)
    # Must match the SQS redrive maxReceiveCount; on the last attempt we tell the user.
    max_receive_count: int = _int("MAX_RECEIVE_COUNT", 3)
    footer: str = _env("ANSWER_FOOTER")
    log_questions: bool = field(
        default_factory=lambda: os.environ.get("LOG_QUESTIONS", "false").lower() == "true"
    )


def get_secrets(secret_name: str) -> dict:
    """Slack bot token + signing secret, cached in memory for SECRET_CACHE_SECONDS."""
    return parameters.get_secret(secret_name, transform="json", max_age=SECRET_CACHE_SECONDS)
