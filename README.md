# Meridian Electronics - AI Support Chatbot Prototype

Production-oriented prototype of a customer support chatbot that uses an LLM plus MCP tools to support Meridian workflows:
- Product availability checks
- Order placement support
- Order history lookup
- Returning customer authentication flows

## Architecture

- `frontend/` - Next.js + Tailwind chat interface with SSE streaming
  - `/api/chat/stream` proxy route forwards streaming to backend
- `backend/` - FastAPI orchestration service
  - Dynamic MCP tool discovery + execution
  - LLM function-calling loop (Groq, `llama-3.1-8b-instant` default)
  - `/chat/stream` SSE endpoint for incremental frontend rendering
  - Guardrails: prompt-injection checks, basic PII pattern blocks, bounded tool calls/turns
- `infra/terraform/` - AWS deploy infrastructure
  - ECR repositories for frontend/backend images
  - App Runner services for both containers
  - SSM SecureString for Groq API key

## Why this architecture

- Keeps LLM app away from direct DB access and uses MCP boundary.
- Uses low-cost model tier for business viability.
- Separates UI and orchestration for easier scaling and independent deploys.
- Adds baseline guardrails and operational controls expected in production prototypes.

## Local Run

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set GROQ_API_KEY in .env
uvicorn app.main:app --reload --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
NEXT_BACKEND_URL=http://localhost:8000 npm run dev
```

### 3) Or with Docker Compose

```bash
export GROQ_API_KEY=your_key
export LLM_MODEL=llama-3.3-70b-versatile
docker compose up --build
```

Frontend: `http://localhost:3000`
Backend health: `http://localhost:8000/health`

## AWS Deploy (Terraform + App Runner)

### Prereqs
- AWS CLI configured
- Terraform >= 1.6
- Docker + ability to push to ECR

### 1) Initialize Terraform

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# edit groq_api_key and other vars
terraform init
terraform apply
```

Capture outputs:
- `backend_ecr_repository_url`
- `frontend_ecr_repository_url`

### 2) Build + push images

Use ECR URLs from Terraform output:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com

docker build -t <backend_repo_url>:latest backend/
docker push <backend_repo_url>:latest

docker build -t <frontend_repo_url>:latest frontend/
docker push <frontend_repo_url>:latest
```

App Runner auto-deploys from ECR.

### Fast path deploy

```bash
AWS_REGION=us-east-1 PROJECT_NAME=meridian-chatbot GROQ_API_KEY=your_key ./scripts/deploy.sh
```

## Guardrails included

- Input scanning for obvious prompt-injection patterns
- Input scanning for sensitive number patterns (SSN/card-style)
- Tool-call loop bounded by max turns and max calls per turn
- Per-session rate limiting on `/chat`
- LLM and MCP tool timeout limits
- CORS allowlist support via config
- Structured error handling and no stack traces in user responses
- Environment-based secret/config handling

## Test

```bash
cd backend
pytest -q
```

Or:

```bash
make test-backend
```

## Assessment Deliverables Checklist

- [ ] Video 1 (Kickoff): business problem + implementation plan
- [ ] Video 2 (Midpoint): progress, corrections, blockers
- [ ] Video 3 (Final): live demo + architecture + limitations
- [ ] GitHub repo
- [ ] Live deployed URL
- [ ] Screenshots

## Suggested demo scenarios

1. Product availability question for a monitor model
2. Customer authentication (email + pin) and order history lookup
3. Order-support workflow (status or details)
4. Injection attempt (show safe refusal)

Detailed scripts:
- `docs/video2-midpoint-script.md`
- `docs/demo-scenarios.md`

## If given more time

- Add Redis-backed session memory and rate limits
- Add observability stack (metrics, traces, dashboards)
- Add stricter output filters and policy engine
- Add integration tests against MCP sandbox environment
- Evaluate vector DB only if support knowledge corpus is added (policies/FAQ/docs)
