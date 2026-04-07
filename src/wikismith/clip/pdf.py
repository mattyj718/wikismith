"""PDF clipping: extract text and build note."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Tuple

from wikismith.config import Config
from wikismith.utils import sanitize_filename, to_frontmatter


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file. Tries pymupdf4llm, falls back to basic."""
    try:
        import pymupdf4llm
        return pymupdf4llm.to_markdown(str(path))
    except ImportError:
        pass

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except ImportError:
        pass

    raise ImportError(
        "PDF extraction requires pymupdf4llm or PyMuPDF. "
        "Install with: pip install 'wikismith[pdf]'"
    )


def clip_pdf(path: Path, config: Config) -> Tuple[str, str, str]:
    """Extract text from a PDF and build a note. Returns (rel_dir, filename, note)."""
    path = Path(path)
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Not a PDF file: {path}")

    text = _extract_pdf_text(path)
    today = dt.date.today()
    title = path.stem

    fm_data = {
        "title": title,
        "source": str(path),
        "created": today.strftime("%Y-%m-%d"),
        "tags": ["clippings", "pdf"],
    }

    note = to_frontmatter(fm_data) + text.strip() + "\n"

    rel_dir = config.clip.output_path.format(
        year=today.strftime("%Y"),
        month_num=today.strftime("%m"),
        month_abbr=today.strftime("%b"),
    )
    filename = sanitize_filename(f"{today.strftime('%Y-%m-%d')} - {title}") + ".md"

    return rel_dir, filename, note
