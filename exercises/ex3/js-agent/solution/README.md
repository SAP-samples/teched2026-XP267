# Order Fulfillment Advisor — Joule Studio agent on SAP BDC Ontology Manager

A pro-code Joule Studio A2A agent that answers order-fulfillment / supply-coverage
questions grounded on an SAP BDC Ontology Manager knowledge graph of customers,
sales orders, and material supply coverage. This is the deployable solution behind the
"Build a Joule Agent on the Golden Record" workshop step.

## How it connects

The agent reaches the knowledge graph through the SAP BDC Ontology Manager MCP server:

1. Ontology Manager tools. `app/bdc_ontology_tools.py` calls the MCP server over HTTP
   (JSON-RPC, SSE responses) and exposes its tools as LangChain tools:
   `list_ontologies`, `get_ontology_schema`, `execute_sparql`.
2. XSUAA authentication. The agent mints an XSUAA client-credentials token and
   sends it as a bearer token on each MCP call. Connection settings live in the
   `_CONFIG` dict in `bdc_ontology_tools.py`.

```
Try Your Agent ──▶ order-fulfillment-advisor (Joule Studio agent)
                      │  app/bdc_ontology_tools.py
                      │   • XSUAA client-credentials → Bearer token
                      ▼
             POST <BDC_ONTOLOGY_MCP_BASE>/mcp/   (JSON-RPC: tools/call)
                      ▼
             BDC Ontology Manager MCP ──▶ SPARQL over the governed knowledge graph
```

## Layout

```
solution.yaml                              # solution: order-fulfillment-handson
assets/order-fulfillment-advisor/
  asset.yaml                               # type: agent, A2A, port 5000
  app/
    main.py  agent.py  agent_executor.py   # A2A server + agent
    bdc_ontology_tools.py                   # BDC Ontology Manager MCP tools + XSUAA auth
    jwt_context.py                          # per-request user-token helpers
  prebuilt_tests/                           # structure + server tests
```

## Credentials

Connection settings live in the `_CONFIG` dict in
`assets/order-fulfillment-advisor/app/bdc_ontology_tools.py`. Fill in the placeholders
with the values for your lab tenant.

| Setting                      | Meaning                                        |
| ---------------------------- | ---------------------------------------------- |
| `BDC_ONTOLOGY_MCP_BASE`      | Ontology Manager MCP host                      |
| `BDC_ONTOLOGY_TOKEN_URL`     | XSUAA token endpoint (`…/oauth/token`)         |
| `BDC_ONTOLOGY_CLIENT_ID`     | OAuth client id                                |
| `BDC_ONTOLOGY_CLIENT_SECRET` | OAuth client secret                            |
| `BDC_ONTOLOGY_MCP_PATH`      | MCP mount path (default `mcp`)                 |

## Deploy & test

```bash
jl solution validate
jl solution deploy --wait --force
```

Then test in Joule Studio → Develop → "Try Your Agent": ask it to list the
ontologies and describe their entities, then ask a supply-coverage question so it
has to query the knowledge graph.

## Local run

The agent is built with LangGraph, LiteLLM, and the SAP Cloud SDK (A2A protocol).
To run it locally, fill in the `_CONFIG` values in
`assets/order-fulfillment-advisor/app/bdc_ontology_tools.py`, then export your SAP AI Core
credentials:

```bash
export AICORE_CLIENT_ID="sb-..."
export AICORE_CLIENT_SECRET='...'
export AICORE_AUTH_URL="https://...authentication...hana.ondemand.com"
export AICORE_BASE_URL="https://api...hana.ondemand.com"
```

Create a virtual environment, install requirements, and run the agent:

```bash
cd assets/order-fulfillment-advisor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
python app/main.py
```

Run the tests with `pytest` from the same directory.
