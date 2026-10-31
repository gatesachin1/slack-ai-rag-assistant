data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# --- Ingress: read the signing secret, enqueue, write its own logs ----------------

resource "aws_iam_role" "ingress" {
  name               = local.ingress_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "ingress" {
  statement {
    sid       = "ReadSlackSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [data.aws_secretsmanager_secret.slack.arn]
  }
  statement {
    sid       = "Enqueue"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.mentions.arn]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.ingress.arn}:*"]
  }
}

resource "aws_iam_role_policy" "ingress" {
  role   = aws_iam_role.ingress.id
  policy = data.aws_iam_policy_document.ingress.json
}

resource "aws_iam_role_policy_attachment" "ingress_xray" {
  role       = aws_iam_role.ingress.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# --- Worker: Bedrock, idempotency table, queue, secret, logs ----------------------

resource "aws_iam_role" "worker" {
  name               = local.worker_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "worker" {
  statement {
    sid = "RetrieveAndGenerate"
    # RetrieveAndGenerate does not support resource-level permissions; access is
    # still scoped by the Retrieve + InvokeModel statements below.
    actions   = ["bedrock:RetrieveAndGenerate"]
    resources = ["*"]
  }
  statement {
    sid       = "KnowledgeBase"
    actions   = ["bedrock:Retrieve"]
    resources = [local.kb_arn]
  }
  statement {
    sid       = "Model"
    actions   = ["bedrock:InvokeModel", "bedrock:GetInferenceProfile"]
    resources = var.model_invoke_arns
  }
  dynamic "statement" {
    for_each = var.guardrail_id == "" ? [] : [1]
    content {
      sid       = "Guardrail"
      actions   = ["bedrock:ApplyGuardrail"]
      resources = [local.guardrail_arn]
    }
  }
  statement {
    sid       = "ReadSlackSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [data.aws_secretsmanager_secret.slack.arn]
  }
  statement {
    sid = "Idempotency"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
    ]
    resources = [aws_dynamodb_table.idempotency.arn]
  }
  statement {
    sid       = "ConsumeQueue"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.mentions.arn]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.worker.arn}:*"]
  }
}

resource "aws_iam_role_policy" "worker" {
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}

resource "aws_iam_role_policy_attachment" "worker_xray" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/AWSXRayDaemonWriteAccess"
}
