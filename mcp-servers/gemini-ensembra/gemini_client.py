"""Ensembra Gemini MCP server — Gemini REST API client.

Handles prompt assembly (system + user), generationConfig, and error masking.
Never includes the API key in error messages.
"""

import json
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
