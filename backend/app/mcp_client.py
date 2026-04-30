import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import settings


@asynccontextmanager
async def get_mcp_session():
    async with streamablehttp_client(str(settings.mcp_server_url)) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def discover_tools() -> list[dict[str, Any]]:
    async with get_mcp_session() as session:
        tools = await session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            for t in tools.tools
        ]


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    async with get_mcp_session() as session:
        result = await session.call_tool(name=name, arguments=arguments)

    if hasattr(result, "content"):
        content = []
        for item in result.content:
            if hasattr(item, "text"):
                content.append(item.text)
            else:
                content.append(str(item))
        return "\n".join(content)

    return json.dumps(result, default=str)
