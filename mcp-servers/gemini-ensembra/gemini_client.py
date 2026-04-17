"""Ensembra Gemini MCP server — Gemini REST API client.

Handles prompt assembly (system + user), generationConfig, and error masking.
Never includes the API key in error messages.
"""

import json
import urllib.error
import urllib.request

from keychain import resolve_api_key

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_OUTPUT_TOKENS = 8192


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
        Error messages never contain the API key.
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
