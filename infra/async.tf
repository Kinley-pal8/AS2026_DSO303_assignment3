# Queues decouple slow/bursty work (marking, file checks, e-mail) from the request path.
# Every queue has a dead-letter queue; failed messages are retried 5 times then parked for inspection.

locals {
  queues = {
    marking       = { consumer = "marker", max_concurrency = 20 } # caps DB load during peak
    uploads       = { consumer = "uploads", max_concurrency = 10 }
    notifications = { consumer = "notifier", max_concurrency = 5 } # stay within SES send rate
  }
}

resource "aws_sqs_queue" "dlq" {
  for_each                  = local.queues
  name                      = "${local.name}-${each.key}-dlq"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "marking" {
  name                       = "${local.name}-marking"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true
  redrive_policy             = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dlq["marking"].arn, maxReceiveCount = 5 })
}

resource "aws_sqs_queue" "uploads" {
  name                       = "${local.name}-uploads"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true
  redrive_policy             = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dlq["uploads"].arn, maxReceiveCount = 5 })
}

resource "aws_sqs_queue" "notifications" {
  name                       = "${local.name}-notifications"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true
  redrive_policy             = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dlq["notifications"].arn, maxReceiveCount = 5 })
}

locals {
  queue_arns = {
    marking       = aws_sqs_queue.marking.arn
    uploads       = aws_sqs_queue.uploads.arn
    notifications = aws_sqs_queue.notifications.arn
  }
}

# Allow S3 to publish ObjectCreated events for the uploads bucket only.
resource "aws_sqs_queue_policy" "uploads" {
  queue_url = aws_sqs_queue.uploads.url
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.uploads.arn
      Condition = {
        ArnEquals    = { "aws:SourceArn" = local.uploads_bucket_arn }
        StringEquals = { "aws:SourceAccount" = local.account_id }
      }
    }]
  })
}

resource "aws_lambda_event_source_mapping" "workers" {
  for_each                           = local.queues
  event_source_arn                   = local.queue_arns[each.key]
  function_name                      = aws_lambda_function.fn[each.value.consumer].arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 2
  function_response_types            = ["ReportBatchItemFailures"]
  scaling_config {
    maximum_concurrency = each.value.max_concurrency
  }
}

# ---------------------------------------------------------------- sweeper: auto-submit expired attempts
resource "aws_cloudwatch_event_rule" "sweeper" {
  name                = "${local.name}-sweeper"
  description         = "Auto-submit exam attempts whose time has run out"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "sweeper" {
  rule = aws_cloudwatch_event_rule.sweeper.name
  arn  = aws_lambda_function.fn["sweeper"].arn
}

resource "aws_lambda_permission" "sweeper" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn["sweeper"].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sweeper.arn
}

# ---------------------------------------------------------------- SES
# Terraform sends a verification link to this address; click it before e-mails can be sent.
# While the account is in the SES sandbox, recipients must be verified too (see README).
resource "aws_sesv2_email_identity" "sender" {
  count          = var.enable_ses ? 1 : 0
  email_identity = var.ses_sender_email
}
