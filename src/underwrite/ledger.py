"""Append-only JSONL ledger. Four record kinds, one file each, all timestamped UTC.

proposals.jsonl   what the LLM proposed (thesis, structure, p_profit)      — the CLAIM of edge
gate.jsonl        what the deterministic gate decided and why
orders.jsonl      what the executor CLAIMS happened (MCP place_option_order result)
audits.jsonl      what the auditor OBSERVED through the CLI (orders/positions/account)
outcomes.jsonl    resolved P&L per structure, joined back to the proposal
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import LEDGER_DIR

KINDS = ("proposals", "gate", "orders", "audits", "outcomes")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def path(kind: str) -> Path:
    assert kind in KINDS, kind
    return LEDGER_DIR / f"{kind}.jsonl"


def append(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    rec = {"ts": now(), **record}
    with path(kind).open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    return rec


def read(kind: str) -> list[dict[str, Any]]:
    p = path(kind)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def latest_by(kind: str, key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in read(kind):
        k = r.get(key)
        if k:
            out[k] = r
    return out


def dump_all() -> dict[str, list[dict[str, Any]]]:
    return {k: read(k) for k in KINDS}
