output "app_url" {
  description = "Open this in a browser."
  value       = local.app_url
}

output "cloudfront_distribution_id" {
  value = one(aws_cloudfront_distribution.main[*].id)
}

output "api_endpoint_direct" {
  description = "Raw API Gateway URL (requests without the CloudFront origin header are rejected with 403)."
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "user_pool_client_id" {
  value = aws_cognito_user_pool_client.web.id
}

output "cognito_domain" {
  value = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.region}.amazoncognito.com"
}

output "uploads_bucket" {
  value = local.uploads_bucket
}

output "attempts_table" {
  value = aws_dynamodb_table.attempts.name
}

output "db_instance_id" {
  value = aws_db_instance.main.identifier
}

output "db_endpoint" {
  description = "Endpoint the Lambdas use (RDS Proxy if enabled, otherwise the RDS instance)."
  value       = local.db_host
}

output "deployment_profile" {
  value = {
    existing_role      = var.existing_role_name
    customer_kms_key   = var.use_customer_kms_key
    rds_proxy          = var.enable_rds_proxy
    waf                = var.enable_waf
    backup             = var.enable_backup
    ses                = var.enable_ses
    db_multi_az        = var.db_multi_az
    nat_gateway_per_az = var.nat_gateway_per_az
  }
}

output "queues" {
  value = { for k, v in local.queue_arns : k => v }
}

output "dashboard_url" {
  value = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}
