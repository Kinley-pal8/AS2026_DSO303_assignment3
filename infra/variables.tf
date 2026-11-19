variable "project" {
  description = "Short project name used as a prefix for every resource."
  type        = string
  default     = "uniexam"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "region" {
  description = "Primary AWS region. Assignment 3 prices the platform in Singapore."
  type        = string
  default     = "ap-southeast-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR. Subnets are /24s carved from it."
  type        = string
  default     = "10.20.0.0/16"
}

variable "nat_gateway_per_az" {
  description = "One NAT gateway per AZ (true = survives an AZ loss) or a single shared one (cheaper for testing)."
  type        = bool
  default     = true
}

variable "db_instance_class" {
  description = "RDS instance class. A3: db.t4g.medium on a 1-year Reserved Instance; db.m7g.large for exam months if the load test shows CPU-credit exhaustion."
  type        = string
  default     = "db.t4g.medium"
}

variable "db_engine_version" {
  description = "PostgreSQL major version."
  type        = string
  default     = "16"
}

variable "api_memory_mb" {
  description = "API Lambda memory. CPU is allocated in proportion (1,769 MB = 1 vCPU), which shortens cold starts."
  type        = number
  default     = 512
}

variable "api_provisioned_concurrency" {
  description = "Pre-warmed API Lambda environments. Set to ~20 during exam week, 0 otherwise."
  type        = number
  default     = 0
}

variable "waf_rate_limit" {
  description = "Max requests per IP per 5 minutes. Kept high because a whole campus can share one NAT IP."
  type        = number
  default     = 20000
}

variable "ses_sender_email" {
  description = "Verified SES sender address for result / submission e-mails."
  type        = string
  default     = "noreply@example.com"
}

variable "alarm_email" {
  description = "E-mail address subscribed to CloudWatch alarms (empty = no subscription)."
  type        = string
  default     = ""
}

variable "initial_admin_email" {
  description = "If set, creates the first administrator in Cognito (an invite with a temporary password is e-mailed)."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Optional custom domain (e.g. exams.example.edu). Empty = use the CloudFront domain."
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID for domain_name (required if domain_name is set)."
  type        = string
  default     = ""
}

variable "cloudfront_price_class" {
  description = "CloudFront edge coverage. PriceClass_200 includes India and most of Asia."
  type        = string
  default     = "PriceClass_200"
}

variable "protect_data" {
  description = "Production safety: deletion protection on RDS/DynamoDB/Cognito, keep final snapshot, don't force-delete buckets. Set false for coursework so 'terraform destroy' works."
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention. 14 days (was 30) - cost optimisation; long-term records live in RDS/S3/Backup, not logs."
  type        = number
  default     = 14
}

# ---------------------------------------------------------------- feature switches
# Everything defaults to the full production design. learner-lab.tfvars turns off what an
# AWS Academy Learner Lab account cannot create (it forbids creating IAM roles).

variable "existing_role_name" {
  description = "Use this existing IAM role (e.g. \"LabRole\" in Learner Lab) for every service instead of creating least-privilege roles."
  type        = string
  default     = ""
}

variable "use_customer_kms_key" {
  description = "Encrypt data with a customer-managed KMS key (false = AWS-managed keys / SSE-S3; still encrypted at rest)."
  type        = bool
  default     = true
}

variable "enable_rds_proxy" {
  description = "Put RDS Proxy (IAM auth) in front of PostgreSQL. False = Lambdas connect directly using the Secrets Manager password."
  type        = bool
  default     = true
}

variable "enable_waf" {
  description = "Attach AWS WAF to CloudFront."
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Create the AWS Backup vault/plan (5-year monthly backups)."
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "VPC flow logs to CloudWatch."
  type        = bool
  default     = true
}

variable "enable_ses" {
  description = "Send e-mail with SES. False = the notifier writes each e-mail to CloudWatch Logs instead (useful where SES is unavailable)."
  type        = bool
  default     = true
}

variable "db_multi_az" {
  description = "RDS Multi-AZ standby in the second AZ."
  type        = bool
  default     = true
}

variable "enable_load_test_auth" {
  description = "Allow ADMIN_USER_PASSWORD_AUTH on the web client so scripts/load_test.py can sign in test students. Turn off after testing."
  type        = bool
  default     = false
}

variable "lambda_system_log_level" {
  description = "Lambda platform log level. WARN drops the START/END/REPORT lines (cost optimisation); DEBUG or INFO keeps them."
  type        = string
  default     = "WARN"
}

variable "enable_api_access_logs" {
  description = "API Gateway per-request access logs. Off in production to save CloudWatch Logs cost; on for load tests."
  type        = bool
  default     = false
}

variable "create_buckets_with_cli" {
  description = "Create the two S3 buckets with the AWS CLI instead of aws_s3_bucket (AWS Academy Learner Lab denies s3:GetBucketObjectLockConfiguration)."
  type        = bool
  default     = false
}

variable "web_origin_public" {
  description = "Serve the static SPA from the bucket's public website endpoint instead of a private bucket + Origin Access Control (AWS Academy Learner Lab denies cloudfront:CreateOriginAccessControl)."
  type        = bool
  default     = false
}

variable "enable_cloudfront" {
  description = "Serve the app through CloudFront (+WAF). False = API Gateway serves the SPA too, via the 'web' Lambda (AWS Academy Learner Lab denies cloudfront:CreateDistribution)."
  type        = bool
  default     = true
}
