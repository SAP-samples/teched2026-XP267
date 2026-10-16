"""SAP BDC Ontology Manager MCP tools for the Churn Advisor agent.

Exposes the SAP BDC Ontology Manager knowledge-graph tools to the agent by
calling its MCP server over HTTP, authenticating with an XSUAA
client-credentials token.

The MCP server is served at `<BDC_ONTOLOGY_MCP_BASE>/mcp/`, accepts a
`Authorization: Bearer <token>` header, and replies with SSE
(`event: message` / `data: {...}`). Tools exposed here:
    list_ontologies, get_ontology_schema, execute_sparql

Connection settings are the `_CONFIG` literals below:
    BDC_ONTOLOGY_MCP_BASE        MCP host, e.g. https://<host>.hana.ondemand.com
    BDC_ONTOLOGY_TOKEN_URL       XSUAA token endpoint (…/oauth/token)
    BDC_ONTOLOGY_CLIENT_ID
    BDC_ONTOLOGY_CLIENT_SECRET
    BDC_ONTOLOGY_MCP_PATH        MCP mount path, default "mcp"
"""
from __future__ import annotations

import json
import logging
import os
import ssl
import time

import httpx
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import Field, create_model

logger = logging.getLogger(__name__)

_ACCEPT = "application/json, text/event-stream"

# Tool results are re-sent to the LLM on every subsequent turn, so a large
# SPARQL result slows every following completion and can push the whole agent
# loop past the "Try Your Agent" request deadline (~50s). Cap the result size
# the agent sees; override with MCP_MAX_RESPONSE_CHARS if an agent genuinely
# needs larger payloads.
MCP_MAX_RESPONSE_CHARS = int(os.environ.get("MCP_MAX_RESPONSE_CHARS", 12_000))

# ---------------------------------------------------------------------------
# SAP BDC Ontology Manager connection settings. Fill in the placeholders for
# your lab tenant before deploying.
# ---------------------------------------------------------------------------
_CONFIG = {
    "BDC_ONTOLOGY_MCP_BASE": "<BDC_ONTOLOGY_MCP_BASE>",
    "BDC_ONTOLOGY_TOKEN_URL": "<BDC_ONTOLOGY_TOKEN_URL>",
    "BDC_ONTOLOGY_CLIENT_ID": "<BDC_ONTOLOGY_CLIENT_ID>",
    "BDC_ONTOLOGY_CLIENT_SECRET": "<BDC_ONTOLOGY_CLIENT_SECRET>",
    "BDC_ONTOLOGY_MCP_PATH": "mcp",
}

# Tool catalogue: name -> (description, {arg_name: (type, required, description)})
_TOOLS: dict[str, tuple[str, dict]] = {
    "list_ontologies": (
        "List all ontologies available in the SAP BDC Ontology Manager. "
        "Returns id (UUID), name, description.",
        {},
    ),
    "get_ontology_schema": (
        "Fetch the RDF/XML schema (classes, properties, relationships) for one ontology. "
        "Call once per conversation and reuse; needed before writing SPARQL.",
        {"ontology_id": (str, True, "The ontology UUID (not its name).")},
    ),
    "execute_sparql": (
        "Run a SPARQL SELECT query against an ontology's knowledge graph and return rows. "
        "Only SELECT; use IRIs/prefixes from the schema.",
        {
            "ontology_id": (str, True, "The ontology UUID."),
            "sparql": (str, True, "A SPARQL SELECT query."),
        },
    ),
}

# Process-wide token cache (agent is long-lived; token is ~12h).
_token: str | None = None
_token_exp: float = 0.0


def _config(name: str) -> str:
    """Return a connection setting, erroring if it is still a placeholder."""
    val = (_CONFIG.get(name) or "").strip()
    if not val or val.startswith("<"):
        raise RuntimeError(f"{name} is not configured in bdc_ontology_tools._CONFIG.")
    return val


def _ssl_context() -> ssl.SSLContext:
    """Build an SSL context that trusts the usual public roots.

    Starts from the default context (which honours SSL_CERT_FILE / SSL_CERT_DIR
    when set) and additionally loads certifi's roots and the OS trust store, so
    TLS verification works both locally and when deployed. Each extra source is
    best-effort and never breaks the context.
    """
    ctx = ssl.create_default_context()  # honours SSL_CERT_FILE / SSL_CERT_DIR when set
    for loader in (
        lambda: ctx.load_verify_locations(cafile=__import__("certifi").where()),
        ctx.load_default_certs,  # OS trust store (/etc/ssl/certs)
    ):
        try:
            loader()
        except Exception:  # pragma: no cover - best effort
            pass
    # Also honour an explicit SSL_CERT_FILE if one is set in the environment.
    cert_file = os.environ.get("SSL_CERT_FILE")
    if cert_file and os.path.exists(cert_file):
        try:
            ctx.load_verify_locations(cafile=cert_file)
        except Exception:  # pragma: no cover
            pass
    return ctx


def _client() -> httpx.Client:
    # trust_env=True lets httpx honour SSL_CERT_FILE/REQUESTS_CA_BUNDLE/proxy env too.
    return httpx.Client(timeout=60, verify=_ssl_context(), trust_env=True)


def _get_token(http: httpx.Client) -> str:
    global _token, _token_exp
    now = time.time()
    if _token and now < _token_exp - 60:
        return _token
    resp = http.post(
        _config("BDC_ONTOLOGY_TOKEN_URL"),
        data={
            "grant_type": "client_credentials",
            "client_id": _config("BDC_ONTOLOGY_CLIENT_ID"),
            "client_secret": _config("BDC_ONTOLOGY_CLIENT_SECRET"),
        },
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    payload = resp.json()
    _token = payload["access_token"]
    _token_exp = now + float(payload.get("expires_in", 3600))
    logger.info("Minted XSUAA token (expires_in=%ss)", int(payload.get("expires_in", 3600)))
    return _token


def _mcp_url() -> str:
    base = _config("BDC_ONTOLOGY_MCP_BASE").rstrip("/")
    path = _config("BDC_ONTOLOGY_MCP_PATH").strip("/")
    return f"{base}/{path}/"


def _truncate(text: str) -> str:
    """Bound a tool result to MCP_MAX_RESPONSE_CHARS.

    A SPARQL SELECT can return far more rows than the question needs; the full
    payload then rides along in context on every later LLM turn. Cut at the last
    newline before the limit so a row isn't split mid-way, and append a marker so
    the model knows the result was clipped and should narrow its query.
    """
    if len(text) <= MCP_MAX_RESPONSE_CHARS:
        return text
    window = text[:MCP_MAX_RESPONSE_CHARS]
    cut = window.rfind("\n")
    if cut > 0:
        window = window[:cut]
    return (
        window
        + "\n\n[result truncated — too many rows. Add a tighter LIMIT or more "
        "selective FILTERs to the SPARQL query and run it again.]"
    )


def _call(tool_name: str, arguments: dict) -> str:
    """Call an MCP tool and return the tool result as a JSON string."""
    with _client() as http:
        token = _get_token(http)
        resp = http.post(
            _mcp_url(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": _ACCEPT,
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
        )
    resp.raise_for_status()
    # SSE: pull the `data:` line; else plain JSON.
    raw = None
    for line in resp.text.split("\n"):
        if line.startswith("data:"):
            raw = json.loads(line[5:])
            break
    if raw is None:
        raw = resp.json()
    content = raw.get("result", {}).get("content", [])
    if content:
        return _truncate(content[0].get("text", json.dumps(raw)))
    return _truncate(json.dumps(raw))


def _make_tool(name: str, description: str, arg_spec: dict) -> BaseTool:
    field_defs: dict = {}
    for arg_name, (py_type, required, arg_desc) in arg_spec.items():
        if required:
            field_defs[arg_name] = (py_type, Field(description=arg_desc))
        else:
            field_defs[arg_name] = (py_type, Field(default=None, description=arg_desc))
    args_schema = create_model(f"{name}_args", **field_defs) if field_defs else create_model(f"{name}_args")

    async def _run(**kwargs) -> str:
        return _call(name, {k: v for k, v in kwargs.items() if v is not None})

    return StructuredTool(
        name=name,
        description=description,
        args_schema=args_schema,
        coroutine=_run,
    )


async def get_mcp_tools() -> list[BaseTool]:
    """Return LangChain tools backed by the SAP BDC Ontology Manager MCP server."""
    return [_make_tool(name, desc, spec) for name, (desc, spec) in _TOOLS.items()]
