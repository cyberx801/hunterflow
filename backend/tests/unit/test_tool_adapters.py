"""Adapter tests for dnsx and gau (arg shaping and output parsing)."""

from __future__ import annotations

import json

from app.integrations.tools.base import StepContext
from app.integrations.tools.registry import DnsxAdapter, GauAdapter

CTX = StepContext(
    targets=["api.example.com", "www.example.com"],
    targets_file="/tmp/run/targets.txt",
)


def test_dnsx_build_args_uses_targets_file():
    args = DnsxAdapter().build_args(CTX, "/usr/local/bin/dnsx")
    assert args[0] == "/usr/local/bin/dnsx"
    assert "-json" in args
    assert "-l" in args
    assert args[args.index("-l") + 1] == "/tmp/run/targets.txt"
    assert "api.example.com" not in args  # targets go through the file, not argv


def test_dnsx_parse():
    lines = [
        json.dumps({"host": "api.example.com", "a": ["203.0.113.10"], "status_code": "NOERROR"}),
        json.dumps({"host": "www.example.com", "a": [], "cname": ["edge.example.net"]}),
        "not json",
        "",
    ]
    observations = list(DnsxAdapter().parse("\n".join(lines).encode(), CTX))
    assert len(observations) == 2
    first = observations[0]
    assert first.kind == "dns_record"
    assert first.payload["host"] == "api.example.com"
    assert first.payload["ips"] == ["203.0.113.10"]


def test_gau_build_args_and_parse():
    args = GauAdapter().build_args(CTX, "/usr/local/bin/gau")
    assert args[0] == "/usr/local/bin/gau"
    assert "--json" in args
    assert args[-2:] == ["api.example.com", "www.example.com"]

    stdout = "\n".join(
        [
            json.dumps({"url": "https://api.example.com/v1/orders", "source": "wayback"}),
            "https://www.example.com/login",
            "garbage",
        ]
    )
    observations = list(GauAdapter().parse(stdout.encode(), CTX))
    assert [o.payload["url"] for o in observations] == [
        "https://api.example.com/v1/orders",
        "https://www.example.com/login",
    ]
    assert all(o.kind == "url" for o in observations)


def test_httpx_screenshot_args_and_parse():
    import base64

    from app.integrations.tools.registry import HttpxAdapter

    ctx = StepContext(targets=["http://demo.local:8080"], extra={"screenshots": True})
    args = HttpxAdapter().build_args(ctx, "/usr/local/bin/httpx")
    assert "-screenshot" in args
    assert "-system-chrome" in args

    png = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
    line = (
        '{"url": "http://demo.local:8080", "status_code": 200, "tech": ["nginx"], '
        f'"screenshot_bytes": "{png}"}}'
    )
    observations = list(HttpxAdapter().parse(line.encode(), ctx))
    kinds = [o.kind for o in observations]
    assert "screenshot" in kinds
    shot = next(o for o in observations if o.kind == "screenshot")
    assert shot.payload["bytes_b64"] == png


def test_katana_resolvers_and_scope_args():
    from app.integrations.tools.registry import KatanaAdapter

    ctx = StepContext(
        targets=["http://demo.example.com:8080"],
        extra={
            "no_follow_redirects": True,
            "in_scope_regexes": ["(?i)^https?://demo\\.example\\.com"],
            "resolvers_file": "/tmp/resolvers.txt",
        },
    )
    args = KatanaAdapter().build_args(ctx, "/usr/local/bin/katana")
    assert "-disable-redirects" in args
    assert "-r" in args
    assert args[args.index("-r") + 1] == "/tmp/resolvers.txt"
    assert "-cs" in args
