"""Asset/URL normalization and dedup keys (HF-FR-041).

Equivalent representations must collapse to one canonical key:
- hosts: lowercase, trailing-dot stripped, IPv6 bracket stripped
- URLs: default ports removed, fragment removed, single trailing slash only
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit, urlunsplit

from ..scope.policy import RuleKind  # noqa: F401  (kind names kept distinct)


class AssetKind:
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    IP = "ip"
    URL = "url"
    WEB_SERVICE = "web_service"
    API_ENDPOINT = "api_endpoint"


def normalize_host(host: str | None) -> str:
    if not host:
        return ""
    host = host.strip().lower().rstrip(".")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "").lower()
    host = normalize_host(parts.hostname)
    if parts.port:
        netloc = host
        if not ((scheme == "http" and parts.port == 80) or (scheme == "https" and parts.port == 443)):
            netloc = f"{host}:{parts.port}"
        if parts.username or parts.password:
            netloc = f"{host}:{parts.port}"
    else:
        netloc = host
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query = parts.query
    return urlunsplit((scheme, netloc, path, query, ""))


def kind_of(value: str) -> str:
    v = value.strip()
    if v.startswith(("http://", "https://")):
        return AssetKind.URL
    try:
        ipaddress.ip_address(normalize_host(v))
        return AssetKind.IP
    except ValueError:
        pass
    return AssetKind.SUBDOMAIN if normalize_host(v).count(".") >= 2 else AssetKind.DOMAIN


def dedup_key(kind: str, value: str) -> tuple[str, str]:
    if kind in (AssetKind.URL,):
        return (kind, normalize_url(value))
    if kind == AssetKind.IP:
        try:
            return (kind, ipaddress.ip_address(normalize_host(value)).compressed)
        except ValueError:
            return (kind, normalize_host(value))
    return (kind, normalize_host(value))


def url_to_asset_kind_and_value(url: str) -> tuple[str, str]:
    """Map a discovered URL onto the most specific stable identity."""
    return AssetKind.URL, normalize_url(url)


def parent_domain_of(host: str) -> str:
    host = normalize_host(host)
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])
