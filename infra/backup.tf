# 5-year record retention for the databases (S3 files are covered by their lifecycle rule).
resource "aws_backup_vault" "main" {
  count         = var.enable_backup ? 1 : 0
  name          = "${local.name}-vault"
  kms_key_arn   = local.kms_key_arn
  force_destroy = !var.protect_data
}

resource "aws_backup_plan" "main" {
  count = var.enable_backup ? 1 : 0
  name  = "${local.name}-plan"

  rule {
    rule_name         = "daily-35-days"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = "cron(0 20 * * ? *)"
    lifecycle {
      delete_after = 35
    }
  }

  rule {
    rule_name         = "monthly-5-years"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = "cron(0 21 1 * ? *)"
    lifecycle {
      delete_after = 1825
    }
  }
}

resource "aws_iam_role" "backup" {
  count = var.enable_backup && !local.use_existing_role ? 1 : 0
  name  = "${local.name}-backup"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "backup.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  for_each = var.enable_backup && !local.use_existing_role ? toset([
    "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup",
    "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores",
  ]) : toset([])
  role       = aws_iam_role.backup[0].name
  policy_arn = each.value
}

resource "aws_backup_selection" "main" {
  count        = var.enable_backup ? 1 : 0
  name         = "${local.name}-databases"
  plan_id      = aws_backup_plan.main[0].id
  iam_role_arn = local.use_existing_role ? local.existing_role_arn : aws_iam_role.backup[0].arn
  resources    = [aws_db_instance.main.arn, aws_dynamodb_table.attempts.arn]
}
