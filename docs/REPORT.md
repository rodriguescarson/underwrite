# Underwrite — desk report
_Generated 2026-09-03T19:14+00:00 from the ledger and nothing else. Action channel: Alpaca MCP server (`uvx alpaca-mcp-server`). Audit channel: Alpaca CLI 0.0.14. Strategist: Gemini via Google ADK, read-only MCP tools._

## The idea in one line
The strategist proposes, a deterministic gate re-prices and sizes, the executor acts through Alpaca's MCP server, an independent auditor re-checks every claim through the Alpaca CLI, and position size is earned by measured calibration rather than granted by confidence.

## How to verify this report
Every order id below appears twice: once in the executor's claim (what the MCP server returned) and once in the CLI audit (what the account actually holds). Every gate decision lists its reasons. Every proposal lists the MCP tool calls it made. The raw ledger is at `ledger.json` next to this page; the code is at github.com/rodriguescarson/underwrite.

## Account (as the CLI sees it)
| first snapshot | equity | latest snapshot | equity | account |
|---|---|---|---|---|
| 2026-09-03T19:03:09+00:00 | 100000 | 2026-09-03T19:13:09+00:00 | 99997.95 | PA3TNFFGMVEM |

## Calibration — the numbers that set position size
| claims | audited | claim accuracy | silent failures | resolved | wins | Brier | ECE | risk/trade | status |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 2 | 1.0 | 0 | 0 | 0 | None | None | 0.25% | floor |

Gate verdict: only 0/10 structures resolved; ECE undefined; Brier undefined

## Claims vs. audits (executor said → CLI observed)
| time | kind | underlying | structure | qty | limit | claimed | observed | match | order |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-03T19:08:07 | open | SPY | bull_put_spread | 1 | -0.64 | pending_new | filled | ✔ | 49ce68dd |
| 2026-09-03T19:13:39 | open | NVDA | bull_put_spread | 1 | -0.96 | pending_new | filled | ✔ | 927683d5 |

## Gate decisions
| time | verdict | qty | reasons |
|---|---|---|---|
| 2026-09-03T19:08:05 | accept | 1 | defined risk: width 5.00 - credit 0.66 = 4.34/share<br>floor sizing 1x: budget $250 (0.25% of equity, calibration not yet earned) &lt; max loss $434; the 1% hard cap still holds |
| 2026-09-03T19:13:37 | accept | 1 | defined risk: width 5.00 - credit 0.98 = 4.01/share<br>floor sizing 1x: budget $250 (0.25% of equity, calibration not yet earned) &lt; max loss $402; the 1% hard cap still holds |

## Strategist proposals
| time | model | tool calls | structure | p_profit | thesis |
|---|---|---|---|---|---|
| 2026-09-03T19:05:02 | none | 0 | unparsed | — |  |
| 2026-09-03T19:08:03 | gemini-2.5-flash | 5 | bull_put_spread | 0.7678 | SPY is expected to remain above 765.00 until the September 11, 2026 expiration. The short 765 put has a delta of -0.2322, indicating a probability of approximately 76.78% that SPY will stay above 765 at expiration, allow |
| 2026-09-03T19:10:28 | none | 0 | unparsed | — |  |
| 2026-09-03T19:13:35 | openrouter/google/gemini-2.5-flash | 5 | bull_put_spread | 0.65 | NVDA has shown a strong upward trend in the last two days. I expect this upward momentum to continue or at least hold above 220, making a bull put spread a suitable strategy. |

## Resolved structures
_none resolved yet — provisional MTM is in the latest snapshot below_

## Open positions, mark-to-market (latest CLI snapshot)
| symbol | qty | avg entry | market value | unrealized P&L |
|---|---|---|---|---|
| SPY260911P00760000 | 1 | 1.06 | 105 | -1 |
| SPY260911P00765000 | -1 | 1.75 | -176 | -1 |

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
