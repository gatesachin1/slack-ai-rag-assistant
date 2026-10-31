output "slack_request_url" {
  description = "Paste into Slack app > Event Subscriptions > Request URL."
  value       = aws_lambda_function_url.ingress.function_url
}

output "mentions_queue_url" {
  value = aws_sqs_queue.mentions.url
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "alarm_topic_arn" {
  value = aws_sns_topic.alarms.arn
}
