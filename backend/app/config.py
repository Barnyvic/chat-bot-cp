from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "meridian-support-chatbot-backend"
    app_env: str = "dev"
    app_debug: bool = False

    groq_api_key: str = Field(default="")
    llm_model: str = Field(default="llama-3.1-8b-instant")

    mcp_server_url: AnyHttpUrl = Field(
        default="https://order-mcp-74afyau24q-uc.a.run.app/mcp"
    )

    max_turns: int = 12
    max_tool_calls_per_turn: int = 4
    llm_timeout_seconds: float = 30.0
    tool_timeout_seconds: float = 25.0
    requests_per_minute_per_session: int = 20
    cors_allowed_origins: list[str] = ["*"]

    # Guardrails
    allowed_email_domains: list[str] = ["example.com", "example.net", "example.org"]


settings = Settings()
