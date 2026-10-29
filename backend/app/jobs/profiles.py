"""Scan profiles: declarative ordered pipelines (HF-FR-022).

Each step names a tool and options. Targets are filtered through the scope
policy before every step; `vuln_checks` requires an explicit curated template
selection (Constitution P4).
"""

from __future__ import annotations

PROFILES: dict[str, dict] = {
    "passive": {
        "label": "Passive Discovery",
        "description": "Passive subdomain enumeration only. No requests to discovered targets.",
        "steps": [{"tool": "subfinder", "options": {}}],
    },
    "light_recon": {
        "label": "Light Recon",
        "description": "Passive enumeration, DNS resolution, and low-impact HTTP probing.",
        "steps": [
            {"tool": "subfinder", "options": {}},
            {"tool": "dnsx", "options": {}},
            {"tool": "httpx", "options": {}},
        ],
    },
    "web_inventory": {
        "label": "Web Inventory",
        "description": "Enumeration, DNS, probing, passive URL discovery, and authorized crawling.",
        "steps": [
            {"tool": "subfinder", "options": {}},
            {"tool": "dnsx", "options": {}},
            {"tool": "httpx", "options": {}},
            {"tool": "gau", "options": {}},
            {"tool": "katana", "options": {}},
        ],
    },
    "url_discovery": {
        "label": "Passive URL Discovery",
        "description": "Subdomain enumeration plus historical URL discovery from public sources. No requests to targets.",
        "steps": [
            {"tool": "subfinder", "options": {}},
            {"tool": "gau", "options": {}},
        ],
    },
    "vuln_checks": {
        "label": "Vulnerability Checks",
        "description": "Explicitly selected safe scanner templates only. Requires template selection.",
        "steps": [{"tool": "nuclei", "options": {}}],
        "requires_templates": True,
    },
}

CURATED_TEMPLATES: dict[str, dict] = {
    # category -> template-id -> {name, severity, safe: true}
    "exposure": {
        "http/exposures/configs/git-config.yaml": {
            "name": "Git Configuration File Exposure",
            "severity": "low",
            "safe": True,
        },
        "http/exposures/files/phpinfo.yaml": {
            "name": "phpinfo Page Exposure",
            "severity": "info",
            "safe": True,
        },
    },
    "misconfig": {
        "http/misconfiguration/cors/cors-allow-all.yaml": {
            "name": "CORS Allow All",
            "severity": "low",
            "safe": True,
        },
    },
}


def resolve_profile(profile: str, templates: list[str] | None = None) -> dict:
    if profile not in PROFILES:
        raise KeyError(f"Unknown scan profile: {profile}")
    spec = dict(PROFILES[profile])
    if spec.get("requires_templates"):
        selected = templates or []
        unknown = [t for t in selected if not any(t in group for group in CURATED_TEMPLATES.values())]
        if unknown:
            raise ValueError(f"Templates not in curated subset: {unknown}")
        if not selected:
            raise ValueError("vuln_checks requires explicit template selection")
        steps = []
        for step in spec["steps"]:
            steps.append({**step, "options": {**step.get("options", {}), "templates": selected}})
        spec["steps"] = steps
    return spec
