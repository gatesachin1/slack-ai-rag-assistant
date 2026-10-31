"""Worker Lambda (SQS): answer a Slack mention from the Bedrock Knowledge Base.

Failure policy:
- Transient errors (throttling, 5xx) raise, so SQS retries the message. On the
  final attempt the user is told, and the message goes to the DLQ.
- Permanent errors are reported to the user once and the message is consumed.
- Idempotency on Slack's event_id stops duplicate replies when Slack or SQS
  deliver the same mention more than once.
"""

import time

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    IdempotencyConfig,
    idempotent_function,
)

from slack_rag import rag
from slack_rag.config import WorkerSettings, get_secrets
from slack_rag.slack import RetryableError, extract_question, post_message, to_mrkdwn, truncate

ERROR_REPLY = "Sorry, I couldn't answer that right now. Please try again in a few minutes."
EMPTY_REPLY = "Ask me a question about our runbooks and policies, e.g. `@bot how do I debug OOMKilled pods?`"

logger = Logger()
metrics = Metrics()
settings = WorkerSettings()
# Always return partial-batch failures instead of failing the whole invocation.
processor = BatchProcessor(event_type=EventType.SQS, raise_on_entire_batch_failure=False)
RAG_CONFIG = rag.build_config(
    settings.kb_id,
    settings.model_arn,
    settings.number_of_results,
    settings.guardrail_id,
    settings.guardrail_version,
)
idempotency_config = IdempotencyConfig(
    event_key_jmespath="event_id",
    expires_after_seconds=24 * 3600,
    raise_on_no_idempotency_key=True,
)
persistence = DynamoDBPersistenceLayer(table_name=settings.idempotency_table)


def _reply(msg: dict, text: str) -> None:
    bot_token = get_secrets(settings.secret_name)["bot_token"]
    post_message(bot_token, msg["channel"], msg["thread_ts"], truncate(text))


def _answer_text(msg: dict) -> str:
    question = extract_question(msg.get("text", ""))
    if not question:
        return EMPTY_REPLY
    if len(question) > settings.max_question_chars:
        metrics.add_metric(name="QuestionTooLong", unit=MetricUnit.Count, value=1)
        return f"Please keep questions under {settings.max_question_chars} characters."

    logger.info(
        "Querying knowledge base",
        extra={"question_chars": len(question), **({"question": question} if settings.log_questions else {})},
    )
    started = time.monotonic()
    answer = rag.ask(question, RAG_CONFIG)
    metrics.add_metric(
        name="BedrockLatency", unit=MetricUnit.Milliseconds, value=(time.monotonic() - started) * 1000
    )
    if answer.guardrail_intervened:
        metrics.add_metric(name="GuardrailIntervened", unit=MetricUnit.Count, value=1)
    if not answer.sources:
        metrics.add_metric(name="UngroundedAnswer", unit=MetricUnit.Count, value=1)
    logger.info(
        "Answer generated",
        extra={"sources": list(answer.sources), "guardrail_intervened": answer.guardrail_intervened},
    )
    return to_mrkdwn(rag.format_reply(answer, settings.footer))


@idempotent_function(data_keyword_argument="msg", persistence_store=persistence, config=idempotency_config)
def handle_mention(msg: dict, final_attempt: bool) -> dict:
    try:
        _reply(msg, _answer_text(msg))
    except RetryableError:
        if final_attempt:
            _safe_error_reply(msg)
        raise
    except Exception:
        logger.exception("Permanent failure answering mention")
        metrics.add_metric(name="AnswerFailed", unit=MetricUnit.Count, value=1)
        _safe_error_reply(msg)
        return {"status": "failed"}
    metrics.add_metric(name="AnswersPosted", unit=MetricUnit.Count, value=1)
    return {"status": "answered"}


def _safe_error_reply(msg: dict) -> None:
    try:
        _reply(msg, ERROR_REPLY)
    except Exception:
        logger.exception("Could not post error reply")


def record_handler(record: SQSRecord) -> None:
    msg = record.json_body
    logger.append_keys(slack_event_id=msg.get("event_id"), channel=msg.get("channel"))
    attempt = int(record.attributes.approximate_receive_count or 1)
    handle_mention(msg=msg, final_attempt=attempt >= settings.max_receive_count)


@logger.inject_lambda_context(clear_state=True)
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    idempotency_config.register_lambda_context(context)
    return process_partial_response(
        event=event, record_handler=record_handler, processor=processor, context=context
    )
