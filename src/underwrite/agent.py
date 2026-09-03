"""The strategist: a Gemini agent (Google ADK) whose only market access is Alpaca's MCP
server, filtered to read-only tools. It can look; it cannot touch. It ends its turn with
a JSON proposal that the gate will re-verify against live quotes it fetches itself."""
from __future__ import annotations

import asyncio
import json
import re
from datetime import date, timedelta
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.genai import types

from .config import FALLBACK_MODEL, MODEL, RISK
from .mcp_exec import server_params

READ_ONLY = [
    "get_clock", "get_account_info", "get_all_positions", "get_orders",
    "get_stock_snapshot", "get_stock_bars", "get_news",
    "get_option_chain", "get_option_snapshot", "get_option_contracts", "get_option_latest_quote",
]

INSTRUCTION = f"""You are the strategist of Underwrite, an autonomous options desk trading a paper account.
You propose at most ONE defined-risk options structure per cycle, or no trade. You never place orders; a
deterministic gate re-prices every leg you name and decides size. Be precise and cite the tool data you used.

Allowed underlyings: {", ".join(RISK.allowed_underlyings)}.
Allowed structures: bull_put_spread, bear_call_spread, iron_condor, bull_call_spread, bear_put_spread.
Constraints the gate WILL enforce (so respect them): every leg {RISK.min_dte}-{RISK.max_dte} days to expiration;
bid/ask spread per leg <= {RISK.max_bid_ask_spread_frac:.0%} of mid; open interest >= {RISK.min_open_interest};
max loss per 1x structure <= 1% of equity; you must state p_profit >= {RISK.min_p_profit} to trade at all.

Method, in order:
1. get_clock, get_account_info, get_all_positions (do not add to an underlying already held).
2. Pick ONE underlying; get_stock_snapshot for it; optionally get_stock_bars (daily, 30 days) and get_news.
3. get_option_chain for it with expiration_date_gte/lte inside the DTE window and a strike band of about ±8% around spot
   (use type="put" or "call" to keep it small; limit 200). Choose short strikes near 0.15-0.30 delta; widths 1-5 points.
4. get_option_snapshot for exactly the legs you intend (comma-separated symbols) and quote bid/ask from it.
5. Decide. Your p_profit must be an honest probability that the structure is CLOSED for a profit under the exit plan
   (take profit at 50% of credit, stop at 2x credit, close at 2 DTE). Explain how you got the number (delta, IV, trend).

Finish with exactly one fenced JSON block and nothing after it. Either:
```json
{{"no_trade": true, "reason": "..."}}
```
or
```json
{{"underlying": "SPY", "structure": "bull_put_spread",
 "legs": [{{"symbol": "SPY260925P00600000", "side": "sell", "ratio_qty": 1, "strike": 600, "right": "put", "expiration": "2026-09-25"}},
          {{"symbol": "SPY260925P00595000", "side": "buy", "ratio_qty": 1, "strike": 595, "right": "put", "expiration": "2026-09-25"}}],
 "net_credit": 0.95, "max_loss_per_structure": 405, "limit_price": 0.93, "p_profit": 0.68,
 "thesis": "...", "data_cited": ["get_stock_snapshot SPY last=...", "get_option_snapshot ... bid/ask ..."],
 "exit_plan": "take profit at 50% of credit, stop at 2x credit, close at 2 DTE"}}
```
Numbers are per share (contract multiplier 100 applied only in max_loss_per_structure). Use OCC symbols exactly as the chain returned them."""

JSON_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


def extract_json(text: str) -> dict[str, Any] | None:
    m = JSON_RE.findall(text)
    if not m:
        return None
    try:
        return json.loads(m[-1])
    except json.JSONDecodeError:
        return None


async def _propose(context: dict[str, Any], model: str) -> tuple[dict[str, Any] | None, str, list[str]]:
    toolset = McpToolset(connection_params=StdioConnectionParams(server_params=server_params(), timeout=120), tool_filter=READ_ONLY)
    agent = LlmAgent(name="strategist", model=model, instruction=INSTRUCTION, tools=[toolset])
    sessions = InMemorySessionService()
    runner = Runner(agent=agent, app_name="underwrite", session_service=sessions)
    session = await sessions.create_session(app_name="underwrite", user_id="uw")
    today = date.today()
    ctx = {**context, "today": today.isoformat(), "dte_window": [(today + timedelta(days=RISK.min_dte)).isoformat(), (today + timedelta(days=RISK.max_dte)).isoformat()]}
    msg = types.Content(role="user", parts=[types.Part(text="Cycle context:\n" + json.dumps(ctx, indent=1) + "\nResearch with the tools, then answer with the JSON block.")])
    final, calls = "", []
    try:
        async for ev in runner.run_async(user_id="uw", session_id=session.id, new_message=msg):
            if ev.content and ev.content.parts:
                for part in ev.content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc is not None:
                        calls.append(fc.name)
                    if ev.is_final_response() and getattr(part, "text", None):
                        final += part.text
    finally:
        try:
            await toolset.close()
        except Exception:
            pass
    return extract_json(final), final, calls


def propose(context: dict[str, Any], attempts: int = 3) -> tuple[dict[str, Any] | None, str, list[str], str]:
    """Returns (proposal_json_or_None, transcript, tool_calls, model_used).
    Network blips (DNS, resets) and 503s are retried with backoff before falling back to the next model."""
    import time as _t
    last = "no attempt"
    for model in (MODEL, FALLBACK_MODEL):
        for attempt in range(attempts):
            try:
                j, text, calls = asyncio.run(_propose(context, model))
                return j, text, calls, model
            except Exception as e:  # model unavailable, quota, DNS — retry, then fall through
                last = f"{type(e).__name__}: {str(e)[:300]}"
                transient = any(k in last for k in ("DNS", "Cannot connect", "503", "UNAVAILABLE", "reset", "timeout", "Timeout", "429"))
                if attempt < attempts - 1 and transient:
                    _t.sleep(5 * (attempt + 1))
                    continue
                break
    return None, last, [], "none"
