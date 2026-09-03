"""underwrite — the options agent that has to earn its own position size.

  underwrite doctor            check keys, CLI, MCP server, account
  underwrite run [--dry]       one cycle
  underwrite loop [--every S]  cycles until the market closes
  underwrite audit             reconcile every claim through the CLI, resolve outcomes
  underwrite report            docs/REPORT.md + docs/index.html
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from rich.console import Console

console = Console()


def cmd_doctor(_: argparse.Namespace) -> int:
    from . import audit_cli, calibration, market, mcp_exec
    ok = True
    try:
        a = audit_cli.account()
        console.print(f"[green]CLI[/] {audit_cli.version()} account {a.get('account_number')} equity {a.get('equity')} status {a.get('status')} options level {a.get('options_approved_level')}")
        console.print(f"[green]clock[/] {json.dumps(audit_cli.clock())}")
    except Exception as e:
        ok = False
        console.print(f"[red]CLI failed[/] {e}")
    try:
        txt = mcp_exec.call_tool("get_account_info", {})
        console.print(f"[green]MCP[/] get_account_info → {txt[:160].replace(chr(10), ' ')}")
    except Exception as e:
        ok = False
        console.print(f"[red]MCP failed[/] {e}")
    try:
        eq, info = market.account_equity()
        console.print(f"[green]alpaca-py[/] equity {eq} created {info.get('created_at')}")
        if abs(eq - 100_000) > 1_000 and not any(k for k in info if k == "_"):
            console.print("[yellow]note[/] equity is not ~$100,000 — the hackathon requires a fresh $100k paper account")
    except Exception as e:
        ok = False
        console.print(f"[red]alpaca-py failed[/] {e}")
    console.print(f"[cyan]calibration[/] {calibration.compute().as_dict()}")
    return 0 if ok else 1


def cmd_run(ns: argparse.Namespace) -> int:
    from .cycle import run_once
    log = run_once(dry=ns.dry)
    console.print_json(json.dumps(log, default=str))
    return 0


def cmd_loop(ns: argparse.Namespace) -> int:
    from . import audit_cli
    from .cycle import run_once
    while True:
        log = run_once(dry=ns.dry)
        console.print(f"[bold]{time.strftime('%H:%M:%S')}[/] equity={log.get('equity')} exits={len(log.get('exits') or [])} order={log.get('order')} skipped={log.get('skipped')}")
        if not audit_cli.clock().get("is_open"):
            console.print("market closed — loop ends (a pod is either working or off; so is a desk)")
            return 0
        time.sleep(ns.every)


def cmd_audit(_: argparse.Namespace) -> int:
    from .cycle import reconcile, resolve_outcomes, snapshot
    snapshot()
    console.print(f"reconciled {reconcile()} claims, resolved {resolve_outcomes()} structures")
    return 0


def cmd_report(_: argparse.Namespace) -> int:
    from .report import write
    p = write()
    console.print(f"wrote {p} (+ index.html, ledger.json)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="underwrite", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    r = sub.add_parser("run"); r.add_argument("--dry", action="store_true"); r.set_defaults(fn=cmd_run)
    l = sub.add_parser("loop"); l.add_argument("--every", type=int, default=900); l.add_argument("--dry", action="store_true"); l.set_defaults(fn=cmd_loop)
    sub.add_parser("audit").set_defaults(fn=cmd_audit)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    ns = ap.parse_args(argv)
    return ns.fn(ns)


if __name__ == "__main__":
    sys.exit(main())
