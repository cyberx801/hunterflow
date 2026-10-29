"""Central secret redaction (HF-SEC-007, Constitution P3).

Applied at logging, tool-argument persistence, HAR import, and report rendering.
Deterministic replacement so identical secrets redact identically.
"""

from __future__ import annotations

import re
from typing import Any

_REDACTED = "[REDACTED]"

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("bearer", re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*")),
    ("authorization", re.compile(r"(?i)(authorization\s*[:\s]\s*)(basic\s+\S+|bearer\s+\S+)")),
    ("set_cookie", re.compile(r"(?i)(set-cookie\s*:\s*)[^\r\n]+")),
    ("cookie_header", re.compile(r"(?i)(cookie\s*:\s*)[^\r\n]+")),
    ("aws_key", re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("aws_secret", re.compile(r"(?i)aws_secret_access_key[\"']?\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "generic_api_key",
        re.compile(r"(?i)\b(api[_-]?key|apikey|token|secret|password)[\"']?\s*[:=]\s*[\"'][^\"'\r\n]{6,}[\"']"),
    ),
]

# Patterns applied only to well-formed header dicts, per-name:
_SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "proxy-authorization",
    "x-auth-token",
}


def redact_text(value: str) -> str:
    result = value
    for _name, pattern in _PATTERNS:
        result = pattern.sub(lambda m: m.group(0)[0] + _REDACTED, result)  # keep first char for diff stability
    return result


def redact_headers(headers: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in headers.items():
        if str(key).lower() in _SENSITIVE_HEADER_NAMES:
            out[key] = _REDACTED
        else:
            out[key] = redact_text(str(value)) if isinstance(value, str) else value
    return out


def redact_json(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: redact_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact_json(v) for v in data]
    if isinstance(data, str):
        return redact_text(data)
    return data


def redact_any(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, (dict, list)):
        return redact_json(value)
    return value
