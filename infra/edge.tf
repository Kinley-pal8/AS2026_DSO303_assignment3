# ---------------------------------------------------------------- WAF (global, attached to CloudFront)
resource "aws_wafv2_web_acl" "main" {
  count       = var.enable_waf ? 1 : 0
  provider    = aws.us_east_1
  name        = "${local.name}-waf"
  scope       = "CLOUDFRONT"
  description = "Managed protections + per-IP rate limit for the exam platform"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSCommonRules"
    priority = 1
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
        # Tutors post exam papers larger than 8 KB; count instead of block for body size.
        rule_action_override {
          name = "SizeRestrictions_BODY"
          action_to_use {
            count {}
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "common"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSKnownBadInputs"
    priority = 2
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSIpReputation"
    priority = 3
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesAmazonIpReputationList"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "ip-reputation"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "RateLimitPerIp"
    priority = 4
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit                 = var.waf_rate_limit
        aggregate_key_type    = "IP"
        evaluation_window_sec = 300
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name}-waf"
    sampled_requests_enabled   = true
  }
}

# ---------------------------------------------------------------- CloudFront
# AWS-managed policy IDs are fixed and published by AWS, so they are hard-coded instead of looked
# up by name: the lookup needs cloudfront:List*Policies, which AWS Academy Learner Lab denies.
# https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html
locals {
  cf_cache_optimized     = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized
  cf_cache_disabled      = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # Managed-CachingDisabled
  cf_origin_all_but_host = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # Managed-AllViewerExceptHostHeader
  cf_headers_security    = "67f7725c-6f97-4210-82d7-5512b31e9d03" # Managed-SecurityHeadersPolicy
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  count                             = var.enable_cloudfront && !var.web_origin_public ? 1 : 0
  name                              = "${local.name}-frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "main" {
  count               = var.enable_cloudfront ? 1 : 0
  enabled             = true
  comment             = "${local.name} exam platform"
  default_root_object = "index.html"
  http_version        = "http2and3"
  is_ipv6_enabled     = true
  price_class         = var.cloudfront_price_class
  web_acl_id          = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : null
  aliases             = var.domain_name != "" ? [var.domain_name] : []

  # Production: private bucket read through Origin Access Control. Learner Lab (web_origin_public):
  # the lab denies cloudfront:CreateOriginAccessControl, so the static SPA is served from the
  # bucket's public website endpoint instead. Only the web bucket is public; uploads stay private.
  origin {
    origin_id                = "frontend"
    domain_name              = var.web_origin_public ? aws_s3_bucket_website_configuration.frontend[0].website_endpoint : local.web_bucket_domain
    origin_access_control_id = var.web_origin_public ? null : aws_cloudfront_origin_access_control.frontend[0].id

    dynamic "custom_origin_config" {
      for_each = var.web_origin_public ? [1] : []
      content {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "http-only" # S3 website endpoints are HTTP only; viewers still use HTTPS
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  origin {
    origin_id   = "api"
    domain_name = replace(aws_apigatewayv2_api.main.api_endpoint, "https://", "")
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
    custom_header {
      name  = "X-Origin-Verify"
      value = random_password.origin_verify.result
    }
  }

  default_cache_behavior {
    target_origin_id           = "frontend"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = local.cf_cache_optimized
    response_headers_policy_id = local.cf_headers_security
  }

  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = "api"
    viewer_protocol_policy     = "https-only"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = local.cf_cache_disabled
    origin_request_policy_id   = local.cf_origin_all_but_host
    response_headers_policy_id = local.cf_headers_security
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.domain_name == ""
    acm_certificate_arn            = var.domain_name != "" ? aws_acm_certificate_validation.site[0].certificate_arn : null
    ssl_support_method             = var.domain_name != "" ? "sni-only" : null
    minimum_protocol_version       = var.domain_name != "" ? "TLSv1.2_2021" : "TLSv1"
  }
}

# ---------------------------------------------------------------- optional custom domain (Route 53 + ACM)
resource "aws_acm_certificate" "site" {
  count             = var.domain_name != "" ? 1 : 0
  provider          = aws.us_east_1
  domain_name       = var.domain_name
  validation_method = "DNS"
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = var.domain_name != "" ? {
    for o in aws_acm_certificate.site[0].domain_validation_options : o.domain_name => o
  } : {}
  zone_id = var.hosted_zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  records = [each.value.resource_record_value]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "site" {
  count                   = var.domain_name != "" ? 1 : 0
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

resource "aws_route53_record" "site" {
  for_each = var.domain_name != "" ? toset(["A", "AAAA"]) : toset([])
  zone_id  = var.hosted_zone_id
  name     = var.domain_name
  type     = each.value
  alias {
    name                   = one(aws_cloudfront_distribution.main[*].domain_name)
    zone_id                = one(aws_cloudfront_distribution.main[*].hosted_zone_id)
    evaluate_target_health = false
  }
}
