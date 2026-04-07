"""Local file clipping: import .md, .txt, .html into the vault."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Tuple

from wikismith.config import Config
from wikismith.utils import sanitize_filename, to_frontmatter


def _has_frontmatter(text: str) -> bool:
    """Check if text starts with YAML frontmatter."""
    return text.startswith("---\n")


def clip_local(path: Path, config: Config) -> Tuple[str, str, str]:
    """Import a local file as a vault note. Returns (rel_dir, filename, note)."""
    path = Path(path)
    today = dt.date.today()
    title = path.stem
    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix == ".html" or suffix == ".htm":
        from wikismith.clip.web import strip_html
        content = strip_html(raw)
        note = to_frontmatter({"title": title, "source": str(path), "created": today.strftime("%Y-%m-%d"), "tags": ["clippings"]}) + content.strip() + "\n"
    elif suffix == ".md":
        if _has_frontmatter(raw):
            note = raw
        else:
            fm = to_frontmatter({"title": title, "source": str(path), "created": today.strftime("%Y-%m-%d"), "tags": ["clippings"]})
            note = fm + raw
    else:
        # .txt and other plain text
        note = to_frontmatter({"title": title, "source": str(path), "created": today.strftime("%Y-%m-%d"), "tags": ["clippings"]}) + raw.strip() + "\n"

    filename = sanitize_filename(f"{today.strftime('%Y-%m-%d')} - {title}") + ".md"
    rel_dir = config.clip.output_path.format(
        year=today.strftime("%Y"),
        month_num=today.strftime("%m"),
        month_abbr=today.strftime("%b"),
    )
    return rel_dir, filename, note
