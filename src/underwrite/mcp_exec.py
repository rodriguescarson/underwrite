"""The ACTION channel: Alpaca's official MCP server, driven as an MCP client over stdio.

Orders are placed by calling the server's `place_option_order` tool — the same tool an
LLM would call — so the executor's claim is exactly what the MCP server returned."""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import alpaca_env

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def server_params() -> StdioServerParameters:
    return StdioServerParameters(command="uvx", args=["alpaca-mcp-server"], env={**os.environ, **alpaca_env()})


async def _call(name: str, args: dict[str, Any]) -> str:
    async with stdio_client(server_params()) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(name, args)
            texts = [c.text for c in res.content if getattr(c, "type", "") == "text"]
            return "\n".join(texts)


def call_tool(name: str, args: dict[str, Any]) -> str:
    return asyncio.run(_call(name, args))


def parse_order_id(text: str) -> str | None:
    """MCP tool results are formatted text; pull the order id out of it."""
    try:
        j = json.loads(text)
        if isinstance(j, dict) and j.get("id"):
            return str(j["id"])
    except Exception:
        pass
    m = re.search(r"(?:order[_ ]id|Order ID|id)[\"':\s]+(" + UUID_RE.pattern + ")", text, re.I)
    if m:
        return m.group(1)
    m = UUID_RE.search(text)
    return m.group(0) if m else None


def place_mleg(legs: list[dict[str, str]], qty: int, limit_price: float, client_order_id: str) -> str:
    """limit_price follows the MCP/Alpaca mleg convention: positive = debit, negative = credit."""
    return call_tool("place_option_order", {
        "qty": str(qty),
        "type": "limit",
        "time_in_force": "day",
        "order_class": "mleg",
        "limit_price": f"{limit_price:.2f}",
        "client_order_id": client_order_id,
        "legs": legs,
    })


def cancel(order_id: str) -> str:
    return call_tool("cancel_order_by_id", {"order_id": order_id})


def order_status(order_id: str) -> str:
    return call_tool("get_order_by_id", {"order_id": order_id, "nested": True})
