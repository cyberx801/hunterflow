"""Tool detection and availability (HF-FR-021, Settings page)."""

from __future__ import annotations

import shutil

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..db.models import Tool
from ..integrations.tools.registry import ADAPTERS


def _binary_for(tool_name: str, settings: Settings) -> str | None:
    bundled = settings.data_dir.parent / "tools" / tool_name / tool_name
    if bundled.exists():
        return str(bundled)
    return shutil.which(tool_name)


def detect_all(db: Session, settings: Settings) -> list[Tool]:
    rows: list[Tool] = []
    for name, adapter in ADAPTERS.items():
        binary = _binary_for(name, settings)
        tool = db.scalar(select(Tool).where(Tool.name == name))
        if tool is None:
            tool = Tool(name=name)
            db.add(tool)
        if binary:
            info = adapter.detect(binary)
            if info is not None:
                tool.available = True
                tool.path = binary
                tool.version = info.version
            else:
                tool.available = False
                tool.path = binary
                tool.version = None
        else:
            tool.available = False
            tool.path = None
            tool.version = None
        rows.append(tool)
    db.commit()
    return rows
