#!/usr/bin/env python3
"""Ensembra Gemini MCP server — main entry (v0.9.0+).

Wraps the Google Generative AI REST API so that the Ensembra Conductor
can call Gemini models without exposing the API key in skill/agent content.

Transport: stdin/stdout JSON-RPC 2.0 (MCP protocol).

v0.9.0+ structure (refactored from monolithic server.py):
  - server.py          — main entry, MCP dispatch (this file)
  - keychain.py        — OS keychain (macOS/Linux/Windows)
  - gemini_client.py   — Gemini REST API + system prompt injection
  - roles/
    - architect.py / planner.py / developer.py / security.py / qa.py /
      devils.py / scribe.py / final_auditor.py / triage.py
      each exposes: TOOL_NAME, DEFAULT_MODEL, DEFAULT_TIMEOUT, TEMPERATURE,
      RESPONSE_MIME_TYPE, DESCRIPTION, SYSTEM_PROMPT

Previously named `gemini-architect` (v0.7.0~v0.8.1). Renamed to
`gemini-ensembra` in v0.9.0 to reflect that the server now serves
all 9 Performer roles, not just architect.

API key resolution: see keychain.py (env var → OS keychain → error).
"""

import json
import platform
import sys

from gemini_client import call_gemini
from roles import ALL_ROLES, REGISTRY

# ---------------------------------------------------------------------------
# Server identity
# ---------------------------------------------------------------------------

SERVER_NAME = "ensembra-gemini"
SERVER_VERSION = "0.9.3"

# ---------------------------------------------------------------------------
# MCP tool definitions (built from role registry)
# ---------------------------------------------------------------------------


def build_tool_definitions():
    """Build MCP tool list from role registry."""
    return [
        {
            "name": role.TOOL_NAME,
            "description": role.DESCRIPTION,
            "inputSchema": {
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The full prompt to send to Gemini.",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Gemini model ID. Default: {role.DEFAULT_MODEL}",
                        "default": role.DEFAULT_MODEL,
                    },
                    "timeout_sec": {
                        "type": "integer",
                        "description": f"Request timeout in seconds. Default: {role.DEFAULT_TIMEOUT}",
                        "default": role.DEFAULT_TIMEOUT,
                    },
                },
            },
        }
        for role in ALL_ROLES
    ]


TOOL_DEFINITIONS = build_tool_definitions()

# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------


def _write(obj: dict) -> None:
    """Write a JSON-RPC message to stdout."""
    line = json.dumps(obj, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _ok(id_val, result: dict) -> None:
    _write({"jsonrpc": "2.0", "id": id_val, "result": result})


def _error(id_val, code: int, message: str) -> None:
    _write({"jsonrpc": "2.0", "id": id_val, "error": {"code": code, "message": message}})


# ---------------------------------------------------------------------------
# MCP request handlers
# ---------------------------------------------------------------------------


def handle_initialize(msg: dict) -> None:
    _ok(msg["id"], {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    })


def handle_tools_list(msg: dict) -> None:
    _ok(msg["id"], {"tools": TOOL_DEFINITIONS})


def handle_tools_call(msg: dict) -> None:
    params = msg.get("params", {})
    tool_name = params.get("name", "")

    role = REGISTRY.get(tool_name)
    if role is None:
        _error(msg["id"], -32602, f"Unknown tool: {tool_name}")
        return

    args = params.get("arguments", {})
    prompt = args.get("prompt", "")
    model = args.get("model", role.DEFAULT_MODEL)
    timeout = args.get("timeout_sec", role.DEFAULT_TIMEOUT)

    if not prompt:
        _error(msg["id"], -32602, "prompt is required")
        return

    try:
        text = call_gemini(
            user_prompt=prompt,
            model=model,
            timeout=timeout,
            system_prompt=role.SYSTEM_PROMPT,
            temperature=role.TEMPERATURE,
            response_mime_type=role.RESPONSE_MIME_TYPE,
        )
        _ok(msg["id"], {
            "content": [{"type": "text", "text": text}],
            "isError": False,
        })
    except RuntimeError as exc:
        _ok(msg["id"], {
            "content": [{"type": "text", "text": str(exc)}],
            "isError": True,
        })


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def main() -> None:
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    sys.stderr.write(
        f"{SERVER_NAME} v{SERVER_VERSION} started "
        f"(python={py_ver}, platform={platform.system()}, roles={len(ALL_ROLES)})\n"
    )
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue  # skip malformed lines

        method = msg.get("method", "")

        # Notifications (no id) — just acknowledge
        if "id" not in msg:
            if method == "notifications/initialized":
                pass  # client confirmed init
            continue

        handler = HANDLERS.get(method)
        if handler:
            handler(msg)
        else:
            _error(msg["id"], -32601, f"Method not found: {method}")


if __name__ == "__main__":
    main()
