# Narration per deck slide (fallback video). One paragraph per slide, in order.

1. Underwrite is the options agent that has to earn its own position size. Every trading agent in this hackathon claims it manages risk. This one measures whether its own claims are true, and it will not size up until they are.

2. The problem is not a bad trade. It is a confident report that does not match the account. Language models state probabilities that are not calibrated, then size trades from that confidence, and an order placed by a tool call is a claim, not a fact. Nothing checks it.

3. Underwrite is a pipeline of separate parts. A strategist proposes one defined-risk options structure with a stated probability of profit. A second model reviews the exact legs and must agree. A deterministic gate re-prices every leg itself and enforces one percent of equity, seven to forty-five days to expiration, liquidity, and one structure per underlying. The executor acts. An auditor checks. Position size comes from measured calibration.

4. Two channels, one truth. The strategist and the executor work through Alpaca's MCP server. The auditor works through the Alpaca CLI, a separate binary with its own HTTP client, using the same keys and nothing else in common. What the executor says happened is a claim. What the CLI sees is the record. The account was created for this hackathon and funded with one hundred thousand dollars.

5. In the first live session the desk ran nine cycles unattended. The gate accepted six proposals and refused one in writing, an Apple spread with open interest below the minimum. Six orders went through the MCP server. Four filled, two day orders expired at the bell, and the auditor recorded exactly that. Six of six claims were consistent with the CLI. Zero silent failures. Fifteen hundred dollars at risk, one contract each, at the floor.

6. Calibration is how size is earned. Brier score and expected calibration error of the stated probabilities against realised outcomes, plus how often the executor's claims matched the account. The budget unlocks from a quarter of a percent to one percent of equity only after ten resolved structures. The desk has zero. So it stayed at the floor, and the report says so on its first line instead of hiding it.

7. This is the missing primitive for agent-first brokerage. The first question any allocator asks an agent is: how do you know it does what it says. Underwrite is that answer as infrastructure. It is strategy-agnostic, it sells to desks running language-model agents and to fintechs on Alpaca's Broker API, and every number in it can be checked.

8. Everything is a ledger line. Every order id appears in an executor claim and in a CLI audit. Every gate decision lists its reasons. Every proposal lists its tool calls. The code and the live report are linked in the submission. Thank you to lablab and Alpaca.
