# Video 2 Midpoint Script (2-4 mins)

## 1) What is built so far

"At this point I have a working full-stack prototype. The frontend is a Next.js chat interface with streaming responses, and the backend is a FastAPI orchestration service. The backend connects to Meridian's MCP server over streamable HTTP, discovers available tools dynamically, and lets the LLM call those tools for grounded responses."

"I also containerized both services and added AWS Terraform infrastructure using ECR plus App Runner, so this can be deployed in a repeatable way."

## 2) Decisions made

"I chose a cost-efficient model tier on Groq, defaulting to llama-3.1-8b-instant, to align with the business requirement that per-conversation cost stays low."

"I kept architecture modular: frontend handles UI only, backend handles conversation orchestration and tool execution, and infrastructure is separated in Terraform. This supports production hardening without rewriting core logic."

## 3) Corrections and improvements to AI-generated code

"I tightened safety and reliability after initial scaffolding:"
- Added prompt-injection and sensitive-data input checks
- Added bounded tool-call loops and turn limits
- Added timeout controls for both LLM and tool calls
- Added per-session rate limiting and CORS configuration
- Added unit tests for guardrails and CI checks for tests + Terraform validation

## 4) Challenges and mitigation

"Main challenge was balancing speed with production readiness under a 3-hour window. I prioritized end-to-end reliability and security guardrails over UI polish."

"Another challenge was ensuring safe tool use. I handled this by enforcing grounded MCP responses and preventing unbounded tool chaining."

## 5) Remaining work before final video

"Next I will run a full live walkthrough with realistic customer scenarios, capture screenshots, deploy the latest build to AWS, and prepare an honest trade-off assessment of what still needs hardening before production launch."
