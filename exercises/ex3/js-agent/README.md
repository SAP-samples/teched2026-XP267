# Exercise 3 - Build a Joule Agent on the Golden Record

In this exercise you deploy a Joule Studio agent that answers order-fulfillment questions
in plain language. The agent is grounded on the knowledge graph you built in the Ontology
Manager (Narwhal), which sits on top of the golden records from the earlier exercises.

You deploy it the pro-code way: use the `jl` CLI to push a prepared agent solution, then
test it in a conversation.

> The agent's code (`exercises/ex3/js-agent/solution/`) is ready to deploy. Its connection to
> the Ontology Manager — the MCP tools and authentication — is already wired, so you can focus
> on deploying it and asking questions. See [`solution/README.md`](solution/README.md) for the
> details.

## Prerequisites

- The `jl` CLI (`npm install -g @sap/joule-studio-cli@latest`) and Node.js 22–26.
- The Ontology Manager (Narwhal) golden-record ontology published for your lab tenant.

## Exercise 3.1 Deploy the agent

When you finish these steps, the `Order Fulfillment Advisor` agent is running in your Joule
Studio landscape.

1. Log in to Joule Studio with the `jl` CLI, using the sign-in URL for your lab landscape:
```bash
jl login '<your-landscape-sign-in-url>'
```

2. Add your tenant's Narwhal connection details. Open
   `solution/assets/order-fulfillment-advisor/app/narwhal_tools.py` and replace the
   placeholder values in the `_CONFIG` dict with the values for your lab tenant:
```python
_CONFIG = {
    "NARWHAL_MCP_BASE": "https://...",                         # Narwhal MCP host
    "NARWHAL_TOKEN_URL": "https://.../oauth/token",            # XSUAA token endpoint
    "NARWHAL_CLIENT_ID": "sb-...",                             # OAuth client id
    "NARWHAL_CLIENT_SECRET": "...",                            # OAuth client secret
    "NARWHAL_MCP_PATH": "mcp",
}
```

   > The agent reads these values directly — if the placeholders are left in, it deploys but
   > every question fails because it can't reach Narwhal.

3. From the solution directory, validate and deploy the agent:
```bash
cd exercises/ex3/js-agent/solution
jl solution validate      # expect: Validation passed.
jl solution deploy --wait --force
```
<br>![Deploying the Order Fulfillment Advisor with the jl CLI](/exercises/ex3/js-agent/images/03_01_0010.png)

   > The build runs on SAP's managed builder and can take a few minutes. When the command
   > prints `✓ Deployed`, the agent is ready to test in Joule Studio.

## Exercise 3.2 Ask the agent fulfillment questions

Open your agent in Joule Studio → Develop → "Try Your Agent" and ask it questions in plain
language.

1. First, check that it reads from the governed data — it should look up the ontology before
   it answers:
```text
What data can you help me with? List the ontologies, then describe what entities
and attributes are available.
```
<br>![Agent listing the ontology and its entities](/exercises/ex3/js-agent/images/03_02_0010.png)

2. Ask a question that makes it query the knowledge graph for real rows:
```text
Which customers have sales orders, and for the materials they ordered, what is the
supply coverage by plant? Cite the customer, material, and plant.
```

3. Ask the fulfillment-risk question:
```text
Which customers or materials look under-covered — demand without matching supply —
and why?
```

   > The agent answers only from the knowledge graph: it looks up the ontology, reads its
   > schema, and runs SPARQL, so every answer traces back to the governed data. When the data
   > doesn't support an answer, it says so instead of guessing.

## How it connects (for the curious)

The agent calls the Ontology Manager's MCP server as a set of tools (`list_ontologies`,
`get_ontology_schema`, `execute_sparql`) and authenticates with its own OAuth client. The
Ontology Manager turns the SPARQL into live queries over the golden-record views. For the full
setup, see [`solution/README.md`](solution/README.md).

## Screenshots to capture (for authors)

- [ ] `03_01_0010.png` — `jl solution deploy` succeeding
- [ ] `03_02_0010.png` — Agent listing the ontology / entities in Try Your Agent
- [ ] `03_02_0020.png` — Agent answering a fulfillment-coverage question with citations

## Summary

You deployed an AI agent that answers order-fulfillment questions from the governed knowledge
graph built on your golden records. Every answer is grounded in retrieved data and traces back
through the Ontology Manager to the underlying SAP data.

Return to - [Overview](../../../README.md)
