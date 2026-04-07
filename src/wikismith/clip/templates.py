"""Load and match Obsidian Web Clipper templates."""

from __future__ import annotations

import json
from pathlib import Path


def load_templates(json_path: Path) -> list[dict]:
    """Load templates from an exported Obsidian Web Clipper settings JSON."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    templates = []
    for key, val in data.items():
        if not key.startswith("template_") or not isinstance(val, dict):
            continue
        templates.append({
            "id": val.get("id"),
            "name": val.get("name"),
            "triggers": val.get("triggers") or [],
            "noteNameFormat": val.get("noteNameFormat"),
            "path": val.get("path"),
            "noteContentFormat": val.get("noteContentFormat"),
            "behavior": val.get("behavior"),
        })

    order = data.get("template_list")
    if isinstance(order, list):
        idx = {tid: i for i, tid in enumerate(order)}
        templates.sort(key=lambda t: idx.get(t.get("id"), 10_000))
    else:
        templates.sort(key=lambda t: (t.get("name") or ""))

    return templates


def match_template(url: str, templates: list[dict]) -> dict:
    """Match a URL against template triggers. Most-specific (longest prefix) wins."""
    if not templates:
        return {"name": "Default", "triggers": [], "path": None, "noteNameFormat": None}

    url_triggers = []
    for t in templates:
        for trig in t.get("triggers") or []:
            if isinstance(trig, str) and trig.startswith("http"):
                url_triggers.append((trig, t))

    url_triggers.sort(key=lambda x: len(x[0]), reverse=True)
    for trig, t in url_triggers:
        if url.startswith(trig):
            return t

    # Fallback: "Default - With Summary" or first template
    for t in templates:
        if (t.get("name") or "").strip().lower() == "default - with summary":
            return t
    return templates[0]
