# ---------------------------------------------------------------- RDS PostgreSQL (Multi-AZ)
resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.data[*].id
}

resource "aws_db_parameter_group" "main" {
  name   = "${local.name}-pg${var.db_engine_version}"
  family = "postgres${var.db_engine_version}"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "500"
  }
}

resource "aws_db_instance" "main" {
  identifier     = "${local.name}-db"
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  multi_az              = var.db_multi_az # synchronous standby in the second AZ, automatic failover
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = local.kms_key_arn # null = AWS-managed aws/rds key

  db_name                       = "exams"
  username                      = "examadmin"
  manage_master_user_password   = true # password generated and rotated in Secrets Manager
  master_user_secret_kms_key_id = local.kms_key_arn

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  parameter_group_name   = aws_db_parameter_group.main.name
  publicly_accessible    = false

  backup_retention_period         = 7 # point-in-time restore, transaction logs every 5 min
  backup_window                   = "18:00-19:00"
  maintenance_window              = "sun:19:30-sun:20:30"
  copy_tags_to_snapshot           = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
  auto_minor_version_upgrade      = true
  apply_immediately               = true

  deletion_protection       = var.protect_data
  skip_final_snapshot       = !var.protect_data
  final_snapshot_identifier = "${local.name}-db-final"
}

# ---------------------------------------------------------------- RDS Proxy
resource "aws_iam_role" "rds_proxy" {
  count = var.enable_rds_proxy && !local.use_existing_role ? 1 : 0
  name  = "${local.name}-rds-proxy"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "rds.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "rds_proxy" {
  count = var.enable_rds_proxy && !local.use_existing_role ? 1 : 0
  role  = aws_iam_role.rds_proxy[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
        Resource = aws_db_instance.main.master_user_secret[0].secret_arn
      },
      {
        Effect    = "Allow"
        Action    = "kms:Decrypt"
        Resource  = coalesce(local.kms_key_arn, "*")
        Condition = { StringEquals = { "kms:ViaService" = "secretsmanager.${var.region}.amazonaws.com" } }
      },
    ]
  })
}

resource "aws_db_proxy" "main" {
  count                  = var.enable_rds_proxy ? 1 : 0
  name                   = "${local.name}-proxy"
  engine_family          = "POSTGRESQL"
  role_arn               = local.use_existing_role ? local.existing_role_arn : aws_iam_role.rds_proxy[0].arn
  vpc_subnet_ids         = aws_subnet.data[*].id
  vpc_security_group_ids = [aws_security_group.proxy.id]
  require_tls            = true
  idle_client_timeout    = 1800

  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "REQUIRED" # Lambdas connect with IAM tokens, never a stored password
    secret_arn  = aws_db_instance.main.master_user_secret[0].secret_arn
  }

  depends_on = [aws_iam_role_policy.rds_proxy]
}

resource "aws_db_proxy_default_target_group" "main" {
  count         = var.enable_rds_proxy ? 1 : 0
  db_proxy_name = aws_db_proxy.main[0].name
  connection_pool_config {
    max_connections_percent      = 90
    max_idle_connections_percent = 50
    connection_borrow_timeout    = 120
  }
}

resource "aws_db_proxy_target" "main" {
  count                  = var.enable_rds_proxy ? 1 : 0
  db_proxy_name          = aws_db_proxy.main[0].name
  target_group_name      = aws_db_proxy_default_target_group.main[0].name
  db_instance_identifier = aws_db_instance.main.identifier
}

locals {
  # arn:aws:rds:<region>:<acct>:db-proxy:prx-xxxx -> prx-xxxx (used in rds-db:connect ARNs)
  db_proxy_resource_id = var.enable_rds_proxy ? element(split(":", aws_db_proxy.main[0].arn), 6) : ""
  db_secret_arn        = aws_db_instance.main.master_user_secret[0].secret_arn
  # With the proxy: IAM-token auth through the proxy. Without: direct TLS to RDS with the managed secret.
  db_host = var.enable_rds_proxy ? aws_db_proxy.main[0].endpoint : aws_db_instance.main.address
}

# ---------------------------------------------------------------- DynamoDB (exam attempts + autosaved answers)
resource "aws_dynamodb_table" "attempts" {
  name         = "${local.name}-attempts"
  billing_mode = "PAY_PER_REQUEST" # absorbs the exam-start spike with no capacity planning
  hash_key     = "attempt_id"      # "<examId>#<studentSub>": spreads writes across partitions

  attribute {
    name = "attempt_id"
    type = "S"
  }
  attribute {
    name = "open_status"
    type = "S"
  }
  attribute {
    name = "deadline_epoch"
    type = "N"
  }

  # Sparse index: only IN_PROGRESS attempts carry open_status, so the sweeper reads just those.
  global_secondary_index {
    name            = "open-by-deadline"
    hash_key        = "open_status"
    range_key       = "deadline_epoch"
    projection_type = "KEYS_ONLY"
  }

  point_in_time_recovery {
    enabled = true # restore to any second in the last 35 days (RPO ~ seconds)
  }

  # CMK when enabled; otherwise DynamoDB's default AWS-owned key (still encrypted at rest).
  server_side_encryption {
    enabled     = var.use_customer_kms_key
    kms_key_arn = local.kms_key_arn
  }

  deletion_protection_enabled = var.protect_data
}
