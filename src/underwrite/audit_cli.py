"""The audit channel: Alpaca's official CLI, spoken to as a subprocess with JSON output.

The agent acts through the MCP server; the auditor never trusts that path. It asks the
CLI — a separate binary, separate HTTP client — what the account actually holds, and
reconciles it against what the executor claimed. Two channels, one truth.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from .config import alpaca_env


class CliError(RuntimeError):
    pass


def _run(args: list[str]) -> Any:
    exe = shutil.which("alpaca")
    if not exe:
        raise CliError("alpaca CLI not installed (brew install alpacahq/tap/cli)")
    env = {**os.environ, **alpaca_env()}
    env.pop("ALPACA_LIVE_TRADE", None)  # paper, always
    proc = subprocess.run([exe, *args, "--quiet"], capture_output=True, text=True, env=env, timeout=60)
    if proc.returncode != 0:
        raise CliError(f"alpaca {' '.join(args)} → {proc.returncode}: {proc.stderr.strip()[:400]}")
    out = proc.stdout.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:  # CSV or plain text slipped through
        raise CliError(f"non-JSON from CLI: {out[:200]}") from e


def account() -> dict[str, Any]:
    return _run(["account", "get"])


def positions() -> list[dict[str, Any]]:
    return _run(["position", "list"]) or []


def orders(status: str = "all", limit: int = 200) -> list[dict[str, Any]]:
    return _run(["order", "list", "--status", status, "--limit", str(limit), "--nested", "--direction", "desc"]) or []


def order(order_id: str) -> dict[str, Any]:
    return _run(["order", "get", order_id])


def clock() -> dict[str, Any]:
    return _run(["clock"])


def version() -> str:
    exe = shutil.which("alpaca")
    if not exe:
        return "missing"
    return subprocess.run([exe, "version"], capture_output=True, text=True).stdout.strip()
