# Speaker Guide — Exercise 4: Joule Agent on the Golden Record

**~10 min.** Student doc: [`exercises/ex4`](../exercises/ex4/README.md)

## Goal
Create the `OTIF Risk Advisor` Joule agent grounded on `gold.otif_risk_enriched` and ask it OTIF-risk questions.

## Talking points
- The agent is **only as good as its grounding**. It answers *only* from the governed golden record — explainable and auditable, the opposite of an ungrounded chatbot.
- Every answer cites `ProductionOrder`, plant, `primary_root_cause`, `anomalous_work_centers`, and the figures — because the data carries them.
- The closing loop: change a Silver threshold in ex3 → the agent immediately reasons on better data. Grounding + lineage, not retraining.

## The 3 demo questions and what to expect
1. *"Which production orders are at HIGH risk right now, and why?"* → agent lists orders where `is_at_risk = TRUE` / `risk_tier = 'High Risk'`, with root cause + work centers.
2. *"For 'Final Acceptance Failure' orders, which work centers, and what's their OEE / unplanned downtime?"* → forces the **SAP + non-SAP** combination (SAP root cause + MES `avg_oee`, `unplanned_downtime_minutes`). This is the money shot.
3. *"Rank the top 5 to intervene on by otif_risk_score."* → prioritized, explained list.

## Supplementary (optional) — mes_synthetic_data
If asked "can we recover?", point the agent at `data/mes_synthetic_data` (shopfloor OEE / free-capacity / proposed recovery lots). Keep it clearly **separate** from the governed OTIF record — it's planning context, not a BDC data product. Don't over-reach: it's a different frozen scenario (Smyle, MAT000-7B).

## Gotchas
- If the agent answers from general knowledge instead of the data, the grounding instruction or the Dremio tool binding is wrong. Re-paste the system prompt from the exercise verbatim.
- Keep questions scoped to columns that exist in `gold.otif_risk_enriched` — out-of-scope asks invite hallucination; use them to demo the "if the data doesn't support it, say so" behavior.

## Transition
"Trustworthy answers, grounded and cited. Let's prove where every answer comes from."