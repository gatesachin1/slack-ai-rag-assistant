resource "aws_sns_topic" "alarms" {
  name              = "${var.name}-alarms"
  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

locals {
  alarms = {
    dlq-not-empty = {
      description = "Mentions failed every retry and were not answered. Inspect and redrive the DLQ."
      namespace   = "AWS/SQS"
      metric      = "ApproximateNumberOfMessagesVisible"
      statistic   = "Maximum"
      threshold   = 0
      dimensions  = { QueueName = aws_sqs_queue.dlq.name }
    }
    queue-backlog-age = {
      description = "Mentions are waiting more than 2 minutes for an answer (Bedrock throttling or worker failing)."
      namespace   = "AWS/SQS"
      metric      = "ApproximateAgeOfOldestMessage"
      statistic   = "Maximum"
      threshold   = 120
      dimensions  = { QueueName = aws_sqs_queue.mentions.name }
    }
    ingress-errors = {
      description = "Ingress Lambda is erroring; Slack events are not being acknowledged."
      namespace   = "AWS/Lambda"
      metric      = "Errors"
      statistic   = "Sum"
      threshold   = 0
      dimensions  = { FunctionName = aws_lambda_function.ingress.function_name }
    }
    ingress-throttles = {
      description = "Ingress Lambda hit its reserved concurrency; Slack events may be dropped."
      namespace   = "AWS/Lambda"
      metric      = "Throttles"
      statistic   = "Sum"
      threshold   = 0
      dimensions  = { FunctionName = aws_lambda_function.ingress.function_name }
    }
    worker-errors = {
      description = "Worker Lambda invocations are failing (crash, timeout, bad config)."
      namespace   = "AWS/Lambda"
      metric      = "Errors"
      statistic   = "Sum"
      threshold   = 0
      dimensions  = { FunctionName = aws_lambda_function.worker.function_name }
    }
    answer-failures = {
      description = "Users received an error reply instead of an answer."
      namespace   = local.metrics_ns
      metric      = "AnswerFailed"
      statistic   = "Sum"
      threshold   = 0
      dimensions  = { service = var.name }
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "this" {
  for_each = local.alarms

  alarm_name          = "${var.name}-${each.key}"
  alarm_description   = each.value.description
  namespace           = each.value.namespace
  metric_name         = each.value.metric
  statistic           = each.value.statistic
  dimensions          = each.value.dimensions
  period              = 300
  evaluation_periods  = 1
  threshold           = each.value.threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}
