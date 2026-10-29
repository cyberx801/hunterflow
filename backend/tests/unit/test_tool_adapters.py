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
