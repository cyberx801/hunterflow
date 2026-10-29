"""Tool adapter base: detection, argument construction, output parsing.

Security rules (HF-SEC-010, ADR-004):
- Arguments are always lists; never shell strings; never concatenate untrusted input.
- Adapters are the only place tool binaries are referenced.
- build_args output is redacted before persistence.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolInfo:
    name: str
    version: str
    path: str


@dataclass
class Observation:
    kind: str  # subdomain | web_probe | endpoint | scanner_finding
    payload: dict
    source: str = ""  # tool name


@dataclass
class StepContext:
    """Everything a tool step needs to run against one target set."""

    targets: list[str] = field(default_factory=list)  # hostnames or URLs, policy-approved
    output_json: bool = True
    rate_limit: int | None = None  # requests per second
    timeout_seconds: int = 600
    extra: dict = field(default_factory=dict)

    def add(self, *args: str) -> list[str]:
        return list(args)


class ToolAdapter(Protocol):
    name: str

    def detect(self, binary: str) -> ToolInfo | None: ...

    def build_args(self, ctx: StepContext, binary: str) -> list[str]: ...

    def parse(self, stdout: bytes, ctx: StepContext) -> Iterable[Observation]: ...
