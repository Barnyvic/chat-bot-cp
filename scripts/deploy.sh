#!/usr/bin/env bash
set -euo pipefail

# Usage:
# AWS_REGION=us-east-1 PROJECT_NAME=meridian-chatbot GROQ_API_KEY=... ./scripts/deploy.sh

AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-meridian-chatbot}"
BACKEND_TAG="${BACKEND_TAG:-latest}"
FRONTEND_TAG="${FRONTEND_TAG:-latest}"
MCP_SERVER_URL="${MCP_SERVER_URL:-https://order-mcp-74afyau24q-uc.a.run.app/mcp}"

if [[ -z "${GROQ_API_KEY:-}" ]]; then
  echo "ERROR: GROQ_API_KEY is required"
  exit 1
fi

echo "==> Terraform apply"
pushd infra/terraform >/dev/null

export TF_VAR_groq_api_key="${GROQ_API_KEY}"

terraform init
terraform apply -auto-approve \
  -var="aws_region=${AWS_REGION}" \
  -var="project_name=${PROJECT_NAME}" \
  -var="backend_image_tag=${BACKEND_TAG}" \
  -var="frontend_image_tag=${FRONTEND_TAG}" \
  -var="mcp_server_url=${MCP_SERVER_URL}" \
  -target=aws_ecr_repository.backend \
  -target=aws_ecr_repository.frontend \
  -target=aws_iam_role.apprunner_ecr_access_role \
  -target=aws_iam_role_policy_attachment.apprunner_ecr_access \
  -target=aws_iam_role.apprunner_instance_role \
  -target=aws_iam_role_policy.apprunner_instance_ssm_policy \
  -target=aws_ssm_parameter.groq_api_key

BACKEND_REPO_URL="$(terraform output -raw backend_ecr_repository_url)"
FRONTEND_REPO_URL="$(terraform output -raw frontend_ecr_repository_url)"

popd >/dev/null

AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

echo "==> Logging into ECR"
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Building and pushing backend image"
docker buildx build --platform linux/amd64 -t "${BACKEND_REPO_URL}:${BACKEND_TAG}" backend/ --push

echo "==> Building and pushing frontend image"
docker buildx build --platform linux/amd64 -t "${FRONTEND_REPO_URL}:${FRONTEND_TAG}" frontend/ --push

echo "==> Terraform full apply"
pushd infra/terraform >/dev/null
terraform apply -auto-approve \
  -var="aws_region=${AWS_REGION}" \
  -var="project_name=${PROJECT_NAME}" \
  -var="backend_image_tag=${BACKEND_TAG}" \
  -var="frontend_image_tag=${FRONTEND_TAG}" \
  -var="mcp_server_url=${MCP_SERVER_URL}"
FRONTEND_SERVICE_URL="$(terraform output -raw frontend_service_url)"
popd >/dev/null

echo "==> Deployment submitted. App Runner auto-deploys from ECR."
echo "Frontend URL: ${FRONTEND_SERVICE_URL}"
