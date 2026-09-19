"""Single choke point for whether a model is available. Every agent asks
this module for a completion; nobody reads a provider's env var directly —
see skills/agent-architecture. Returns None on any failure (no key, missing
package, network error, malformed JSON), which is the signal for callers to
fall through to their deterministic fallback.

Two providers are supported, picked by whichever key is set
(ANTHROPIC_API_KEY takes priority if both are): Anthropic via the official
SDK, and Google (Gemini) via a plain stdlib HTTP call — no new dependency
for the second provider, matching this project's stdlib-first bias
elsewhere (see skills/clinical-retrieval). Agents don't know or care which
provider answered; that's the point of the choke point.

Also holds the safe-coercion helpers every agent uses to turn a parsed LLM
JSON value into a Python bool/float without raising or silently inverting
(a bare `bool(x)`/`float(x)` on model output is a real trap: the string
"false" is truthy, and `float(None)` raises)."""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from typing import Any, Optional

_ANTHROPIC_MODEL = os.environ.get("CODER_MODEL", "claude-sonnet-4-5")
_GOOGLE_MODEL = os.environ.get("CODER_MODEL_GOOGLE", "gemini-2.5-flash")
_GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

_client = None
_client_checked = False
_client_lock = threading.Lock()


def _provider() -> Optional[str]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GOOGLE_API_KEY"):
        return "google"
    return None


def available() -> bool:
    return _provider() is not None


def complete_json(system: str, user: str, max_tokens: int = 1024) -> Optional[dict]:
    provider = _provider()
    if provider == "anthropic":
        return _complete_anthropic(system, user, max_tokens)
    if provider == "google":
        return _complete_google(system, user, max_tokens)
    return None


def _get_anthropic_client():
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


def _complete_anthropic(system: str, user: str, max_tokens: int) -> Optional[dict]:
    client = _get_anthropic_client()
    if client is None:
        return None
    try:
        response = client.messages.create(
            model=_ANTHROPIC_MODEL,
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


def _complete_google(system: str, user: str, max_tokens: int) -> Optional[dict]:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": max_tokens,
            # Gemini 2.5's extended-thinking tokens count against
            # maxOutputTokens — left enabled, a model can burn the whole
            # budget "thinking" and get cut off (finishReason=MAX_TOKENS)
            # before writing any of the actual JSON answer. These are
            # narrow, single-purpose calls in an already-multi-step agent
            # pipeline; they don't need the model's own extra deliberation
            # on top, so it's disabled for a direct, complete answer.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = _GOOGLE_URL.format(model=_GOOGLE_MODEL, key=api_key)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
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
