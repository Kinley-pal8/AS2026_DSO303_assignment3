data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name       = "${var.project}-${var.environment}"
  account_id = data.aws_caller_identity.current.account_id
  azs        = slice(data.aws_availability_zones.available.names, 0, 2)
  app_url    = !var.enable_cloudfront ? aws_apigatewayv2_api.main.api_endpoint : var.domain_name != "" ? "https://${var.domain_name}" : "https://${one(aws_cloudfront_distribution.main[*].domain_name)}"

  # Feature switches (see variables.tf / learner-lab.tfvars)
  use_existing_role = var.existing_role_name != ""
  existing_role_arn = "arn:aws:iam::${local.account_id}:role/${var.existing_role_name}"
  kms_key_arn       = var.use_customer_kms_key ? aws_kms_key.main[0].arn : null

  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# One customer-managed key for data at rest (RDS, DynamoDB, S3 uploads, secrets, backups).
resource "aws_kms_key" "main" {
  count                   = var.use_customer_kms_key ? 1 : 0
  description             = "${local.name} data encryption key"
  enable_key_rotation     = true
  deletion_window_in_days = 7
}

resource "aws_kms_alias" "main" {
  count         = var.use_customer_kms_key ? 1 : 0
  name          = "alias/${local.name}"
  target_key_id = aws_kms_key.main[0].key_id
}

# Shared secret CloudFront adds to API requests; the API rejects calls that bypass CloudFront/WAF.
resource "random_password" "origin_verify" {
  length  = 40
  special = false
}
