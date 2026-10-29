"""HAR 1.2 parser: streaming-safe parse with caps, redaction, and hashing
(HF-FR-070/076). Tokens are redacted before persistence (never stored raw).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

from ...core.redaction import redact_headers, redact_text

MAX_HAR_BYTES = 50 * 1024 * 1024
MAX_ENTRY_BYTES = 20 * 1024 * 1024


class HarError(ValueError):
    pass


@dataclass
class HarEntry:
    method: str
    url: str
    request_headers: dict[str, Any]
    request_body: str | None
    response_status: int | None
    response_headers: dict[str, Any]
    response_body: str | None
    timing: dict | None
    hash: str

    @property
    def url_host(self) -> str:
        return (urlsplit(self.url).hostname or "").lower()


def _headers_to_dict(entries: list[dict] | None) -> dict[str, Any]:
    if not entries:
        return {}
    out: dict[str, Any] = {}
    for item in entries:
        name = str(item.get("name", ""))
        if name:
            out[name] = item.get("value", "")
    return out


def _entry_size(entry: dict) -> int:
    return len(json.dumps(entry, default=str))


def parse_har(path: Path) -> Iterator[HarEntry]:
    if path.stat().st_size > MAX_HAR_BYTES:
        raise HarError(f"HAR file exceeds {MAX_HAR_BYTES} bytes")
    try:
        data = json.loads(path.read_text("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise HarError(f"Invalid HAR JSON: {exc}") from exc
    log = data.get("log") or {}
    entries = log.get("entries") or []
    if not isinstance(entries, list):
        raise HarError("HAR log.entries missing or invalid")
    for entry in entries:
        if _entry_size(entry) > MAX_ENTRY_BYTES:
            continue  # skip oversized entries; the import summary reports skips
        request = entry.get("request") or {}
        response = entry.get("response") or {}
        method = (request.get("method") or "GET").upper()
        url = request.get("url") or ""
        if not url:
            continue
        req_headers = redact_headers(_headers_to_dict(request.get("headers")))
        resp_headers = redact_headers(_headers_to_dict(response.get("headers")))
        req_body = None
        post_data = request.get("postData") or {}
        if post_data.get("text"):
            req_body = redact_text(str(post_data["text"]))
        resp_body = None
        content = response.get("content") or {}
        if content.get("text"):
            resp_body = redact_text(str(content["text"]))

        canonical = json.dumps(
            [method, url, response.get("status"), req_headers, resp_headers, req_body, resp_body],
            sort_keys=True,
            default=str,
        )
        h = hashlib.sha256(canonical.encode()).hexdigest()
        yield HarEntry(
            method=method,
            url=url,
            request_headers=req_headers,
            request_body=req_body,
            response_status=response.get("status"),
            response_headers=resp_headers,
            response_body=resp_body,
            timing=entry.get("timings"),
            hash=h,
        )
