#!/usr/bin/env python3
"""Ensembra Gemini Architect — MCP stdio server.

Wraps the Google Generative AI REST API so that the Ensembra Conductor
can call Gemini models without exposing the API key in skill/agent content.

Transport: stdin/stdout JSON-RPC 2.0 (MCP protocol).

API key resolution (first match wins):
  1. GEMINI_API_KEY env var (for CI / manual override)
  2. Claude Code keychain — reads pluginSecrets from OS credential store
     macOS:  security find-generic-password -s "Claude Code-credentials" -w
     Linux:  secret-tool lookup service "Claude Code-credentials"
  3. Error — guides user to /plugin → Configure options
"""

import json
import os
import platform
import subprocess
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVER_NAME = "ensembra-gemini-architect"
SERVER_VERSION = "0.8.1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_ARCHITECT_MODEL = "gemini-2.5-flash"
DEFAULT_DEVELOPER_MODEL = "gemini-2.5-pro"
DEFAULT_TIMEOUT = 60

KEYCHAIN_SERVICE = "Claude Code-credentials"
PLUGIN_SECRET_PATH = ("pluginSecrets", "ensembra@ensembra", "gemini_api_key")

# Backward compatibility: legacy consumers may still reference DEFAULT_MODEL
DEFAULT_MODEL = DEFAULT_ARCHITECT_MODEL

TOOL_DEFINITIONS = [
    {
        "name": "architect_deliberate",
        "description": (
            "Send an architect-framed prompt to Google Gemini and return the "
            "response. Used by the Ensembra Conductor for Phase 1 R1/R2 architect "
            "Performer calls and Phase 3 architect Audit. Keeps the API key out of "
            "skill/agent content (MCP server env only)."
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
                    "description": f"Gemini model ID. Default: {DEFAULT_ARCHITECT_MODEL}",
                    "default": DEFAULT_ARCHITECT_MODEL,
                },
                "timeout_sec": {
                    "type": "integer",
                    "description": f"Request timeout in seconds. Default: {DEFAULT_TIMEOUT}",
                    "default": DEFAULT_TIMEOUT,
                },
            },
        },
    },
    {
        "name": "developer_deliberate",
        "description": (
            "Send a developer-framed prompt to Google Gemini and return the "
            "response. Used by the Ensembra Conductor when the developer Performer "
            "is configured for MCP transport (opt-in via config.performers.developer"
            ".transport_chain). Default model is gemini-2.5-pro for stronger "
            "implementation-level reasoning. Shares the same credential and "
            "masking guarantees as architect_deliberate."
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
                    "description": f"Gemini model ID. Default: {DEFAULT_DEVELOPER_MODEL}",
                    "default": DEFAULT_DEVELOPER_MODEL,
                },
                "timeout_sec": {
                    "type": "integer",
                    "description": f"Request timeout in seconds. Default: {DEFAULT_TIMEOUT}",
                    "default": DEFAULT_TIMEOUT,
                },
            },
        },
    },
]

# Map tool name → default model. Shared call_gemini handles both.
TOOL_DEFAULT_MODEL = {
    "architect_deliberate": DEFAULT_ARCHITECT_MODEL,
    "developer_deliberate": DEFAULT_DEVELOPER_MODEL,
}

# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------

_cached_api_key = None  # type: str | None


def _read_keychain_macos():
    """Read Claude Code credentials from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        raw = result.stdout.strip()
        if not raw:
            return None
        data = json.loads(raw)
        # Navigate: pluginSecrets -> ensembra@ensembra -> gemini_api_key
        node = data
        for key in PLUGIN_SECRET_PATH:
            node = node.get(key)
            if node is None:
                return None
        return str(node) if node else None
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return None


def _read_keychain_linux():
    """Read Claude Code credentials from Linux secret-tool (GNOME Keyring)."""
    try:
        result = subprocess.run(
            ["secret-tool", "lookup", "service", KEYCHAIN_SERVICE],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        raw = result.stdout.strip()
        if not raw:
            return None
        data = json.loads(raw)
        node = data
        for key in PLUGIN_SECRET_PATH:
            node = node.get(key)
            if node is None:
                return None
        return str(node) if node else None
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return None


def _read_keychain_windows():
    """Read Claude Code credentials from Windows Credential Manager via Win32 CredReadW."""
    try:
        import ctypes
        from ctypes import wintypes

        CRED_TYPE_GENERIC = 1

        class CREDENTIAL(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        advapi.CredReadW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(CREDENTIAL)),
        ]
        advapi.CredReadW.restype = wintypes.BOOL
        advapi.CredFree.argtypes = [ctypes.c_void_p]
        advapi.CredFree.restype = None

        cred_ptr = ctypes.POINTER(CREDENTIAL)()
        if not advapi.CredReadW(KEYCHAIN_SERVICE, CRED_TYPE_GENERIC, 0, ctypes.byref(cred_ptr)):
            return None
        try:
            blob_size = cred_ptr.contents.CredentialBlobSize
            blob_ptr = cred_ptr.contents.CredentialBlob
            raw_bytes = ctypes.string_at(blob_ptr, blob_size)
            raw = raw_bytes.decode("utf-16-le", errors="ignore").strip("\x00").strip()
        finally:
            advapi.CredFree(cred_ptr)

        if not raw:
            return None
        data = json.loads(raw)
        node = data
        for key in PLUGIN_SECRET_PATH:
            node = node.get(key)
            if node is None:
                return None
        return str(node) if node else None
    except (json.JSONDecodeError, OSError, AttributeError, ImportError):
        return None


def resolve_api_key() -> str:
    """Resolve GEMINI_API_KEY with fallback chain."""
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key

    # 1. Environment variable
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        _cached_api_key = key
        sys.stderr.write("API key source: environment variable\n")
        sys.stderr.flush()
        return key

    # 2. OS keychain
    system = platform.system()
    if system == "Darwin":
        key = _read_keychain_macos()
    elif system == "Linux":
        key = _read_keychain_linux()
    elif system == "Windows":
        key = _read_keychain_windows()

    if key:
        _cached_api_key = key
        sys.stderr.write(f"API key source: {system} keychain\n")
        sys.stderr.flush()
        return key

    # 3. Not found
    raise RuntimeError(
        "GEMINI_API_KEY not found. "
        "Set it via: /plugin \u2192 ensembra \u2192 Configure options \u2192 gemini_api_key, "
        "then run /reload-plugins. "
        "Alternatively, set the GEMINI_API_KEY environment variable."
    )


# ---------------------------------------------------------------------------
# Gemini API caller
# ---------------------------------------------------------------------------

def call_gemini(prompt: str, model: str, timeout: int) -> str:
    """Call the Gemini REST API and return the text response."""
    api_key = resolve_api_key()

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
    _ok(msg["id"], {"tools": TOOL_DEFINITIONS})


def handle_tools_call(msg: dict) -> None:
    params = msg.get("params", {})
    tool_name = params.get("name", "")

    if tool_name not in TOOL_DEFAULT_MODEL:
        _error(msg["id"], -32602, f"Unknown tool: {tool_name}")
        return

    args = params.get("arguments", {})
    prompt = args.get("prompt", "")
    model = args.get("model", TOOL_DEFAULT_MODEL[tool_name])
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
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    sys.stderr.write(
        f"{SERVER_NAME} v{SERVER_VERSION} started "
        f"(python={py_ver}, platform={platform.system()})\n"
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
