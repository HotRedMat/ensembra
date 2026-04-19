"""Ensembra Gemini MCP server — Gemini REST API client.

Handles prompt assembly (system + user), generationConfig, and error masking.
Never includes the API key in error messages.

v0.11.0+ request-body scrubber: before the prompt is sent to Gemini, a
pattern-based redactor masks common secret formats (API keys, bearer tokens,
.env key=value lines). Defence-in-depth — the caller SHOULD already filter,
but a Context Snapshot accidentally pasting an .env excerpt must not leak.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request

from keychain import resolve_api_key

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_OUTPUT_TOKENS = 8192
ERROR_BODY_SNIPPET_LIMIT = 240
MAX_RETRIES_5XX = 1
RETRY_BACKOFF_SEC = 1.0

# ---------------------------------------------------------------------------
# Outbound secret scrubber (v0.11.0+)
# ---------------------------------------------------------------------------
#
# Patterns chosen for common keys that a Context Snapshot may accidentally
# carry. Intentionally conservative — these redact to "[REDACTED:<kind>]" so
# the model still sees that *something* was there (for reasoning) but never
# the value.

_SCRUB_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("gemini",    re.compile(r"AIza[0-9A-Za-z_\-]{20,}")),
    ("openai",    re.compile(r"sk-[A-Za-z0-9_\-]{20,}")),
    ("anthropic", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("github",    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("slack",     re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("aws",       re.compile(r"AKIA[0-9A-Z]{16}")),
    ("jwt",       re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("bearer",    re.compile(r"(?i)(?:Authorization\s*:\s*)?Bearer\s+[A-Za-z0-9_\-\.=]{16,}")),
]

# .env-style KEY=VALUE lines where KEY hints at a secret. Masks the VALUE.
_ENV_SECRET_LINE = re.compile(
    r"(?im)^(\s*(?:[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE)[A-Z0-9_]*)\s*=\s*)(\S.*)$"
)


def scrub_outbound(text: str) -> str:
    """Redact likely secrets from text that will be sent to an external LLM.

    Redaction is done in-place per pattern. This is a best-effort defensive
    layer — callers must still avoid putting secrets in prompts. Never logs
    the matched value (only the kind label).
    """
    if not text:
        return text
    out = text
    for kind, pattern in _SCRUB_PATTERNS:
        out = pattern.sub(f"[REDACTED:{kind}]", out)
    out = _ENV_SECRET_LINE.sub(r"\1[REDACTED:env]", out)
    return out


def _extract_error_detail(exc: urllib.error.HTTPError, api_key: str) -> str:
    """Read HTTPError body, mask the API key, return a compact detail suffix.

    Returns an empty string when the body is unreadable so that the caller can
    fall back to the bare status code. The API key is always replaced with
    "[REDACTED]" defensively, even though Gemini error bodies should not echo
    it back.
    """
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
    if not body:
        return ""
    if api_key:
        body = body.replace(api_key, "[REDACTED]")
    try:
        data = json.loads(body)
        err = data.get("error", {}) if isinstance(data, dict) else {}
        status = (err.get("status") or "").strip()
        message = (err.get("message") or "").strip()[:ERROR_BODY_SNIPPET_LIMIT]
        if status and message:
            return f" ({status}: {message})"
        if status:
            return f" ({status})"
        if message:
            return f" ({message})"
    except (ValueError, TypeError):
        pass
    snippet = body.strip().replace("\n", " ")[:ERROR_BODY_SNIPPET_LIMIT]
    return f" (body: {snippet})" if snippet else ""


def call_gemini(
    user_prompt: str,
    model: str,
    timeout: int,
    system_prompt: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    response_mime_type: str | None = None,
) -> str:
    """Call the Gemini REST API and return the text response.

    Args:
      user_prompt: User-supplied prompt content (from MCP `prompt` arg).
      model: Gemini model ID (e.g., "gemini-2.5-flash").
      timeout: Request timeout in seconds.
      system_prompt: Optional role-specific system prompt to prefix.
      temperature: Sampling temperature (default 0.7).
      max_output_tokens: Output length cap.
      response_mime_type: Force JSON output when set to "application/json"
        (used by triage role).

    Raises:
      RuntimeError: On API failure, empty response, or unreachable endpoint.
        Error messages never contain the API key. For HTTP failures the
        response body's `error.status` and `error.message` are appended (after
        masking) so callers can distinguish quota / rate-limit / 5xx causes.
    """
    api_key = resolve_api_key()

    # Outbound scrub: mask likely secrets before the prompt leaves the host.
    # System prompt is authored by us (roles/*.py) so we trust it; user_prompt
    # may carry Context Snapshot excerpts that accidentally include an .env
    # line or API key.
    user_prompt = scrub_outbound(user_prompt)

    # Assemble contents: system prompt as first turn if provided
    contents = []
    if system_prompt:
        contents.append({
            "role": "user",
            "parts": [{"text": system_prompt}],
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "이해했습니다. 역할에 맞게 응답하겠습니다."}],
        })
    contents.append({
        "role": "user",
        "parts": [{"text": user_prompt}],
    })

    generation_config = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type

    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={api_key}"
    body = json.dumps({
        "contents": contents,
        "generationConfig": generation_config,
    }).encode()

    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"},
    )

    # 5xx is typically transient (Google-side throttling / Service Unavailable);
    # one retry with short backoff recovers the majority without bothering the
    # caller's fallback chain. 4xx is deterministic — never retried.
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            break
        except urllib.error.HTTPError as exc:
            if 500 <= exc.code < 600 and attempt < MAX_RETRIES_5XX:
                attempt += 1
                sys.stderr.write(
                    f"Gemini HTTP {exc.code} — retry {attempt}/{MAX_RETRIES_5XX} "
                    f"after {RETRY_BACKOFF_SEC}s\n"
                )
                sys.stderr.flush()
                time.sleep(RETRY_BACKOFF_SEC)
                continue
            detail = _extract_error_detail(exc, api_key)
            raise RuntimeError(
                f"Gemini API returned HTTP {exc.code}{detail}"
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
