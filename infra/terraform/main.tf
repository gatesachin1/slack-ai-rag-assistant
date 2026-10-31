data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

data "aws_secretsmanager_secret" "slack" {
  name = var.slack_secret_name
}

locals {
  account_id    = data.aws_caller_identity.current.account_id
  partition     = data.aws_partition.current.partition
  ingress_name  = "${var.name}-ingress"
  worker_name   = "${var.name}-worker"
  metrics_ns    = "SlackRag"
  kb_arn        = "arn:${local.partition}:bedrock:${var.aws_region}:${local.account_id}:knowledge-base/${var.kb_id}"
  guardrail_arn = "arn:${local.partition}:bedrock:${var.aws_region}:${local.account_id}:guardrail/${var.guardrail_id}"

  common_env = {
    SECRET_NAME                  = var.slack_secret_name
    ALLOWED_TEAM_IDS             = join(",", var.allowed_team_ids)
    ALLOWED_CHANNEL_IDS          = join(",", var.allowed_channel_ids)
    POWERTOOLS_SERVICE_NAME      = var.name
    POWERTOOLS_METRICS_NAMESPACE = local.metrics_ns
    POWERTOOLS_LOG_LEVEL         = var.log_level
  }
}

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = var.build_dir
  output_path = "${path.module}/.build/lambda.zip"
}

# --- Queue + idempotency store ------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-dlq"
  message_retention_seconds = 14 * 24 * 3600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "mentions" {
  name                       = "${var.name}-mentions"
  visibility_timeout_seconds = 6 * aws_lambda_function.worker.timeout
  message_retention_seconds  = 3600 # an answer older than an hour is no longer useful
  sqs_managed_sse_enabled    = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}

resource "aws_dynamodb_table" "idempotency" {
  name         = "${var.name}-idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "expiration"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }
}

# --- Logs -----------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "ingress" {
  name              = "/aws/lambda/${local.ingress_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${local.worker_name}"
  retention_in_days = var.log_retention_days
}

# --- Ingress Lambda (public Function URL, Slack signature-verified) ---------------

resource "aws_lambda_function" "ingress" {
  function_name                  = local.ingress_name
  role                           = aws_iam_role.ingress.arn
  handler                        = "slack_rag.ingress.handler"
  runtime                        = "python3.12"
  architectures                  = ["arm64"]
  memory_size                    = 512 # more memory = more CPU = faster cold start inside Slack's 3s budget
  timeout                        = 5
  reserved_concurrent_executions = var.ingress_reserved_concurrency
  filename                       = data.archive_file.lambda.output_path
  source_code_hash               = data.archive_file.lambda.output_base64sha256

  environment {
    variables = merge(local.common_env, {
      QUEUE_URL = aws_sqs_queue.mentions.url
    })
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [aws_cloudwatch_log_group.ingress]
}

resource "aws_lambda_function_url" "ingress" {
  function_name      = aws_lambda_function.ingress.function_name
  authorization_type = "NONE" # Slack cannot SigV4-sign; requests are authenticated by the Slack signature instead
}

# Public Function URLs need both permissions; InvokeFunction is restricted to calls via the URL.
resource "aws_lambda_permission" "url_invoke_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.ingress.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "url_invoke_function" {
  statement_id             = "AllowInvokeViaFunctionUrl"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.ingress.function_name
  principal                = "*"
  invoked_via_function_url = true
}

# --- Worker Lambda (SQS consumer) -------------------------------------------------

resource "aws_lambda_function" "worker" {
  function_name    = local.worker_name
  role             = aws_iam_role.worker.arn
  handler          = "slack_rag.worker.handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]
  memory_size      = 512
  timeout          = 60
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256

  environment {
    variables = merge(local.common_env, {
      KB_ID                = var.kb_id
      MODEL_ARN            = var.model_arn
      GUARDRAIL_ID         = var.guardrail_id
      GUARDRAIL_VERSION    = var.guardrail_version
      KB_NUMBER_OF_RESULTS = tostring(var.kb_number_of_results)
      IDEMPOTENCY_TABLE    = aws_dynamodb_table.idempotency.name
      MAX_RECEIVE_COUNT    = tostring(var.max_receive_count)
      ANSWER_FOOTER        = var.answer_footer
    })
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [aws_cloudwatch_log_group.worker]
}

resource "aws_lambda_event_source_mapping" "worker" {
  event_source_arn        = aws_sqs_queue.mentions.arn
  function_name           = aws_lambda_function.worker.arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = var.worker_max_concurrency
  }
}
