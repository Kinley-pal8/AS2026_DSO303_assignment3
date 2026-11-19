# Plans both deployment profiles against mocked providers (no AWS credentials needed).
# Run: terraform -chdir=infra test

mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b", "us-east-1c"] }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
  mock_resource "aws_db_instance" {
    defaults = {
      arn                = "arn:aws:rds:us-east-1:123456789012:db:uniexam-prod-db"
      master_user_secret = [{ secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds-db", kms_key_id = "k", secret_status = "active" }]
    }
  }
  mock_resource "aws_db_proxy" {
    defaults = { arn = "arn:aws:rds:us-east-1:123456789012:db-proxy:prx-0123456789abcdef" }
  }
  mock_resource "aws_kms_key" {
    defaults = { arn = "arn:aws:kms:us-east-1:123456789012:key/abc" }
  }
  mock_resource "aws_dynamodb_table" {
    defaults = { arn = "arn:aws:dynamodb:us-east-1:123456789012:table/attempts" }
  }
  mock_resource "aws_sqs_queue" {
    defaults = { arn = "arn:aws:sqs:us-east-1:123456789012:q" }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::bucket" }
  }
  mock_resource "aws_apigatewayv2_api" {
    defaults = { api_endpoint = "https://abc.execute-api.us-east-1.amazonaws.com", execution_arn = "arn:aws:execute-api:us-east-1:123456789012:abc" }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:us-east-1:123456789012:log-group:x" }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/r" }
  }
  mock_resource "aws_cloudfront_distribution" {
    defaults = { arn = "arn:aws:cloudfront::123456789012:distribution/E1", domain_name = "d111.cloudfront.net" }
  }
  mock_resource "aws_wafv2_web_acl" {
    defaults = { arn = "arn:aws:wafv2:us-east-1:123456789012:global/webacl/x/1" }
  }
  mock_resource "aws_lambda_function" {
    defaults = { arn = "arn:aws:lambda:us-east-1:123456789012:function:f", version = "1" }
  }
  mock_resource "aws_cognito_user_pool" {
    defaults = { arn = "arn:aws:cognito-idp:us-east-1:123456789012:userpool/x" }
  }
  mock_resource "aws_sns_topic" {
    defaults = { arn = "arn:aws:sns:us-east-1:123456789012:alarms" }
  }
  mock_resource "aws_cloudwatch_event_rule" {
    defaults = { arn = "arn:aws:events:us-east-1:123456789012:rule/s" }
  }
}

mock_provider "aws" {
  alias = "us_east_1"
}

mock_provider "archive" {}

run "production_profile" {
  command = plan

  assert {
    condition     = length(aws_iam_role.fn) == 5 && length(aws_db_proxy.main) == 1 && length(aws_wafv2_web_acl.main) == 1
    error_message = "production profile must create per-function roles, RDS Proxy and WAF"
  }
  assert {
    condition     = aws_db_instance.main.multi_az && length(aws_nat_gateway.main) == 2
    error_message = "production profile must be Multi-AZ with a NAT per AZ"
  }
}

run "learner_lab_profile" {
  command = plan

  variables {
    region                  = "us-east-1"
    existing_role_name      = "LabRole"
    use_customer_kms_key    = false
    enable_rds_proxy        = false
    enable_waf              = false
    enable_backup           = false
    enable_flow_logs        = false
    enable_ses              = false
    nat_gateway_per_az      = false
    enable_cloudfront       = false
    create_buckets_with_cli = true
  }

  assert {
    condition     = length(aws_iam_role.fn) == 0 && length(aws_iam_role.rds_proxy) == 0 && length(aws_iam_role.backup) == 0 && length(aws_iam_role.flow_logs) == 0
    error_message = "Learner Lab profile must not create any IAM roles"
  }
  assert {
    condition     = alltrue([for f in aws_lambda_function.fn : f.role == "arn:aws:iam::123456789012:role/LabRole"])
    error_message = "every Lambda must run as LabRole"
  }
  assert {
    condition     = aws_db_instance.main.multi_az && length(aws_vpc_security_group_ingress_rule.db_from_lambda) == 1
    error_message = "database must stay Multi-AZ and accept Lambda directly"
  }
  assert {
    condition     = length(aws_cloudfront_distribution.main) == 0 && contains(keys(aws_lambda_function.fn), "web") && length(aws_apigatewayv2_route.web) == 2
    error_message = "without CloudFront, API Gateway must serve the SPA through the web Lambda"
  }
  assert {
    condition     = aws_lambda_function.fn["api"].environment[0].variables["DB_AUTH"] == "secret" && aws_lambda_function.fn["notifier"].environment[0].variables["EMAIL_MODE"] == "log"
    error_message = "Lambdas must use secret DB auth and logged e-mail"
  }
}
