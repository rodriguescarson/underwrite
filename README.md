# Underwrite

**The options agent that has to earn its own position size.**

Every autonomous trading agent in this hackathon *claims* it manages risk. Underwrite measures whether its own claims are true, and will not size up until they are.

- **Strategist** — a Gemini agent (Google ADK) whose only market access is [Alpaca's MCP server](https://github.com/alpacahq/alpaca-mcp-server), filtered to read-only tools. It proposes one defined-risk options structure per cycle with a stated probability of profit, or declines.
- **Gate** — deterministic Python. Re-quotes every leg through alpaca-py, recomputes max loss itself, enforces 1% of equity per structure, DTE 7–45, bid/ask ≤ 15%, open interest ≥ 100, at most one structure per underlying, four total. Sizes from **measured calibration**, not from confidence.
- **Executor** — places the multi-leg order through the MCP server's `place_option_order`. What the server returns is recorded verbatim as the executor's **claim**.
- **Auditor** — asks the [Alpaca CLI](https://github.com/alpacahq/cli), a separate binary with its own HTTP client, what the account actually holds, and reconciles it against the claim. Claimed filled but not filled is a **silent failure**, and one silent failure freezes sizing at the floor.
- **Calibration** — Brier score and ECE of stated p_profit against realised outcomes, reported-vs-verified claim accuracy, silent-failure count. Position size unlocks from 0.25% to 1% of equity only when ≥10 structures have resolved with ECE ≤ 0.15, Brier ≤ 0.25 and 99%+ claim accuracy. The metric code is reused from [Attest](https://github.com/rodriguescarson/attest-fleet) (standard definitions, no LLM anywhere in it).

Two channels, one truth: MCP acts, CLI audits. That is how the hackathon's "MCP or CLI" requirement becomes the point of the product rather than a checkbox.

## Run

```bash
brew install alpacahq/tap/cli          # audit channel
uv sync                                 # Python 3.12 venv with google-adk, alpaca-py, mcp
cp .env.example .env                    # ALPACA_API_KEY / ALPACA_SECRET_KEY of a FRESH $100k paper account, GOOGLE_API_KEY
uv run underwrite doctor                # CLI, MCP server and alpaca-py all reach the account
uv run underwrite run --dry             # one cycle: audit → strategist → gate, no order
uv run underwrite loop --every 900      # trade until the close; audits every claim; stops when the market closes
uv run underwrite report                # docs/REPORT.md + docs/index.html + docs/ledger.json
```

The MCP server is launched on demand with `uvx alpaca-mcp-server` (stdio) — nothing to install.

Strategist model: `UNDERWRITE_MODEL` is a native Gemini id by default; set it to `openrouter/<vendor>/<model>` (with `OPENROUTER_API_KEY`) to route through LiteLLM — the desk did exactly that mid-session on 2026-09-03 when the Gemini key ran out of quota, without stopping.

## The ledger

Append-only JSONL under `ledger/`, one file per record kind: `proposals`, `gate`, `orders` (claims), `audits` (CLI observations), `outcomes`. The report is generated from these files and nothing else; every number in it has a line behind it.

## Honest limits

- Calibration needs resolved trades. In a 7-day hackathon the desk trades at the floor the whole time — which is the correct behaviour for an agent that has not yet proven it can predict its own outcomes, and the report says so.
- Earnings dates are not checked; the allowlist is liquid index ETFs and mega-caps to keep event risk low.
- Paper trading fills at the NBBO mid-ish; live fills would be worse. The auditor records the actual fill prices so that gap is measurable, not assumed.

Apache-2.0.
