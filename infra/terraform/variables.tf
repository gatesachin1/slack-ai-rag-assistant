variable "name" {
  description = "Prefix for all resource names."
  type        = string
  default     = "slack-rag"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "tags" {
  type    = map(string)
  default = {}
}

# --- Bedrock -----------------------------------------------------------------

variable "kb_id" {
  description = "Bedrock Knowledge Base ID."
  type        = string
}

variable "model_arn" {
  description = "Model or inference profile ARN used for generation (passed to RetrieveAndGenerate)."
  type        = string
}

variable "model_invoke_arns" {
  description = <<-EOT
    ARNs the worker may call bedrock:InvokeModel on. For a cross-region inference profile,
    include the profile ARN and the foundation-model ARN in every region it routes to
    (e.g. "arn:aws:bedrock:*::foundation-model/amazon.nova-2-lite-v1:0").
  EOT
  type        = list(string)
}

variable "guardrail_id" {
  type    = string
  default = ""
}

variable "guardrail_version" {
  description = "Pin a numbered version in production; DRAFT changes whenever someone edits the guardrail."
  type        = string
  default     = "DRAFT"
}

variable "kb_number_of_results" {
  type    = number
  default = 5
}

# --- Slack ---------------------------------------------------------------------

variable "slack_secret_name" {
  description = "Secrets Manager secret holding {\"bot_token\", \"signing_secret\"}. Created out-of-band so tokens never land in Terraform state."
  type        = string
  default     = "slack-rag-bot"
}

variable "allowed_team_ids" {
  description = "Slack workspace IDs allowed to use the bot. Empty allows any workspace that has the app installed."
  type        = list(string)
  default     = []
}

variable "allowed_channel_ids" {
  description = "Channels the bot answers in. Empty allows all channels it is invited to."
  type        = list(string)
  default     = []
}

variable "answer_footer" {
  description = "Text appended to every answer. Empty disables it."
  type        = string
  default     = "This doc. is generated and managed by Sachin Gate for more queries/ Questions please connect with him."
}

# --- Runtime -------------------------------------------------------------------

variable "build_dir" {
  description = "Directory produced by `make build` (source + bundled dependencies)."
  type        = string
  default     = "../../build/lambda"
}

variable "ingress_reserved_concurrency" {
  description = "Caps ingress concurrency to bound the cost of floods of unsigned requests. -1 = unreserved (needed on accounts with the default 10-concurrency quota)."
  type        = number
  default     = 10
}

variable "worker_max_concurrency" {
  description = "Max concurrent worker invocations; keeps Bedrock calls under your account quota."
  type        = number
  default     = 5
}

variable "max_receive_count" {
  description = "Delivery attempts per mention before it goes to the DLQ."
  type        = number
  default     = 3
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "log_level" {
  type    = string
  default = "INFO"
}

variable "alarm_email" {
  description = "Optional email subscribed to the alarm topic."
  type        = string
  default     = ""
}
