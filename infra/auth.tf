resource "aws_cognito_user_pool" "main" {
  name                     = "${local.name}-users"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OPTIONAL"
  deletion_protection      = var.protect_data ? "ACTIVE" : "INACTIVE"

  # University accounts are provisioned by administrators; no public sign-up.
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  software_token_mfa_configuration {
    enabled = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_user_group" "roles" {
  for_each = {
    admins   = 1
    tutors   = 2
    students = 3
  }
  name         = each.key
  user_pool_id = aws_cognito_user_pool.main.id
  precedence   = each.value
  description  = "Role-based access: ${each.key}"
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${local.name}-${local.account_id}"
  user_pool_id = aws_cognito_user_pool.main.id
}

# Public SPA client: authorization-code flow with PKCE, no client secret.
resource "aws_cognito_user_pool_client" "web" {
  name                                 = "${local.name}-web"
  user_pool_id                         = aws_cognito_user_pool.main.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["${local.app_url}/"]
  logout_urls                          = ["${local.app_url}/"]
  explicit_auth_flows                  = concat(["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"], var.enable_load_test_auth ? ["ALLOW_ADMIN_USER_PASSWORD_AUTH"] : [])
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true

  id_token_validity      = 60
  access_token_validity  = 60
  refresh_token_validity = 12
  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "hours"
  }
}

resource "aws_cognito_user" "initial_admin" {
  count        = var.initial_admin_email != "" ? 1 : 0
  user_pool_id = aws_cognito_user_pool.main.id
  username     = var.initial_admin_email
  attributes = {
    email          = var.initial_admin_email
    email_verified = true
    name           = "Platform Administrator"
  }
  desired_delivery_mediums = ["EMAIL"]
}

resource "aws_cognito_user_in_group" "initial_admin" {
  count        = var.initial_admin_email != "" ? 1 : 0
  user_pool_id = aws_cognito_user_pool.main.id
  group_name   = aws_cognito_user_group.roles["admins"].name
  username     = aws_cognito_user.initial_admin[0].username
}
