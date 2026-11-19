# AWS Academy Learner Lab profile (free). Use with: terraform apply -var-file=learner-lab.tfvars
# Learner Lab only allows us-east-1 / us-west-2 and does not allow creating IAM roles,
# so every service uses the pre-made LabRole. Services the lab may block are switched off;
# try turning any of them back on - if the apply fails with AccessDenied, switch it off again.
region                  = "us-east-1"
existing_role_name      = "LabRole"
use_customer_kms_key    = false # data still encrypted at rest with AWS-managed keys
enable_rds_proxy        = false # Lambdas connect straight to RDS with the Secrets Manager password
enable_waf              = false
enable_backup           = false
enable_flow_logs        = false
enable_ses              = false          # e-mails are written to CloudWatch Logs (/aws/lambda/uniexam-prod-notifier)
nat_gateway_per_az      = false          # one NAT saves lab credit; set true for the AZ-failure screenshot
db_multi_az             = true           # two-AZ database (rubric requirement)
enable_load_test_auth   = true           # Assignment 3 load test signs in test students; set false when finished
enable_api_access_logs  = true           # keep per-request logs during the load test for evidence
lambda_system_log_level = "INFO"         # keep Lambda REPORT lines (@initDuration) as cold-start evidence; production uses WARN
db_instance_class       = "db.t4g.micro" # the Assignment 2 size; load test showed RDS CPU at 6.4%, so no upsizing
create_buckets_with_cli = true           # lab SCP denies s3:GetBucketObjectLockConfiguration
web_origin_public       = true           # lab denies cloudfront:CreateOriginAccessControl; only static files are public
enable_cloudfront       = false          # lab denies cloudfront:CreateDistribution; API Gateway serves the SPA over HTTPS

# Load-test fixes. D (provisioned concurrency) is denied by the lab's service control policy, so it stays 0.
# E (run 2): more API memory, so cold starts get more CPU. 512 MB = run 1, 1769 MB = one full vCPU.
api_provisioned_concurrency = 0
api_memory_mb               = 1769
