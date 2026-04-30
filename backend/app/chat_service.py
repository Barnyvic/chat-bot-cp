import json
import re
from asyncio import TimeoutError as AsyncTimeoutError, sleep, wait_for
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

    @staticmethod
    def _compact_history(history: list[ChatMessage]) -> list[dict[str, str]]:
        """
        Keep recent conversational context while preventing token blowups from
        very long tool-rich answers (e.g. large order lists).
        """
        compact: list[dict[str, str]] = []
        total_chars = 0
        max_total_chars = 7000
        max_message_chars = 1200

        for msg in reversed(history[-12:]):
            content = (msg.content or "").strip()
            if not content:
                continue
            clipped = content[:max_message_chars]
            if total_chars + len(clipped) > max_total_chars:
                continue
            compact.append({"role": msg.role, "content": clipped})
            total_chars += len(clipped)

        compact.reverse()
        return compact

    @staticmethod
    def _extract_failed_function_call(error_text: str) -> tuple[str, dict[str, Any]] | None:
        match = re.search(
            r"<function=(?P<name>[A-Za-z0-9_]+)>(?P<body>.*?)</function>",
            error_text,
            flags=re.DOTALL,
        )
        if not match:
            return None

        tool_name = match.group("name").strip()
        body = match.group("body").strip()
        if not body:
            return tool_name, {}

        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                return tool_name, parsed
        except Exception:  # noqa: BLE001
            pass

        kv_pairs = re.findall(r'([A-Za-z0-9_]+)\s*=\s*"([^"]*)"', body)
        if kv_pairs:
            return tool_name, {k: v for k, v in kv_pairs}

        return tool_name, {}

    async def _recover_from_tool_use_failed(
        self,
        error_text: str,
        user_message: str,
        used_tools: list[str],
    ) -> str | None:
        recovered = self._extract_failed_function_call(error_text)
        if not recovered:
            return None

        tool_name, tool_args = recovered
        used_tools.append(tool_name)

        try:
            tool_result = await wait_for(
                execute_tool(tool_name, tool_args),
                timeout=settings.tool_timeout_seconds,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Recovery tool execution failed",
                extra={"tool_name": tool_name},
            )
            return None

        try:
            summary = await wait_for(
                client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                "Summarize this backend tool result for the customer clearly and concisely. "
                                "Do not mention internal tool names.\n\n"
                                f"Original user request: {user_message}\n"
                                f"Tool result:\n{tool_result[:8000]}"
                            ),
                        },
                    ],
                    temperature=0.2,
                ),
                timeout=settings.llm_timeout_seconds,
            )
            return summary.choices[0].message.content or tool_result[:1200]
        except Exception:  # noqa: BLE001
            logger.exception("Recovery summarization failed")
            return tool_result[:1200]

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
        messages.extend(self._compact_history(history))
        messages.append({"role": "user", "content": user_message})

        used_tools: list[str] = []
        rate_limit_retry_used = False

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
                    recovered_answer = await self._recover_from_tool_use_failed(
                        error_text=error_text,
                        user_message=user_message,
                        used_tools=used_tools,
                    )
                    if recovered_answer:
                        return recovered_answer, used_tools
                    logger.warning("Model tool-call format failure", extra={"error": error_text[:500]})
                    return (
                        "I hit a tool-call formatting issue while querying Meridian systems. "
                        "Please retry your request once; if it persists, ask a more specific query "
                        "like 'list all products in monitors category'.",
                        used_tools,
                    )
                if "rate limit" in error_text.lower() or "too many requests" in error_text.lower():
                    if not rate_limit_retry_used:
                        rate_limit_retry_used = True
                        await sleep(2)
                        continue
                    return (
                        "The AI provider is rate-limiting requests right now. Please wait a few seconds and retry.",
                        used_tools,
                    )
                if "maximum context length" in error_text.lower() or "context" in error_text.lower():
                    return (
                        "This conversation became too long for one request. Please retry with a shorter follow-up.",
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
