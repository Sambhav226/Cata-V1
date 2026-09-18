"""Single choke point for whether a model is available. Every agent asks
this module for a completion; nobody reads ANTHROPIC_API_KEY directly — see
skills/agent-architecture. Returns None on any failure (no key, missing
package, network error, malformed JSON), which is the signal for callers to
fall through to their deterministic fallback."""
from __future__ import annotations

import json
import os
from typing import Optional

_DEFAULT_MODEL = os.environ.get("CODER_MODEL", "claude-sonnet-4-5")

_client = None
_client_checked = False


def _get_client():
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic

        _client = anthropic.Anthropic(api_key=api_key)
    except Exception:
        _client = None
    return _client


def available() -> bool:
    return _get_client() is not None


def complete_json(system: str, user: str, max_tokens: int = 1024) -> Optional[dict]:
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.messages.create(
            model=_DEFAULT_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception:
        return None
