# Underwrite — desk report
_Generated 2026-09-03T18:58+00:00 from the ledger and nothing else. Action channel: Alpaca MCP server (`uvx alpaca-mcp-server`). Audit channel: Alpaca CLI . Strategist: Gemini via Google ADK, read-only MCP tools._

## The idea in one line
The strategist proposes, a deterministic gate re-prices and sizes, the executor acts through Alpaca's MCP server, an independent auditor re-checks every claim through the Alpaca CLI, and position size is earned by measured calibration rather than granted by confidence.

## How to verify this report
Every order id below appears twice: once in the executor's claim (what the MCP server returned) and once in the CLI audit (what the account actually holds). Every gate decision lists its reasons. Every proposal lists the MCP tool calls it made. The raw ledger is at `ledger.json` next to this page; the code is at github.com/rodriguescarson/underwrite.

## Account (as the CLI sees it)
| first snapshot | equity | latest snapshot | equity | account |
|---|---|---|---|---|
| — | — | — | — | — |

## Calibration — the numbers that set position size
| claims | audited | claim accuracy | silent failures | resolved | wins | Brier | ECE | risk/trade | status |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | None | 0 | 0 | 0 | None | None | 0.25% | floor |

Gate verdict: only 0/10 structures resolved; ECE undefined; Brier undefined; claim accuracy None < 0.99

## Claims vs. audits (executor said → CLI observed)
_no orders yet_

## Gate decisions
_none_

## Strategist proposals
_none_

## Resolved structures
_none resolved yet — provisional MTM is in the latest snapshot below_

## Open positions, mark-to-market (latest CLI snapshot)
_flat_

## The gate's constants
| parameter | value |
|---|---|
| max_loss_per_trade_frac | 0.01 |
| floor_risk_frac | 0.0025 |
| earned_risk_frac | 0.01 |
| min_dte | 7 |
| max_dte | 45 |
| max_open_structures | 4 |
| max_structures_per_underlying | 1 |
| max_bid_ask_spread_frac | 0.15 |
| max_abs_spread | 0.1 |
| min_open_interest | 100 |
| min_p_profit | 0.55 |
| allowed_underlyings | ('SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA') |
| calib_min_resolved | 10 |
| calib_max_ece | 0.15 |
| calib_max_brier | 0.25 |
| calib_min_claim_accuracy | 0.99 |
