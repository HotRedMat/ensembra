"""Ensembra Gemini MCP server — role registry.

Each role module defines:
  - ROLE_NAME      — e.g. "architect"
  - TOOL_NAME      — MCP tool identifier (e.g. "architect_deliberate")
  - DEFAULT_MODEL  — Gemini model ID
  - DEFAULT_TIMEOUT — seconds
  - TEMPERATURE    — sampling temperature
  - RESPONSE_MIME_TYPE — None or "application/json"
  - DESCRIPTION    — MCP tool description (English, for tool listing)
  - SYSTEM_PROMPT  — role-specific system prompt (Korean, matches agents/*.md)
"""

from . import (
    architect,
    planner,
    developer,
    security,
    qa,
    devils,
    scribe,
    final_auditor,
    triage,
)

ALL_ROLES = [
    architect,
    planner,
    developer,
    security,
    qa,
    devils,
    scribe,
    final_auditor,
    triage,
]

# Tool name → role module dispatch table
REGISTRY = {role.TOOL_NAME: role for role in ALL_ROLES}
