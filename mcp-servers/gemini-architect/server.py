#!/usr/bin/env python3
"""Ensembra Gemini Architect — MCP stdio server.

Wraps the Google Generative AI REST API so that the Ensembra Conductor
can call Gemini models without exposing the API key in skill/agent content.

Transport: stdin/stdout JSON-RPC 2.0 (MCP protocol).
Secret:    GEMINI_API_KEY env var (injected via settings.local.json mcpServers.env).
"""

import json
import os
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVER_NAME = "ensembra-gemini-architect"
SERVER_VERSION = "0.7.0"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT = 60

TOOL_DEFINITION = {
    "name": "architect_deliberate",
    "description": (
        "Send a prompt to Google Gemini and return the response. "
        "Used by the Ensembra Conductor to delegate architect analysis "
        "to a Gemini model via MCP, keeping the API key out of "
        "skill/agent content."
    ),
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
                "description": f"Gemini model ID. Default: {DEFAULT_MODEL}",
                "default": DEFAULT_MODEL,
            },
            "timeout_sec": {
                "type": "integer",
                "description": f"Request timeout in seconds. Default: {DEFAULT_TIMEOUT}",
                "default": DEFAULT_TIMEOUT,
            },
        },
    },
}

# ---------------------------------------------------------------------------
# Gemini API caller
# ---------------------------------------------------------------------------

def call_gemini(prompt: str, model: str, timeout: int) -> str:
    """Call the Gemini REST API and return the text response."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={api_key}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192},
    }).encode()

    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        # Never include the API key in error messages
        raise RuntimeError(
            f"Gemini API returned HTTP {exc.code}"
        ) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Gemini API unreachable: {exc.reason}"
        ) from None

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned empty candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)

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
    _ok(msg["id"], {"tools": [TOOL_DEFINITION]})


def handle_tools_call(msg: dict) -> None:
    params = msg.get("params", {})
    tool_name = params.get("name", "")

    if tool_name != "architect_deliberate":
        _error(msg["id"], -32602, f"Unknown tool: {tool_name}")
        return

    args = params.get("arguments", {})
    prompt = args.get("prompt", "")
    model = args.get("model", DEFAULT_MODEL)
    timeout = args.get("timeout_sec", DEFAULT_TIMEOUT)

    if not prompt:
        _error(msg["id"], -32602, "prompt is required")
        return

    try:
        text = call_gemini(prompt, model, timeout)
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
    # Log to stderr (not visible to Claude Code MCP client)
    sys.stderr.write(f"{SERVER_NAME} v{SERVER_VERSION} started\n")
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
