data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda" # produced by scripts/build.sh
  output_path = "${path.module}/../build/lambda.zip"
}

locals {
  functions = merge({
    api      = { handler = "api.handler", timeout = 15, memory = 512, vpc = true }
    marker   = { handler = "marker.handler", timeout = 30, memory = 256, vpc = true }
    uploads  = { handler = "uploads.handler", timeout = 30, memory = 256, vpc = true }
    notifier = { handler = "notifier.handler", timeout = 30, memory = 128, vpc = false }
    sweeper  = { handler = "sweeper.handler", timeout = 60, memory = 128, vpc = false }
    }, var.enable_cloudfront ? {} : {
    web = { handler = "web.handler", timeout = 5, memory = 128, vpc = false } # serves the SPA without CloudFront
  })

  lambda_env = {
    TABLE_NAME        = aws_dynamodb_table.attempts.name
    MARKING_QUEUE_URL = aws_sqs_queue.marking.url
    NOTIFY_QUEUE_URL  = aws_sqs_queue.notifications.url
    UPLOAD_BUCKET     = local.uploads_bucket
    DB_HOST           = local.db_host
    DB_AUTH           = var.enable_rds_proxy ? "iam" : "secret"
    DB_SECRET_ARN     = local.db_secret_arn
    EMAIL_MODE        = var.enable_ses ? "ses" : "log"
    DB_NAME           = aws_db_instance.main.db_name
    DB_USER           = aws_db_instance.main.username
    USER_POOL_ID      = aws_cognito_user_pool.main.id
    SENDER_EMAIL      = var.ses_sender_email
    APP_URL           = local.app_url
    ORIGIN_SECRET     = var.enable_cloudfront ? random_password.origin_verify.result : "" # no CloudFront = no origin header to check
    FRONTEND_CONFIG   = local.frontend_config
    GRACE_SECONDS     = "60"
  }

  kms_data_actions = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
  db_connect_arn   = "arn:aws:rds-db:${var.region}:${local.account_id}:dbuser:${local.db_proxy_resource_id}/${aws_db_instance.main.username}"
  kms_resource     = coalesce(local.kms_key_arn, "*")
  # Proxy: IAM token for the proxy. No proxy: read the RDS-managed password from Secrets Manager.
  db_access = var.enable_rds_proxy ? {
    actions   = ["rds-db:connect"]
    resources = [local.db_connect_arn]
    } : {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [local.db_secret_arn]
  }
  sqs_consume = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"]
}

# ---------------------------------------------------------------- least-privilege policy per function
data "aws_iam_policy_document" "api" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:BatchGetItem"]
    resources = [aws_dynamodb_table.attempts.arn]
  }
  statement {
    actions   = ["sqs:SendMessage", "sqs:SendMessageBatch"]
    resources = [aws_sqs_queue.marking.arn, aws_sqs_queue.notifications.arn]
  }
  statement {
    sid       = "PresignUploadsAndDownloads"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${local.uploads_bucket_arn}/submissions/*"]
  }
  statement {
    actions   = local.kms_data_actions
    resources = [local.kms_resource]
  }
  statement {
    actions   = local.db_access.actions
    resources = local.db_access.resources
  }
  statement {
    actions   = ["cognito-idp:AdminCreateUser", "cognito-idp:AdminAddUserToGroup", "cognito-idp:ListUsersInGroup"]
    resources = [aws_cognito_user_pool.main.arn]
  }
}

data "aws_iam_policy_document" "marker" {
  statement {
    actions   = local.sqs_consume
    resources = [aws_sqs_queue.marking.arn]
  }
  statement {
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.attempts.arn]
  }
  statement {
    actions   = local.kms_data_actions
    resources = [local.kms_resource]
  }
  statement {
    actions   = local.db_access.actions
    resources = local.db_access.resources
  }
}

data "aws_iam_policy_document" "uploads" {
  statement {
    actions   = local.sqs_consume
    resources = [aws_sqs_queue.uploads.arn]
  }
  statement {
    actions   = ["sqs:SendMessage", "sqs:SendMessageBatch"]
    resources = [aws_sqs_queue.notifications.arn]
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObjectTagging"]
    resources = ["${local.uploads_bucket_arn}/submissions/*"]
  }
  statement {
    actions   = local.kms_data_actions
    resources = [local.kms_resource]
  }
  statement {
    actions   = local.db_access.actions
    resources = local.db_access.resources
  }
}

data "aws_iam_policy_document" "notifier" {
  statement {
    actions   = local.sqs_consume
    resources = [aws_sqs_queue.notifications.arn]
  }
  statement {
    actions   = ["ses:SendEmail"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "ses:FromAddress"
      values   = [var.ses_sender_email]
    }
  }
}

data "aws_iam_policy_document" "sweeper" {
  statement {
    actions   = ["dynamodb:Query", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.attempts.arn, "${aws_dynamodb_table.attempts.arn}/index/open-by-deadline"]
  }
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.marking.arn]
  }
  statement {
    actions   = local.kms_data_actions
    resources = [local.kms_resource]
  }
}

locals {
  function_policies = {
    api      = data.aws_iam_policy_document.api.json
    marker   = data.aws_iam_policy_document.marker.json
    uploads  = data.aws_iam_policy_document.uploads.json
    notifier = data.aws_iam_policy_document.notifier.json
    sweeper  = data.aws_iam_policy_document.sweeper.json
    web      = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "xray:PutTraceSegments", Resource = "*" }] })
  }
}

# Least-privilege role per function, unless an existing role (Learner Lab "LabRole") is supplied.
locals {
  own_roles = local.use_existing_role ? {} : local.functions
}

resource "aws_iam_role" "fn" {
  for_each = local.own_roles
  name     = "${local.name}-${each.key}-lambda"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "fn" {
  for_each = local.own_roles
  role     = aws_iam_role.fn[each.key].id
  policy   = local.function_policies[each.key]
}

resource "aws_iam_role_policy_attachment" "basic" {
  for_each   = local.own_roles
  role       = aws_iam_role.fn[each.key].name
  policy_arn = each.value.vpc ? "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole" : "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "xray" {
  for_each   = local.own_roles
  role       = aws_iam_role.fn[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_cloudwatch_log_group" "fn" {
  for_each          = local.functions
  name              = "/aws/lambda/${local.name}-${each.key}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "fn" {
  for_each         = local.functions
  function_name    = "${local.name}-${each.key}"
  role             = local.use_existing_role ? local.existing_role_arn : aws_iam_role.fn[each.key].arn
  handler          = each.value.handler
  runtime          = "python3.13"
  architectures    = ["arm64"]
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = each.value.timeout
  memory_size      = each.value.memory
  publish          = each.key == "api" # versions needed for the alias / provisioned concurrency

  environment {
    variables = local.lambda_env
  }

  tracing_config {
    mode = "Active"
  }

  # A3 cost optimisation: JSON logs, and platform START/END/REPORT lines (INFO) dropped -
  # about 300 bytes per invocation, i.e. ~40% of log volume at exam peak.
  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = var.lambda_system_log_level
  }

  dynamic "vpc_config" {
    for_each = each.value.vpc ? [1] : []
    content {
      subnet_ids         = aws_subnet.app[*].id # ENIs in both AZs
      security_group_ids = [aws_security_group.lambda.id]
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.fn,
    aws_iam_role_policy.fn,
    aws_iam_role_policy_attachment.basic,
  ]
}

resource "aws_lambda_alias" "api_live" {
  name             = "live"
  function_name    = aws_lambda_function.fn["api"].function_name
  function_version = aws_lambda_function.fn["api"].version
}

resource "aws_lambda_provisioned_concurrency_config" "api" {
  count                             = var.api_provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_alias.api_live.function_name
  qualifier                         = aws_lambda_alias.api_live.name
  provisioned_concurrent_executions = var.api_provisioned_concurrency
}
