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

Everything is an append-only JSONL ledger, and the hosted report is generated from it and nothing else: every order id appears in both a claim and a CLI audit, every gate decision lists its reasons, every proposal lists its MCP tool calls. Account: paper account PA3TNFFGMVEM, created for this hackathon on 2026-09-03 19:00 UTC with $100,000. First live session (US close, Sep 3): 2 defined-risk spreads opened through the MCP server (SPY 765/760, NVDA 220/215), both confirmed filled by the CLI audit, 2/2 claims matched, 0 silent failures, $836 at risk, sized 1x at the floor because 0 of the 10 resolved structures needed to earn the full budget exist yet.

**Technology tags:** Alpaca, Gemini, Google ADK, MCP, Python, Streamlit-free static report (Vercel)

**Category tags:** Finance, Agents, Trading

**Cover image (16:9):** docs/cover.png

**Video (≤5 min, MP4):** intro → PDF deck walkthrough → live report + ledger + a gate rejection + a CLI audit matching an MCP order

**Slide deck (PDF):** docs/deck.pdf (regenerate after the session: fill the {{...}} numbers in docs/deck.html, then run the headless-Chrome command in the README)

**GitHub (public):** https://github.com/rodriguescarson/underwrite (make public: `gh repo edit rodriguescarson/underwrite --visibility public --accept-visibility-change-consequences`)

**Application URL:** https://underwrite-ashen.vercel.app

**One-page write-up:** docs/WRITEUP.md (attach as PDF or paste)

**Social links (up to 5):** the three posts in docs/POSTS.md, X + LinkedIn
