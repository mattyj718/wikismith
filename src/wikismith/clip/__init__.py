"""Clip sources into the vault. Routes to the appropriate handler."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from wikismith.config import Config


def _is_url(source: str) -> bool:
    try:
        parsed = urlparse(source)
        return parsed.scheme in ("http", "https")
    except Exception:
        return False


def _is_youtube(url: str) -> bool:
    host = urlparse(url).netloc.replace("www.", "")
    return host in ("youtube.com", "youtu.be", "m.youtube.com")


def route_clip(source: str, config: Config) -> Tuple[str, str, str]:
    """Route a clip source to the appropriate handler. Returns (rel_dir, filename, note)."""
    if _is_url(source):
        if _is_youtube(source):
            from wikismith.clip.youtube import clip_youtube
            return clip_youtube(source, config)
        else:
            from wikismith.clip.web import clip_web
            return clip_web(source, config)

    path = Path(source)
    if path.exists():
        if path.suffix.lower() == ".pdf":
            from wikismith.clip.pdf import clip_pdf
            return clip_pdf(path, config)
        else:
            from wikismith.clip.local import clip_local
            return clip_local(path, config)

    raise ValueError(f"Cannot clip '{source}': not a valid URL or existing file path.")
