# lablab.ai paste pack — Underwrite (Alpaca AI Trading Agents Hackathon)

Submit from: https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon (Submit / Manage submission). Deadline re-read in the browser first.

**Project title:** Underwrite: the options agent that has to earn its own position size

**Short description (≤255 chars):**
An autonomous options desk on Alpaca where an LLM proposes, a deterministic gate re-prices and sizes, orders go through Alpaca's MCP server, an auditor re-checks every claim through the Alpaca CLI, and position size is earned by measured calibration.

**Long description (≥100 words):**
Every trading agent claims it manages risk. Underwrite measures whether its own claims are true and refuses to size up until they are.

A Gemini strategist (Google ADK) sees the market only through Alpaca's MCP server, filtered to read-only tools. Each cycle it proposes one defined-risk options structure (bull put, bear call, iron condor, debit spread) with a stated probability of profit and the tool outputs it relied on, or declines.

A deterministic gate re-quotes every leg through a separate client, recomputes max loss itself, and enforces the rules the write-up quotes: max loss ≤ 1% of equity, 7–45 DTE, bid/ask ≤ 15% of mid, open interest ≥ 100, one structure per underlying, four at most, liquid underlyings only. Exits are mechanical: take profit at 50% of credit, stop at 2× credit, close at 2 DTE.

The executor places the multi-leg order through the MCP server's place_option_order; the server's reply is recorded verbatim as a claim. An auditor then asks the Alpaca CLI, a separate binary with its own HTTP client, what the account actually holds, and reconciles it. Claimed filled but not filled is a silent failure, and one silent failure freezes sizing at the floor.

Position size is a function of measured calibration: Brier score and expected calibration error of stated probabilities against realised outcomes, reported-vs-verified claim accuracy, and silent-failure count. The budget unlocks from 0.25% to 1% of equity only after ten resolved structures with ECE ≤ 0.15, Brier ≤ 0.25 and 99% claim accuracy. During the hackathon the desk trades at the floor, and the published report says so rather than hiding it.

Everything is an append-only JSONL ledger, and the hosted report is generated from it and nothing else: every order id appears in both a claim and a CLI audit, every gate decision lists its reasons, every proposal lists its MCP tool calls. Account: paper account PA3TNFFGMVEM, created for this hackathon on 2026-09-03 19:00 UTC with $100,000. Two live sessions (US close Sep 3, US open Sep 4): 10 orders through the MCP server, 10 of 10 claims reconciled by the CLI audit, 0 silent failures. Session 1: SPY 765/760, NVDA 220/215, TSLA 360/355 and TSLA 355/350 bull put spreads filled; AAPL and MSFT day orders expired at the bell, recorded as such. Session 2 with the second-opinion committee (Claude Sonnet 4.5 proposes, Gemini 2.5 Pro reviews the exact legs): 10 proposals, 7 reviews (2 agreed, 5 vetoed in writing — open interest below 100, a 378-DTE expiry, unrealistic credits), 2 reasoned declines, gate 2 accepts / 5 rejects; AAPL 9/25 filled, QQQ 9/25 working at the close; the desk's own policy check caught a duplicate TSLA structure that slipped in while the first order was still working and put in a closing order on the record. $1,959 at risk, 1x each at the floor, because 0 of the 10 resolved structures needed to earn the full budget exist yet; equity $99,679.50 (mark-to-market on fresh credit spreads).

**Technology tags:** Alpaca, Gemini, Google ADK, MCP, Python, Streamlit-free static report (Vercel)

**Category tags:** Finance, Agents, Trading

**Cover image (16:9):** docs/cover.png

**Video (≤5 min, MP4):** docs/underwrite-fallback.mp4 (2:49, narrated deck + live dashboard) — or Carson's own recording if made

**Slide deck (PDF):** docs/deck.pdf (filled with both sessions' numbers)

**GitHub (public):** https://github.com/rodriguescarson/underwrite (make public: `gh repo edit rodriguescarson/underwrite --visibility public --accept-visibility-change-consequences`)

**Application URL:** https://underwrite-ashen.vercel.app/dashboard.html (report: https://underwrite-ashen.vercel.app)

**One-page write-up:** docs/WRITEUP.md (attach as PDF or paste)

**Social links (up to 5):** the three posts in docs/POSTS.md, X + LinkedIn
