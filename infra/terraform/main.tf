locals {
  backend_repo_name  = "${var.project_name}-backend"
  frontend_repo_name = "${var.project_name}-frontend"
}

resource "aws_ecr_repository" "backend" {
  name                 = local.backend_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = local.frontend_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_iam_role" "apprunner_ecr_access_role" {
  name = "${var.project_name}-apprunner-ecr-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_iam_role" "apprunner_instance_role" {
  name = "${var.project_name}-apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "apprunner_instance_ssm_policy" {
  name = "${var.project_name}-apprunner-ssm-policy"
  role = aws_iam_role.apprunner_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = aws_ssm_parameter.groq_api_key.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_apprunner_service" "backend" {
  service_name = "${var.project_name}-backend"

  instance_configuration {
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  source_configuration {
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access_role.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          LLM_MODEL      = "llama-3.1-8b-instant"
          MCP_SERVER_URL = var.mcp_server_url
        }
        runtime_environment_secrets = {
          GROQ_API_KEY = aws_ssm_parameter.groq_api_key.arn
        }
      }
    }
  }

  health_check_configuration {
    path                = "/health"
    protocol            = "HTTP"
    healthy_threshold   = 1
    unhealthy_threshold = 5
    interval            = 10
    timeout             = 5
  }
}

resource "aws_ssm_parameter" "groq_api_key" {
  name  = "/${var.project_name}/groq_api_key"
  type  = "SecureString"
  value = var.groq_api_key
}

resource "aws_apprunner_service" "frontend" {
  service_name = "${var.project_name}-frontend"

  source_configuration {
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access_role.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.frontend.repository_url}:${var.frontend_image_tag}"
      image_repository_type = "ECR"

      image_configuration {
        port = "3000"
        runtime_environment_variables = {
          NEXT_BACKEND_URL = "https://${aws_apprunner_service.backend.service_url}"
        }
      }
    }
  }
}
