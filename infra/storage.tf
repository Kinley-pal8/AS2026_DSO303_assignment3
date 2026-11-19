# ---------------------------------------------------------------- assignment uploads
resource "aws_s3_bucket" "uploads" {
  count         = var.create_buckets_with_cli ? 0 : 1
  bucket        = "${local.name}-uploads-${local.account_id}"
  force_destroy = !var.protect_data
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = local.uploads_bucket
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "uploads" {
  bucket = local.uploads_bucket
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = local.uploads_bucket
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = local.uploads_bucket
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.use_customer_kms_key ? "aws:kms" : "AES256"
      kms_master_key_id = local.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

# Records kept 5 years, getting cheaper as they age.
resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = local.uploads_bucket

  rule {
    id     = "submissions-5-year-retention"
    status = "Enabled"
    filter {
      prefix = "submissions/"
    }
    transition {
      days          = 30
      storage_class = "STANDARD_IA" # marking period over, occasional access
    }
    transition {
      days          = 90
      storage_class = "GLACIER_IR" # A3 optimisation: was 180 d; files are rarely opened after the first month
    }
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE" # compliance archive
    }
    expiration {
      days = 1825 # 5 years
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = local.uploads_bucket
  cors_rule {
    allowed_methods = ["POST", "GET"]
    allowed_origins = [local.app_url]
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_policy" "uploads" {
  bucket = local.uploads_bucket
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [local.uploads_bucket_arn, "${local.uploads_bucket_arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.uploads]
}

resource "aws_s3_bucket_notification" "uploads" {
  bucket = local.uploads_bucket
  queue {
    queue_arn     = aws_sqs_queue.uploads.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "submissions/"
  }
  depends_on = [aws_sqs_queue_policy.uploads]
}

# ---------------------------------------------------------------- frontend (static SPA)
resource "aws_s3_bucket" "frontend" {
  count         = var.enable_cloudfront && !var.create_buckets_with_cli ? 1 : 0
  bucket        = "${local.name}-web-${local.account_id}"
  force_destroy = true # rebuilt from git on every deploy
}

# ---------------------------------------------------------------- Learner Lab bucket workaround
# The AWS Academy Learner Lab service control policy denies s3:GetBucketObjectLockConfiguration,
# which the aws_s3_bucket resource always reads, so it can never apply there. With
# create_buckets_with_cli = true the two buckets are created/deleted by the AWS CLI from Terraform
# instead; every other bucket setting (policy, encryption, lifecycle, CORS, events) stays in Terraform.
resource "terraform_data" "bucket" {
  for_each = var.create_buckets_with_cli ? toset(compact(["${local.name}-uploads-${local.account_id}", var.enable_cloudfront ? "${local.name}-web-${local.account_id}" : ""])) : toset([])
  input    = each.key

  provisioner "local-exec" {
    command = "aws s3api head-bucket --bucket ${self.input} 2>/dev/null || aws s3api create-bucket --bucket ${self.input} --region ${var.region} ${var.region == "us-east-1" ? "" : "--create-bucket-configuration LocationConstraint=${var.region}"}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "python3 -c \"import boto3,sys; b=boto3.resource('s3').Bucket(sys.argv[1]); b.object_versions.delete(); b.delete()\" ${self.input}"
  }
}

locals {
  uploads_bucket     = var.create_buckets_with_cli ? terraform_data.bucket["${local.name}-uploads-${local.account_id}"].output : aws_s3_bucket.uploads[0].id
  uploads_bucket_arn = "arn:aws:s3:::${local.uploads_bucket}"
  web_bucket         = !var.enable_cloudfront ? "" : var.create_buckets_with_cli ? try(terraform_data.bucket["${local.name}-web-${local.account_id}"].output, "") : try(aws_s3_bucket.frontend[0].id, "")
  web_bucket_arn     = "arn:aws:s3:::${local.web_bucket}"
  web_bucket_domain  = "${local.web_bucket}.s3.${var.region}.amazonaws.com"
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  count                   = var.enable_cloudfront ? 1 : 0
  bucket                  = local.web_bucket
  block_public_acls       = true
  block_public_policy     = !var.web_origin_public
  ignore_public_acls      = true
  restrict_public_buckets = !var.web_origin_public
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  count  = var.enable_cloudfront && var.web_origin_public ? 1 : 0
  bucket = local.web_bucket
  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = local.web_bucket
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = local.web_bucket
  policy = var.web_origin_public ? jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadStaticSite" # Learner Lab only: static HTML/JS/CSS, no data
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${local.web_bucket_arn}/*"
    }]
    }) : jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCloudFrontOAC"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${local.web_bucket_arn}/*"
      Condition = { StringEquals = { "AWS:SourceArn" = one(aws_cloudfront_distribution.main[*].arn) } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

locals {
  frontend_dir   = "${path.module}/../frontend"
  frontend_files = setsubtract(fileset(local.frontend_dir, "**"), ["config.js"])
  mime_types = {
    html = "text/html; charset=utf-8"
    js   = "application/javascript"
    css  = "text/css"
    svg  = "image/svg+xml"
    png  = "image/png"
    ico  = "image/x-icon"
    json = "application/json"
  }
}

resource "aws_s3_object" "frontend" {
  for_each      = var.enable_cloudfront ? local.frontend_files : toset([])
  bucket        = local.web_bucket
  key           = each.value
  source        = "${local.frontend_dir}/${each.value}"
  etag          = filemd5("${local.frontend_dir}/${each.value}")
  content_type  = lookup(local.mime_types, reverse(split(".", each.value))[0], "application/octet-stream")
  cache_control = endswith(each.value, ".html") ? "no-cache" : "public, max-age=300"
}

resource "aws_s3_object" "frontend_config" {
  count         = var.enable_cloudfront ? 1 : 0
  bucket        = local.web_bucket
  key           = "config.js"
  content_type  = "application/javascript"
  cache_control = "no-cache"
  content       = "window.APP_CONFIG = ${local.frontend_config};\n"
}

locals {
  frontend_config = jsonencode({
    apiBase       = "/api"
    cognitoDomain = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.region}.amazoncognito.com"
    clientId      = aws_cognito_user_pool_client.web.id
    region        = var.region
  })
}
