#!/usr/bin/env python3
"""Call an Ontology Manager MCP tool and return the result.

Usage:
    python3 ask_ontology_manager.py <tool_name> [arguments_json]

Examples:
    python3 ask_ontology_manager.py list_ontologies
    python3 ask_ontology_manager.py get_ontology_schema '{"ontology_id": "abc-123"}'
    python3 ask_ontology_manager.py execute_sparql '{"ontology_id": "abc-123", "sparql": "SELECT ..."}'
    python3 ask_ontology_manager.py ping

Reads the connector proxy URL from $API_ONTOLOGY_MANAGER_SKILL_AGENT (injected by the
Joule runtime from this skill's .sap-connectivity.json). Auth is handled automatically by the
BTP Destination proxy.

Timing is written to stderr:
  [timing] tool=get_ontology_schema duration_ms=1102
  [timing] tool=execute_sparql duration_ms=3094 backend_execution_ms=1703
"""

import argparse
import json
import os
import sys
import time

import requests
from requests.exceptions import RequestException

ENV_VAR = "API_ONTOLOGY_MANAGER_SKILL_AGENT"

DEBUG_ENV_VARS = [
    ENV_VAR,
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "no_proxy",
]

AVAILABLE_TOOLS = [
    "list_ontologies",
    "get_ontology_schema",
    "execute_sparql",
    "list_business_actions",
    "execute_business_action",
]


def emit_error(kind: str, message: str, **extra) -> None:
    payload = {"ok": False, "error": kind, "message": message, **extra}
    print(json.dumps(payload, indent=2))
    print(f"{kind}: {message}", file=sys.stderr)
    sys.exit(1)


def log_timing(tool: str, duration_ms: float, **extra) -> None:
    parts = [f"tool={tool}", f"duration_ms={duration_ms:.0f}"]
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    print(f"[timing] {' '.join(parts)}", file=sys.stderr)


def get_base_url() -> str:
    base_url = os.environ.get(ENV_VAR)
    if not base_url:
        emit_error(
            "env_var_missing",
            f"{ENV_VAR} is not set. Check .sap-connectivity.json declares the "
            "'agent' connector for skill 'ontology-manager-skill', and that the plugin "
            "with this connectivity file is the one currently active.",
        )
    return base_url.rstrip("/")


def mcp_call(base_url: str, tool_name: str, arguments: dict, timeout: float = 60) -> dict:
    attempts = [
        {"Accept": "application/json"},
        {"Accept": "application/json, text/event-stream"},
        {"Accept": "*/*"},
    ]
    last_status = None
    last_body = None
    for extra_headers in attempts:
        try:
            response = requests.post(
                f"{base_url}/mcp-json/",
                headers={"Content-Type": "application/json", **extra_headers},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
                timeout=timeout,
            )
            last_status = response.status_code
            last_body = response.text
            if response.status_code == 406:
                continue
            response.raise_for_status()
            for line in response.text.split("\n"):
                if line.startswith("data:"):
                    return json.loads(line[5:])
            return response.json()
        except RequestException as exc:
            last_body = getattr(exc.response, "text", str(exc))
            last_status = getattr(getattr(exc, "response", None), "status_code", None)
            continue
    emit_error(
        "mcp_request_failed",
        "All attempts returned 406. Server requires Accept: application/json, text/event-stream but the BTP proxy strips it.",
        http_status=last_status,
        response_body=last_body,
    )


def extract_tool_result(raw: dict) -> dict:
    content = raw.get("result", {}).get("content", [])
    if content:
        try:
            return json.loads(content[0].get("text", "{}"))
        except json.JSONDecodeError:
            pass
    return raw


def print_env_debug() -> None:
    env_dump = {name: os.environ.get(name) for name in DEBUG_ENV_VARS}
    base_url = os.environ.get(ENV_VAR, "").rstrip("/")
    reachability = {"checked": False}
    if base_url:
        reachability["checked"] = True
        for url, accept in [(f"{base_url}/mcp-json", "application/json"), (f"{base_url}/mcp-json/", "application/json")]:
            try:
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json", "Accept": accept},
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                    timeout=10,
                )
                reachability[url] = {
                    "status_code": response.status_code,
                    "ok": response.status_code < 500,
                    "response_body": response.text[:500],
                }
            except RequestException as exc:
                reachability[url] = {
                    "ok": False,
                    "exception": type(exc).__name__,
                    "exception_message": str(exc),
                }
    print(json.dumps({"env": env_dump, "reachability": reachability}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", help=f"Tool to call. One of: {', '.join(AVAILABLE_TOOLS)} or 'ping'")
    parser.add_argument("arguments", nargs="?", default="{}", help="JSON arguments for the tool (default: {})")
    parser.add_argument("--timeout", type=float, default=None,
                        help="HTTP timeout in seconds (default: 120 for execute_business_action, 60 for all others)")
    args = parser.parse_args()

    if args.tool.strip().lower() == "ping":
        print_env_debug()
        return

    if args.tool not in AVAILABLE_TOOLS:
        emit_error("unknown_tool", f"Unknown tool '{args.tool}'. Available: {AVAILABLE_TOOLS}")

    try:
        arguments = json.loads(args.arguments)
    except json.JSONDecodeError as e:
        emit_error("invalid_arguments", f"Arguments must be valid JSON: {e}")

    base_url = get_base_url()

    if args.timeout is not None:
        timeout = args.timeout
    elif args.tool == "execute_business_action":
        timeout = 120
    else:
        timeout = 60

    t0 = time.monotonic()
    raw = mcp_call(base_url, args.tool, arguments, timeout=timeout)
    duration_ms = (time.monotonic() - t0) * 1000

    result = extract_tool_result(raw)

    timing: dict = {"tool": args.tool, "duration_ms": round(duration_ms)}
    if args.tool == "execute_sparql" and "execution_time_ms" in result:
        timing["backend_execution_ms"] = result["execution_time_ms"]

    # Write to stderr for live visibility
    log_timing(args.tool, duration_ms, **{k: v for k, v in timing.items() if k not in ("tool", "duration_ms")})

    # Include timing in stdout so the Joule runtime log captures it
    print(json.dumps({"ok": True, "tool": args.tool, "timing": timing, "result": raw}, indent=2))


if __name__ == "__main__":
    main()
