"""Single choke point for whether a model is available. Every agent asks
this module for a completion; nobody reads ANTHROPIC_API_KEY directly — see
skills/agent-architecture. Returns None on any failure (no key, missing
package, network error, malformed JSON), which is the signal for callers to
fall through to their deterministic fallback.

Also holds the safe-coercion helpers every agent uses to turn a parsed LLM
JSON value into a Python bool/float without raising or silently inverting
(a bare `bool(x)`/`float(x)` on model output is a real trap: the string
"false" is truthy, and `float(None)` raises)."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Optional

_DEFAULT_MODEL = os.environ.get("CODER_MODEL", "claude-sonnet-4-5")

_client = None
_client_checked = False
_client_lock = threading.Lock()


def _get_client():
    global _client, _client_checked
    if _client_checked:
        return _client
    with _client_lock:
        if _client_checked:
            return _client
        _client_checked = True
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
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
        )
        return _parse_json_object(text)
    except Exception:
        return None


def _parse_json_object(text: str) -> Optional[dict]:
    """Tries a few increasingly forgiving ways to pull one JSON object out
    of a model response: as-is, with a code fence stripped, and as the
    substring between the first '{' and the last '}' (covers stray prose
    before/after the JSON, which fence-stripping alone doesn't)."""
    candidates = [text.strip()]

    fenced = text.strip()
    if fenced.startswith("```"):
        fenced = fenced.strip("`")
        if fenced.lower().startswith("json"):
            fenced = fenced[4:]
        candidates.append(fenced.strip())

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "no", "0", "")
    return bool(value)


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
