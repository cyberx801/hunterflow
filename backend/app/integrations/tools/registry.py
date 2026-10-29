"""Tool adapters and the registry that owns them (HF-FR-020/021)."""

from __future__ import annotations

import json
from collections.abc import Iterable

from ...core.redaction import redact_text
from .base import Observation, StepContext, ToolAdapter, ToolInfo


def _detect_version(binary: str, flag: str = "--version") -> ToolInfo | None:
    import subprocess

    try:
        proc = subprocess.run(
            [binary, flag],
            capture_output=True,
            timeout=10,
            text=True,
        )
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    version = (proc.stdout or proc.stderr).strip().splitlines()[0]
    return ToolInfo(name="", version=redact_text(version), path=binary)


class SubfinderAdapter:
    name = "subfinder"

    def detect(self, binary: str) -> ToolInfo | None:
        info = _detect_version(binary)
        if info is None:
            return None
        info.name = self.name
        info.version = info.version.replace("subfinder", "").strip()
        return info

    def build_args(self, ctx: StepContext, binary: str) -> list[str]:
        args = [binary, "-silent", "-json"]
        for target in ctx.targets:
            args += ["-d", target]
        if ctx.rate_limit:
            args += ["-rl", str(ctx.rate_limit)]
        return args

    def parse(self, stdout: bytes, ctx: StepContext) -> Iterable[Observation]:
        for line in stdout.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            host = data.get("host")
            if not host:
                continue
            yield Observation(
                kind="subdomain",
                payload={"host": host, "source": data.get("source"), "ips": data.get("ip")},
                source=self.name,
            )


class DnsxAdapter:
    name = "dnsx"

    def detect(self, binary: str) -> ToolInfo | None:
        info = _detect_version(binary)
        if info is None:
            return None
        info.name = self.name
        info.version = info.version.replace("dnsx", "").strip()
        return info

    def build_args(self, ctx: StepContext, binary: str) -> list[str]:
        args = [binary, "-silent", "-json", "-a", "-resp"]
        if ctx.rate_limit:
            args += ["-rl", str(ctx.rate_limit)]
        if ctx.targets_file:
            args += ["-l", ctx.targets_file]
        return args

    def parse(self, stdout: bytes, ctx: StepContext) -> Iterable[Observation]:
        for line in stdout.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            host = data.get("host")
            if not host:
                continue
            yield Observation(
                kind="dns_record",
                payload={
                    "host": host,
                    "ips": data.get("a") or [],
                    "cname": data.get("cname") or [],
                    "status_code": data.get("status_code"),
                },
                source=self.name,
            )


class HttpxAdapter:
    name = "httpx"

    def detect(self, binary: str) -> ToolInfo | None:
        info = _detect_version(binary)
        if info is None:
            return None
        info.name = self.name
        info.version = info.version.replace("httpx", "").strip()
        return info

    def build_args(self, ctx: StepContext, binary: str) -> list[str]:
        args = [
            binary,
            "-silent",
            "-json",
            "-no-color",
            "-status-code",
            "-title",
            "-tech-detect",
        ]
        # httpx does not follow redirects unless -follow-redirects is passed;
        # out-of-scope redirect following is prohibited, so we never enable it.
        if ctx.extra.get("screenshots"):
            args += ["-screenshot", "-system-chrome"]
        if ctx.rate_limit:
            args += ["-rl", str(ctx.rate_limit)]
        for target in ctx.targets:
            args += ["-u", target]
        return args

    def parse(self, stdout: bytes, ctx: StepContext) -> Iterable[Observation]:
        for line in stdout.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = data.get("url")
            if not url:
                continue
            yield Observation(
                kind="web_probe",
                payload={
                    "url": url,
                    "status_code": data.get("status_code"),
                    "tech": data.get("tech") or [],
                    "title": data.get("title"),
                    "ip": data.get("a") or (data.get("a", [])),
                    "host": data.get("host"),
                },
                source=self.name,
            )
            screenshot = data.get("screenshot_bytes")
            if screenshot:
                yield Observation(
                    kind="screenshot",
                    payload={"url": url, "bytes_b64": screenshot},
                    source=self.name,
                )


class GauAdapter:
    """Passive URL discovery from public sources (Wayback, Common Crawl, OTX).

    These are historical URLs, not live requests: results are stored as URL
    assets for the inventory and are not probed automatically.
    """

    name = "gau"

    def detect(self, binary: str) -> ToolInfo | None:
        info = _detect_version(binary, flag="-version")
        if info is None:
            return None
        info.name = self.name
        info.version = info.version.replace("gau", "").strip()
        return info

    def build_args(self, ctx: StepContext, binary: str) -> list[str]:
        args = [binary, "--json", "--subs", "--threads", "3", "--timeout", "20"]
        for target in ctx.targets:
            args.append(target)
        return args

    def parse(self, stdout: bytes, ctx: StepContext) -> Iterable[Observation]:
        for line in stdout.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            url = None
            source = None
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    url = data.get("url") or data.get("URL")
                    source = data.get("source")
            except json.JSONDecodeError:
                if line.startswith(("http://", "https://")):
                    url = line
            if not url or not str(url).startswith(("http://", "https://")):
                continue
            yield Observation(
                kind="url",
                payload={"url": url, "source": source},
                source=self.name,
            )


class KatanaAdapter:
    name = "katana"

    def detect(self, binary: str) -> ToolInfo | None:
        info = _detect_version(binary)
        if info is None:
            return None
        info.name = self.name
        info.version = info.version.replace("katana", "").strip()
        return info

    def build_args(self, ctx: StepContext, binary: str) -> list[str]:
        args = [binary, "-silent", "-jsonl", "-no-color"]
        if ctx.rate_limit:
            args += ["-rl", str(ctx.rate_limit)]
        if ctx.extra.get("no_follow_redirects", True):
            args.append("-disable-redirects")
        # Scope enforcement inside katana: in-scope regexes derived from policy.
        in_scope = ctx.extra.get("in_scope_regexes") or []
        out_scope = ctx.extra.get("out_of_scope_regexes") or []
        if in_scope:
            args += ["-cs", "|".join(in_scope)]
        if out_scope:
            args += ["-cos", "|".join(out_scope)]
        if ctx.extra.get("resolvers_file"):
            args += ["-r", ctx.extra["resolvers_file"]]
        for target in ctx.targets:
            args += ["-u", target]
        return args

    def parse(self, stdout: bytes, ctx: StepContext) -> Iterable[Observation]:
        for line in stdout.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            request = data.get("request") or {}
            url = request.get("endpoint") or data.get("endpoint") or data.get("url")
            if not url:
                continue
            response = data.get("response") or {}
            yield Observation(
                kind="endpoint",
                payload={
                    "url": url,
                    "method": request.get("method", "GET"),
                    "request_headers": request.get("headers") or {},
                    "response_status": response.get("status_code"),
                    "response_headers": response.get("headers") or {},
                    "content_type": (response.get("headers") or {}).get("content_type"),
                    "category_hints": [],
                },
                source=self.name,
            )


class NucleiAdapter:
    name = "nuclei"

    def detect(self, binary: str) -> ToolInfo | None:
        info = _detect_version(binary)
        if info is None:
            return None
        info.name = self.name
        info.version = info.version.replace("nuclei", "").strip()
        return info

    def build_args(self, ctx: StepContext, binary: str) -> list[str]:
        args = [binary, "-silent", "-jsonl", "-no-color", "-dr"]
        if ctx.extra.get("no_interactsh", True):
            args.append("-no-interactsh")
        if ctx.rate_limit:
            args += ["-rl", str(ctx.rate_limit)]
        templates = ctx.extra.get("templates") or []
        if templates:
            args += ["-t", ",".join(templates)]
        for target in ctx.targets:
            args += ["-u", target]
        return args

    def parse(self, stdout: bytes, ctx: StepContext) -> Iterable[Observation]:
        for line in stdout.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield Observation(
                kind="scanner_finding",
                payload={
                    "template_id": data.get("template-id"),
                    "name": (data.get("info") or {}).get("name"),
                    "severity": (data.get("info") or {}).get("severity"),
                    "matched_at": data.get("matched-at"),
                    "matcher_name": data.get("matcher-name"),
                    "extracted_results": data.get("extracted-results"),
                },
                source=self.name,
            )


ADAPTERS: dict[str, ToolAdapter] = {
    "subfinder": SubfinderAdapter(),
    "dnsx": DnsxAdapter(),
    "httpx": HttpxAdapter(),
    "gau": GauAdapter(),
    "katana": KatanaAdapter(),
    "nuclei": NucleiAdapter(),
}


def get_adapter(name: str) -> ToolAdapter:
    adapter = ADAPTERS.get(name)
    if adapter is None:
        raise KeyError(f"Unknown tool adapter: {name}")
    return adapter


