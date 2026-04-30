output "backend_ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "frontend_ecr_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "backend_service_url" {
  value = "https://${aws_apprunner_service.backend.service_url}"
}

output "frontend_service_url" {
  value = "https://${aws_apprunner_service.frontend.service_url}"
}
