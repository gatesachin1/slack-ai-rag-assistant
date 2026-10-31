import json

import pytest
from botocore.exceptions import ClientError

from slack_rag import rag, worker
from slack_rag.slack import RetryableError

KB_RESPONSE = {
    "output": {"text": "Check **logs** first."},
    "citations": [
        {
            "retrievedReferences": [
                {"location": {"s3Location": {"uri": "s3://bucket/docs/runbook-oomkilled.md"}}},
                {"location": {"s3Location": {"uri": "s3://bucket/docs/runbook-oomkilled.md"}}},
                {"location": {"s3Location": {"uri": "s3://bucket/docs/oncall%20handbook.md"}}},
            ]
        }
    ],
    "guardrailAction": "NONE",
}


def _sqs_event(receive_count=1, text="<@UBOT> pod OOMKilled?"):
    msg = {"event_id": "Ev1", "channel": "C1", "thread_ts": "1.1", "user": "U1", "text": text}
    return {
        "Records": [
            {
                "messageId": "m1",
                "receiptHandle": "r",
                "body": json.dumps(msg),
                "attributes": {"ApproximateReceiveCount": str(receive_count)},
                "messageAttributes": {},
                "md5OfBody": "",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:q",
                "awsRegion": "us-east-1",
            }
        ]
    }


@pytest.fixture
def posted(monkeypatch):
    replies = []
    monkeypatch.setattr(worker, "post_message", lambda token, ch, ts, text: replies.append(text))
    return replies


def _bedrock(monkeypatch, result):
    class Fake:
        def retrieve_and_generate(self, **kw):
            if isinstance(result, Exception):
                raise result
            return result

    monkeypatch.setattr(rag, "_client", Fake())


def _client_error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "RetrieveAndGenerate")


def test_answers_with_sources_and_footer(lambda_context, posted, monkeypatch):
    _bedrock(monkeypatch, KB_RESPONSE)
    resp = worker.handler(_sqs_event(), lambda_context)
    assert resp == {"batchItemFailures": []}
    reply = posted[0]
    assert reply.startswith("Check *logs* first.")
    assert "`runbook-oomkilled.md`, `oncall handbook.md`" in reply
    assert reply.rstrip().endswith("_Managed by the SRE team_")


def test_empty_question_gets_help(lambda_context, posted, monkeypatch):
    _bedrock(monkeypatch, AssertionError("must not call Bedrock"))
    worker.handler(_sqs_event(text="<@UBOT>"), lambda_context)
    assert posted == [worker.EMPTY_REPLY]


def test_throttling_retries_without_replying(lambda_context, posted, monkeypatch):
    _bedrock(monkeypatch, _client_error("ThrottlingException"))
    resp = worker.handler(_sqs_event(receive_count=1), lambda_context)
    assert resp == {"batchItemFailures": [{"itemIdentifier": "m1"}]}
    assert posted == []


def test_final_attempt_tells_user_and_fails(lambda_context, posted, monkeypatch):
    _bedrock(monkeypatch, _client_error("ThrottlingException"))
    resp = worker.handler(_sqs_event(receive_count=3), lambda_context)
    assert resp == {"batchItemFailures": [{"itemIdentifier": "m1"}]}
    assert posted == [worker.ERROR_REPLY]


def test_permanent_error_replies_once_and_consumes(lambda_context, posted, monkeypatch):
    _bedrock(monkeypatch, _client_error("ValidationException"))
    resp = worker.handler(_sqs_event(), lambda_context)
    assert resp == {"batchItemFailures": []}
    assert posted == [worker.ERROR_REPLY]


def test_slack_outage_is_retried(lambda_context, monkeypatch):
    _bedrock(monkeypatch, KB_RESPONSE)

    def boom(*a):
        raise RetryableError("slack down")

    monkeypatch.setattr(worker, "post_message", boom)
    resp = worker.handler(_sqs_event(), lambda_context)
    assert resp == {"batchItemFailures": [{"itemIdentifier": "m1"}]}


def test_guardrail_hides_sources():
    answer = rag.parse_response({**KB_RESPONSE, "guardrailAction": "INTERVENED"})
    assert "Sources" not in rag.format_reply(answer)


def test_build_config_with_guardrail():
    cfg = rag.build_config("KB", "arn", 4, "gr-1", "2")["knowledgeBaseConfiguration"]
    assert cfg["retrievalConfiguration"]["vectorSearchConfiguration"]["numberOfResults"] == 4
    assert cfg["generationConfiguration"]["guardrailConfiguration"] == {
        "guardrailId": "gr-1",
        "guardrailVersion": "2",
    }
    assert "generationConfiguration" not in rag.build_config("KB", "arn", 4)["knowledgeBaseConfiguration"]
