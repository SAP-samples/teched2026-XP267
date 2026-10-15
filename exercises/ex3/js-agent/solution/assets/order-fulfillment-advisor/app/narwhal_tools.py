"""Narwhal MCP tools for the Order Fulfillment Advisor agent.

Exposes the SAP Ontology Manager (Narwhal) knowledge-graph tools to the agent by
calling Narwhal's MCP server over HTTP, authenticating with an XSUAA
client-credentials token.

The Narwhal MCP server is served at `<NARWHAL_MCP_BASE>/mcp/`, accepts a
`Authorization: Bearer <token>` header, and replies with SSE
(`event: message` / `data: {...}`). Tools exposed here:
    list_ontologies, get_ontology_schema, execute_sparql

Connection settings are the `_CONFIG` literals below:
    NARWHAL_MCP_BASE        Narwhal MCP host, e.g. https://<host>.hana.ondemand.com
    NARWHAL_TOKEN_URL       XSUAA token endpoint (…/oauth/token)
    NARWHAL_CLIENT_ID
    NARWHAL_CLIENT_SECRET
    NARWHAL_MCP_PATH        MCP mount path, default "mcp"
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

# ---------------------------------------------------------------------------
# Narwhal connection settings. Fill in the placeholders for your lab tenant
# before deploying.
# ---------------------------------------------------------------------------
_CONFIG = {
    "NARWHAL_MCP_BASE": "<NARWHAL_MCP_BASE>",
    "NARWHAL_TOKEN_URL": "<NARWHAL_TOKEN_URL>",
    "NARWHAL_CLIENT_ID": "<NARWHAL_CLIENT_ID>",
    "NARWHAL_CLIENT_SECRET": "<NARWHAL_CLIENT_SECRET>",
    "NARWHAL_MCP_PATH": "mcp",
}

# Tool catalogue: name -> (description, {arg_name: (type, required, description)})
_TOOLS: dict[str, tuple[str, dict]] = {
    "list_ontologies": (
        "List all ontologies available in Narwhal. Returns id (UUID), name, description.",
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
    """Return a Narwhal connection setting, erroring if it is still a placeholder."""
    val = (_CONFIG.get(name) or "").strip()
    if not val or val.startswith("<"):
        raise RuntimeError(f"{name} is not configured in narwhal_tools._CONFIG.")
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
        _config("NARWHAL_TOKEN_URL"),
        data={
            "grant_type": "client_credentials",
            "client_id": _config("NARWHAL_CLIENT_ID"),
            "client_secret": _config("NARWHAL_CLIENT_SECRET"),
        },
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    payload = resp.json()
    _token = payload["access_token"]
    _token_exp = now + float(payload.get("expires_in", 3600))
    logger.info("Minted Narwhal XSUAA token (expires_in=%ss)", int(payload.get("expires_in", 3600)))
    return _token


def _mcp_url() -> str:
    base = _config("NARWHAL_MCP_BASE").rstrip("/")
    path = _config("NARWHAL_MCP_PATH").strip("/")
    return f"{base}/{path}/"


def _call(tool_name: str, arguments: dict) -> str:
    """Call a Narwhal MCP tool and return the tool result as a JSON string."""
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
        return content[0].get("text", json.dumps(raw))
    return json.dumps(raw)


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
    """Return LangChain tools backed by the Narwhal MCP server."""
    return [_make_tool(name, desc, spec) for name, (desc, spec) in _TOOLS.items()]
