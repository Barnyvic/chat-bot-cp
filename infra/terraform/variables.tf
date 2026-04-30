variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "meridian-chatbot"
}

variable "backend_image_tag" {
  type    = string
  default = "latest"
}

variable "frontend_image_tag" {
  type    = string
  default = "latest"
}

variable "groq_api_key" {
  type      = string
  sensitive = true
}

variable "mcp_server_url" {
  type    = string
  default = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"
}
