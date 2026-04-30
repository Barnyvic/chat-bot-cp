from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.chat_service import ChatService
from app.config import settings
from app.logger import setup_logger
from app.rate_limit import SlidingWindowRateLimiter
from app.schemas import ChatRequest, ChatResponse, HealthResponse

logger = setup_logger()
app = FastAPI(title=settings.app_name)
chat_service = ChatService()
rate_limiter = SlidingWindowRateLimiter(limit=settings.requests_per_minute_per_session)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        if not rate_limiter.allow(req.session_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry shortly.")
        answer, used_tools = await chat_service.run(req.user_message, req.chat_history)
        return ChatResponse(answer=answer, used_tools=used_tools, session_id=req.session_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail="Internal chatbot error") from exc


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    if not rate_limiter.allow(req.session_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry shortly.")

    async def event_stream():
        try:
            answer, used_tools = await chat_service.run(req.user_message, req.chat_history)
            for token in answer.split(" "):
                yield f"event: token\ndata: {token} \n\n"
            if used_tools:
                yield f"event: tools\ndata: {','.join(used_tools)}\n\n"
            yield "event: done\ndata: complete\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming chat failed")
            yield f"event: error\ndata: {str(exc)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
