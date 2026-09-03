# Underwrite — video script (≤5 min; target 3:30). Record QuickTime at 1440×900, cursor visible, no music.

| t | On screen | Say |
|---|---|---|
| 0:00–0:20 | Title slide of deck.pdf | "Underwrite: the options agent that has to earn its own position size. Every trading agent in this hackathon claims it manages risk. This one measures whether its own claims are true, and won't size up until they are." |
| 0:20–1:00 | Deck slides 2–4 (problem, pipeline, two channels) | "An LLM strategist sees the market only through Alpaca's MCP server, read-only. It proposes one defined-risk spread with a stated probability of profit. A deterministic gate re-quotes every leg through a second client, recomputes max loss, enforces 1% of equity. The executor places the order through the MCP server. Then an auditor asks the Alpaca CLI, a separate binary, what the account actually holds. MCP acts, CLI audits." |
| 1:00–2:00 | Hosted report: account snapshot, claims-vs-audits table | "This is tonight's session on a paper account created for the hackathon, reset to $100,000. Every row here is a ledger line. Executor said → CLI observed. [N] claims, [N] matched, zero silent failures." |
| 2:00–2:40 | Gate decisions table, one rejection expanded | "The gate refused [K] proposals, each with a sentence a human can read: bid-ask too wide, DTE outside 7–45, stated edge below 0.55. Sizing stayed at the floor: 0.25% of equity per structure, because zero of the ten resolved trades needed to earn the 1% budget exist yet. The report says so on page one." |
| 2:40–3:10 | Terminal: `underwrite audit` then `cat ledger/orders.jsonl | head -1` and the matching audits line | "Two channels, one truth. The order id in the executor's claim is the same id the CLI returns, with the fills the CLI saw, not the ones the agent remembers." |
| 3:10–3:30 | Deck slide 7–8 (business value, verify) | "Calibration-gated sizing is the missing primitive for agent-first brokerage: the first question any allocator asks an agent is how do you know it does what it says. Repo and report links are in the submission. Thanks to lablab and Alpaca." |

Export MP4 (H.264). Upload with the PDF deck and cover.png.
