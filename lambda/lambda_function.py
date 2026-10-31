import json, os, re, hmac, hashlib, time, base64, urllib.request
import boto3

lam = boto3.client("lambda")
bedrock = boto3.client("bedrock-agent-runtime")
sm = boto3.client("secretsmanager")

KB_ID = os.environ["KB_ID"]
MODEL_ARN = os.environ["MODEL_ARN"]
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "DRAFT")
SECRETS = json.loads(sm.get_secret_value(SecretId=os.environ["SECRET_NAME"])["SecretString"])

FOOTER = ("-- This doc. is generated and managed by Sachin Gate "
          "for more queries/ Questions please connect with him.")


def verify(headers, body):
    """Check the Slack request signature and reject old timestamps."""
    ts = headers.get("x-slack-request-timestamp", "0")
    if abs(time.time() - int(ts)) > 300:
        return False
    base = f"v0:{ts}:{body}".encode()
    sig = "v0=" + hmac.new(SECRETS["signing_secret"].encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, headers.get("x-slack-signature", ""))


def post(channel, thread_ts, text):
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": channel, "thread_ts": thread_ts, "text": text}).encode(),
        headers={
            "Authorization": f"Bearer {SECRETS['bot_token']}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    urllib.request.urlopen(req, timeout=10)


def work(ev):
    """Runs asynchronously: ask the Knowledge Base and reply in the thread."""
    question = re.sub(r"<@[A-Z0-9]+>", "", ev["text"]).strip()

    kb_config = {"knowledgeBaseId": KB_ID, "modelArn": MODEL_ARN}
    if GUARDRAIL_ID:
        kb_config["generationConfiguration"] = {
            "guardrailConfiguration": {
                "guardrailId": GUARDRAIL_ID,
                "guardrailVersion": GUARDRAIL_VERSION,
            }
        }

    resp = bedrock.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": kb_config,
        },
    )
    answer = resp["output"]["text"]
    if FOOTER not in answer:  # guaranteed footer, never added twice
        answer += "\n\n" + FOOTER
    post(ev["channel"], ev.get("thread_ts") or ev["ts"], answer)


def handler(event, context):
    # Async worker path (the function invokes itself)
    if event.get("source") == "worker":
        return work(event["event"])

    headers = {k.lower(): v for k, v in event["headers"].items()}
    body = event["body"]
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()

    if not verify(headers, body):
        return {"statusCode": 401}
    if headers.get("x-slack-retry-num"):  # ignore Slack retries
        return {"statusCode": 200}

    payload = json.loads(body)
    if payload.get("type") == "url_verification":
        return {"statusCode": 200, "body": payload["challenge"]}

    ev = payload.get("event", {})
    if ev.get("type") == "app_mention" and not ev.get("bot_id"):
        lam.invoke(
            FunctionName=context.function_name,
            InvocationType="Event",
            Payload=json.dumps({"source": "worker", "event": ev}),
        )
    return {"statusCode": 200}
