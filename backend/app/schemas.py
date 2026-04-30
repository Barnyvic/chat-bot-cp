from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant|tool)$")
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=3, max_length=128)
    user_message: str = Field(min_length=1, max_length=4000)
    chat_history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    used_tools: list[str]
    session_id: str


class HealthResponse(BaseModel):
    status: str = "ok"
