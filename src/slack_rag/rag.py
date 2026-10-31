"""Bedrock Knowledge Base query and answer formatting."""

from dataclasses import dataclass
from urllib.parse import unquote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from slack_rag.slack import RetryableError

RETRYABLE_CODES = {
    "ThrottlingException",
    "ServiceQuotaExceededException",
    "InternalServerException",
    "DependencyFailedException",
    "BadGatewayException",
    "ServiceUnavailableException",
}

_client = None


def client():
    global _client
    if _client is None:
        _client = boto3.client(
            "bedrock-agent-runtime",
            config=Config(
                retries={"mode": "adaptive", "max_attempts": 4},
                connect_timeout=5,
                read_timeout=50,
            ),
        )
    return _client


@dataclass(frozen=True)
class Answer:
    text: str
    sources: tuple[str, ...]
    guardrail_intervened: bool


def build_config(
    kb_id: str,
    model_arn: str,
    number_of_results: int,
    guardrail_id: str = "",
    guardrail_version: str = "DRAFT",
) -> dict:
    kb_config = {
        "knowledgeBaseId": kb_id,
        "modelArn": model_arn,
        "retrievalConfiguration": {"vectorSearchConfiguration": {"numberOfResults": number_of_results}},
    }
    if guardrail_id:
        kb_config["generationConfiguration"] = {
            "guardrailConfiguration": {
                "guardrailId": guardrail_id,
                "guardrailVersion": guardrail_version,
            }
        }
    return {"type": "KNOWLEDGE_BASE", "knowledgeBaseConfiguration": kb_config}


def parse_response(resp: dict) -> Answer:
    sources: list[str] = []
    for citation in resp.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            uri = ref.get("location", {}).get("s3Location", {}).get("uri")
            if uri:
                name = unquote(uri.rsplit("/", 1)[-1])
                if name not in sources:
                    sources.append(name)
    return Answer(
        text=resp.get("output", {}).get("text", "").strip(),
        sources=tuple(sources),
        guardrail_intervened=resp.get("guardrailAction") == "INTERVENED",
    )


def ask(question: str, rag_config: dict) -> Answer:
    try:
        resp = client().retrieve_and_generate(
            input={"text": question},
            retrieveAndGenerateConfiguration=rag_config,
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in RETRYABLE_CODES:
            raise RetryableError(str(exc)) from exc
        raise
    return parse_response(resp)


def format_reply(answer: Answer, footer: str = "") -> str:
    parts = [answer.text or "I couldn't find an answer to that in the knowledge base."]
    if answer.sources and not answer.guardrail_intervened:
        parts.append("*Sources:* " + ", ".join(f"`{s}`" for s in answer.sources))
    if footer and footer not in parts[0]:
        parts.append(f"_{footer}_")
    return "\n\n".join(parts)
