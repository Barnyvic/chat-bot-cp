import json
from asyncio import TimeoutError as AsyncTimeoutError, wait_for
from typing import Any

from app.config import settings
from app.guardrails import validate_user_message
from app.llm import SYSTEM_PROMPT, client
from app.logger import setup_logger
from app.mcp_client import discover_tools, execute_tool
from app.schemas import ChatMessage

logger = setup_logger()


class ChatService:
    DATA_DEPENDENT_KEYWORDS = (
        "availability",
        "in stock",
        "stock",
        "order",
        "history",
        "status",
        "shipment",
        "shipping",
        "deliver",
        "track",
        "invoice",
        "pin",
        "email",
        "account",
        "authenticate",
        "lookup",
        "price",
        "buy",
        "purchase",
    )

    @classmethod
    def _requires_tool_evidence(cls, user_message: str) -> bool:
        normalized = user_message.lower()
        return any(keyword in normalized for keyword in cls.DATA_DEPENDENT_KEYWORDS)

    @staticmethod
    def _no_evidence_response() -> str:
        return (
            "I don't have verified backend data for that yet. "
            "Please ask me to check product, order, or account details and I will query Meridian systems."
        )

    async def run(self, user_message: str, history: list[ChatMessage]) -> tuple[str, list[str]]:
        if not settings.groq_api_key:
            return "Chatbot is not configured yet. Please set GROQ_API_KEY.", []

        ok, reason = validate_user_message(user_message)
        if not ok:
            return reason, []

        tools = await discover_tools()
        tool_specs = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description") or "MCP tool",
                    "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                },
            }
            for t in tools
        ]

        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-12:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        used_tools: list[str] = []

        for _ in range(settings.max_turns):
            try:
                response = await wait_for(
                    client.chat.completions.create(
                        model=settings.llm_model,
                        messages=messages,
                        tools=tool_specs,
                        tool_choice="auto",
                        temperature=0.2,
                    ),
                    timeout=settings.llm_timeout_seconds,
                )
            except AsyncTimeoutError:
                return "The assistant timed out while thinking. Please try again.", used_tools
            except Exception as exc: 
                error_text = str(exc)
                if "tool_use_failed" in error_text or "Failed to call a function" in error_text:
                    logger.warning("Model tool-call format failure", extra={"error": error_text[:500]})
                    return (
                        "I hit a tool-call formatting issue while querying Meridian systems. "
                        "Please retry your request once; if it persists, ask a more specific query "
                        "like 'list all products in monitors category'.",
                        used_tools,
                    )
                logger.exception("LLM completion failed")
                return "I could not process that request right now. Please try again.", used_tools

            choice = response.choices[0].message

            if not choice.tool_calls:
                final_text = choice.content or "I could not complete that request."
                if self._requires_tool_evidence(user_message) and not used_tools:
                    return self._no_evidence_response(), used_tools
                return final_text, used_tools

            messages.append(
                {
                    "role": "assistant",
                    "content": choice.content or "",
                    "tool_calls": [tc.model_dump() for tc in choice.tool_calls],
                }
            )

            for idx, tool_call in enumerate(choice.tool_calls):
                if idx >= settings.max_tool_calls_per_turn:
                    break

                tool_name = tool_call.function.name
                used_tools.append(tool_name)

                try:
                    tool_args = json.loads(tool_call.function.arguments or "{}")
                    tool_result = await wait_for(
                        execute_tool(tool_name, tool_args),
                        timeout=settings.tool_timeout_seconds,
                    )
                except AsyncTimeoutError:
                    logger.warning("Tool call timed out", extra={"tool_name": tool_name})
                    tool_result = "Tool timeout: the backend tool took too long to respond."
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Tool call failed", extra={"tool_name": tool_name})
                    tool_result = f"Tool error: {str(exc)}"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result[:8000],
                    }
                )

        return "I hit a safety stop while processing your request. Please try a narrower question.", used_tools
