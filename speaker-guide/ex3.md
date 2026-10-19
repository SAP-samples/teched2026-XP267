# Speaker Guide — Exercise 3: Joule Agent on the Golden Record

**~10 min.** Student docs: [`exercises/ex3/joule-skill`](../exercises/ex3/joule-skill/README.md) (Joule skill) and [`exercises/ex3/js-agent`](../exercises/ex3/js-agent/README.md) (coded agent).

## Goal
Ground a Joule agent/skill (the `churn-advisor`) on the `Customer_Churn_Ontology` built in Exercise 2 and ask it churn & delivery questions. The agent reasons over the ontology (via `list_ontologies` / `get_ontology_schema` / `execute_sparql`), which sits on the CRM 360 golden records (`v_customer_otif` + `v_crm_account_resolved`) from Exercise 1. OTIF manufacturing (`otif_risk`) is optional secondary context.

## Talking points
- The agent is only as good as its grounding. It answers *only* from the governed ontology / knowledge graph — explainable and auditable, the opposite of an ungrounded chatbot.
- It grounds itself once, up front: pins the ontology UUID, caches the RDF/XML schema, writes SPARQL from the actual class and property names — it never invents fields or answers from memory.
- The closing loop: change a threshold in Exercise 1 → the view updates → the ontology and agent immediately reason on better data. Grounding + lineage back to BDC data products, not retraining.

## The demo questions and what to expect
1. *"What data can you help me with? List the ontology, then describe its entities."* → the agent lists the `Customer_Churn_Ontology` and its concepts rather than answering from general knowledge — proof it grounds first.
2. *"Which at-risk accounts have the worst delivery performance (lowest OTIF), and why?"* → a prioritized list resolved by SPARQL over the knowledge graph, citing `churn_risk`, `otif_pct`, open cases — the churn ↔ delivery link made answerable.
3. *(Secondary / OTIF)* *"Which production orders are at HIGH risk of missing OTIF, and why?"* → only if the OTIF manufacturing context was attached; shows the agent spans both golden records.

## Gotchas
- If the agent answers from general knowledge instead of the graph, the grounding instruction (SKILL.md) or the Ontology Manager tool binding is wrong — re-check the skill is enabled and re-paste the `@ontology-manager-skill use the Customer_Churn_Ontology…` opener verbatim.
- All tools require the ontology **UUID**, not its name — never pass a name string as `ontology_id`.
- Keep questions scoped to concepts that exist in the ontology — out-of-scope asks invite hallucination; use them to demo the "if the data doesn't support it, say so" behavior.

## Transition
"Trustworthy, cited answers on a governed ontology sourced from BDC data products. That's the session."
