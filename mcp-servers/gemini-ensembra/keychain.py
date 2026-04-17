"""Ensembra Gemini MCP server — OS keychain integration.

Resolves GEMINI_API_KEY from env var or OS keychain (macOS/Linux/Windows).
Never exposes the key in logs or error messages.
"""

import json
import os
import platform
import subprocess
import sys

KEYCHAIN_SERVICE = "Claude Code-credentials"
PLUGIN_SECRET_PATH = ("pluginSecrets", "ensembra@ensembra", "gemini_api_key")

_cached_api_key = None  # type: str | None


def _navigate_secret(data: dict) -> str | None:
    """Navigate pluginSecrets → ensembra@ensembra → gemini_api_key."""
    node = data
    for key in PLUGIN_SECRET_PATH:
        node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            return None
    return str(node) if node else None


def _read_keychain_macos() -> str | None:
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
        return _navigate_secret(json.loads(raw))
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return None


def _read_keychain_linux() -> str | None:
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
        return _navigate_secret(json.loads(raw))
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return None


def _read_keychain_windows() -> str | None:
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
        return _navigate_secret(json.loads(raw))
    except (json.JSONDecodeError, OSError, AttributeError, ImportError):
        return None


def resolve_api_key() -> str:
    """Resolve GEMINI_API_KEY with fallback chain.

    Priority:
      1. GEMINI_API_KEY env var (CI / manual override)
      2. OS keychain (macOS/Linux/Windows)
      3. RuntimeError with user guidance

    Cached after first successful resolution.
    """
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key

    checked = []

    # 1. Environment variable
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    checked.append("env GEMINI_API_KEY (empty)" if not key else "env GEMINI_API_KEY")
    if key:
        _cached_api_key = key
        sys.stderr.write("API key source: environment variable\n")
        sys.stderr.flush()
        return key

    # 2. OS keychain
    system = platform.system()
    if system == "Darwin":
        key = _read_keychain_macos()
        checked.append(
            f"macOS Keychain service '{KEYCHAIN_SERVICE}' "
            f"\u2192 pluginSecrets.ensembra@ensembra.gemini_api_key"
        )
    elif system == "Linux":
        key = _read_keychain_linux()
        checked.append(f"secret-tool service '{KEYCHAIN_SERVICE}'")
    elif system == "Windows":
        key = _read_keychain_windows()
        checked.append(f"Credential Manager target '{KEYCHAIN_SERVICE}'")
    else:
        checked.append(f"unknown platform '{system}' — keychain skipped")

    if key:
        _cached_api_key = key
        sys.stderr.write(f"API key source: {system} keychain\n")
        sys.stderr.flush()
        return key

    # 3. Not found — emit diagnostic listing every probed source so users can
    # pinpoint which step failed (env var typo vs. keychain service mismatch).
    raise RuntimeError(
        f"GEMINI_API_KEY not found on {system}. "
        f"Checked: {'; '.join(checked)}. "
        f"Fix: /plugin \u2192 ensembra \u2192 Configure options \u2192 gemini_api_key, "
        f"then run /reload-plugins. "
        f"Alternatively, set the GEMINI_API_KEY environment variable "
        f"(e.g., export GEMINI_API_KEY=AIza...)."
    )
