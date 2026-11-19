resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name}-api"
  protocol_type = "HTTP"
  description   = "Exam platform API (reached through CloudFront at /api/*)"
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  name             = "cognito"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  jwt_configuration {
    audience = [aws_cognito_user_pool_client.web.id]
    issuer   = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  }
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_alias.api_live.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 15000
}

resource "aws_apigatewayv2_route" "api" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "ANY /api/{proxy+}"
  target             = "integrations/${aws_apigatewayv2_integration.api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /api/health"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${local.name}"
  retention_in_days = var.log_retention_days
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit   = 2000
    throttling_rate_limit    = 1000
    detailed_metrics_enabled = true
  }

  # A3 cost optimisation: per-request access logs are off in production (CloudWatch metrics
  # cover latency and errors); switch on for load tests and incident investigation.
  dynamic "access_log_settings" {
    for_each = var.enable_api_access_logs ? [1] : []
    content {
      destination_arn = aws_cloudwatch_log_group.api_access.arn
      format = jsonencode({
        requestId = "$context.requestId"
        ip        = "$context.identity.sourceIp"
        method    = "$context.httpMethod"
        path      = "$context.path"
        status    = "$context.status"
        latencyMs = "$context.responseLatency"
        user      = "$context.authorizer.claims.sub"
        error     = "$context.integrationErrorMessage"
      })
    }
  }
}

resource "aws_lambda_permission" "api" {
  statement_id  = "AllowApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn["api"].function_name
  qualifier     = aws_lambda_alias.api_live.name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ---------------------------------------------------------------- SPA without CloudFront (Learner Lab)
resource "aws_apigatewayv2_integration" "web" {
  count                  = var.enable_cloudfront ? 0 : 1
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.fn["web"].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "web" {
  for_each  = var.enable_cloudfront ? toset([]) : toset(["GET /", "GET /{proxy+}"])
  api_id    = aws_apigatewayv2_api.main.id
  route_key = each.key
  target    = "integrations/${aws_apigatewayv2_integration.web[0].id}"
}

resource "aws_lambda_permission" "web" {
  count         = var.enable_cloudfront ? 0 : 1
  statement_id  = "AllowApiGatewayWeb"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn["web"].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
