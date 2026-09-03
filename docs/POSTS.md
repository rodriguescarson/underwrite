# Build-in-public posts — Underwrite (lablab.ai × Alpaca)

Corpus note: `corpus/carson-en/` is empty, so these follow the voice rules (tight, numbers, named practitioners, no emoji, no em dashes, hashtags) without a profile to match against. Post from your own accounts; up to 5 links go on the lablab submission.

## Post 1 — kickoff (X)

Building for the @lablabai x @AlpacaHQ hackathon this week.

Every trading agent claims it manages risk. Mine has to prove it.

Underwrite: an LLM proposes an options spread with a stated P(profit). A deterministic gate re-prices every leg and sizes the trade from the agent's measured calibration, not its confidence.

Orders go through Alpaca's MCP server. An auditor checks every claim through the Alpaca CLI. Two channels, one truth.

Position size starts at 0.25% of equity and only reaches 1% after 10 resolved trades with ECE under 0.15. Most agents never get there. That is the point.

#AIagents #OptionsTrading #Alpaca #MCP #lablabai #BuildInPublic

## Post 1 — kickoff (LinkedIn)

I am building an options trading agent for the lablab.ai x Alpaca hackathon this week, and the design decision that matters is not the strategy.

It is that the agent does not get to decide how big it trades.

The strategist is a Gemini agent whose only market access is Alpaca's MCP server, filtered to read-only tools. It proposes one defined-risk spread per cycle with a stated probability of profit, or declines.

A deterministic gate then re-quotes every leg through a separate client, recomputes max loss itself, and sizes the position from the agent's measured calibration: Brier score and expected calibration error of its stated probabilities against realised outcomes, plus how often what it reported matched what the account actually showed.

The executor acts through the MCP server. An auditor re-checks every order through the Alpaca CLI, a separate binary with its own HTTP client. "Claimed filled, not filled" is a silent failure, and one of them freezes sizing at the floor.

Floor is 0.25% of equity per structure. The 1% budget unlocks only after 10 resolved trades with ECE under 0.15. In a 7-day hackathon the desk will stay at the floor the whole time, and the report will say so. An agent that has not proven it can predict its own outcomes should not be trading size.

Ledger, gate reasons and every MCP tool call are published. @lablabai @AlpacaHQ

#AIagents #OptionsTrading #Alpaca #MCP #Calibration #BuildInPublic

## Post 2 — the setback (X)

Setback from the Underwrite build for @lablabai x @AlpacaHQ:

Alpaca's MCP server (FastMCP 3.4) and Google ADK 2.8 disagree about the mcp package. ADK imports mcp.shared.session.ProgressFnT, mcp 2.1 removed it. Pinning mcp<2 fixed it in one line, after 40 minutes of reading tracebacks.

Lesson: when two agent frameworks share a protocol library, pin the protocol library first.

Second lesson, cheaper: the risk gate rejected my own test trade because a $0.50 wing had an 18% bid/ask spread. Correct behaviour. Cheap far-OTM legs need an absolute spread rule ($0.10) next to the relative one.

#AIagents #MCP #Alpaca #OptionsTrading #lablabai

## Post 2 — the setback (LinkedIn)

Two things broke while building Underwrite for the lablab.ai x Alpaca hackathon, and both are worth writing down.

1. Alpaca's MCP server runs on FastMCP 3.4. Google ADK 2.8 imports mcp.shared.session.ProgressFnT. The mcp package hit 2.1 last week and removed that module. The fix was one line, mcp<2, and it took 40 minutes to find because the traceback pointed at ADK, not at the dependency both sides share. When two agent frameworks share a protocol library, pin the protocol library first.

2. My own risk gate rejected my own test trade. A $0.50 put wing had a 10 cent bid/ask, which is 18% of mid, over the 15% cap. That is the gate doing its job; a relative spread rule punishes cheap legs. The fix was an absolute alternative: accept if the spread is under $0.10 in dollars. Every rule in the gate is now a sentence in the report, so a judge can read why a trade was refused.

Neither is clever. Both are the kind of thing that decides whether an autonomous agent runs unattended at 7pm or not. @lablabai @AlpacaHQ

#AIagents #MCP #Alpaca #OptionsTrading #Calibration #BuildInPublic

## Post 3 — first live session (X)

First live session for Underwrite, @lablabai x @AlpacaHQ hackathon, on a fresh $100k paper account:

→ 4 strategist cycles, 2 proposals accepted by the gate (2 cycles produced nothing: Gemini quota hit, rerouted through OpenRouter mid-session)
→ 2 bull put spreads opened through Alpaca's MCP server (SPY 765/760, NVDA 220/215), both confirmed by the CLI audit: 2/2 claims matched, 0 silent failures
→ stated P(profit) 0.65 and 0.77, $836 at risk total, sized 1x each at the floor

Sizing stayed at the floor. 0 of 10 required resolved trades for calibration. The report says so, on purpose.

Ledger and report: https://underwrite-ashen.vercel.app

#AIagents #OptionsTrading #Alpaca #MCP #lablabai

## Post 3 — first live session (LinkedIn)

Underwrite traded its first live session for the lablab.ai x Alpaca hackathon, on a paper account created for it and reset to $100,000.

What happened, from the ledger, not from memory:

→ The strategist ran 4 cycles; 2 produced proposals (SPY and NVDA) and the gate accepted both after re-pricing every leg itself: width 5.00, credits 0.66 and 0.98 at mid, max loss $434 and $402. The other 2 cycles produced nothing because the Gemini key ran out of quota mid-session; the desk was rerouted through OpenRouter without stopping.
→ 2 defined-risk spreads were opened through Alpaca's MCP server. The auditor re-read every order through the Alpaca CLI: 2 of 2 claims matched, 0 silent failures.
→ Stated probability of profit: 0.77 (SPY, from the short strike's delta) and 0.65 (NVDA). $836 at risk in total, 1x each.

Position size stayed at the floor, 0.25% of equity per structure, because 0 of the 10 resolved trades needed for calibration exist yet. That number is on the first page of the report. Most agent demos would hide it. The whole point of this one is that it cannot.

Report: https://underwrite-ashen.vercel.app · Code: github.com/rodriguescarson/underwrite @lablabai @AlpacaHQ

#AIagents #OptionsTrading #Alpaca #MCP #Calibration #BuildInPublic
