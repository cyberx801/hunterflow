"""Tool-specific target shaping (subfinder gets hosts, others get URLs)."""

from __future__ import annotations

from app.jobs.pipeline import tool_targets


def test_subfinder_gets_bare_hosts():
    targets = ["http://demo.local:8080/a", "https://api.example.com", "plain.example.com"]
    assert tool_targets(targets, "subfinder") == [
        "demo.local",
        "api.example.com",
        "plain.example.com",
    ]


def test_subfinder_deduplicates_hosts():
    assert tool_targets(["http://a.example.com/x", "a.example.com"], "subfinder") == [
        "a.example.com"
    ]


def test_httpx_and_katana_keep_urls():
    targets = ["http://demo.local:8080/a"]
    assert tool_targets(targets, "httpx") == targets
    assert tool_targets(targets, "katana") == targets
    assert tool_targets(targets, "nuclei") == targets


def test_host_tools_get_hosts():
    targets = ["http://demo.local:8080/a"]
    for tool in ("dnsx", "gau"):
        assert tool_targets(targets, tool) == ["demo.local"]
