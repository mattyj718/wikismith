"""Utility functions: slugify, content_hash, to_frontmatter, sanitize_filename."""

from __future__ import annotations

import hashlib
import re
import unicodedata

import yaml

INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def slugify(text: str, max_len: int = 200) -> str:
    """Convert text to a safe, lowercase, hyphenated slug for use as filenames/IDs.

    Strips path traversal components, normalizes unicode, and collapses separators.
    """
    # Normalize unicode (e.g., cafe\u0301 -> caf\u00e9 -> cafe)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Lowercase
    text = text.lower()
    # Replace path separators and dots with hyphens
    text = re.sub(r"[/\\.]", "-", text)
    # Replace anything that isn't alphanumeric or hyphen with hyphen
    text = re.sub(r"[^a-z0-9-]", "-", text)
    # Collapse consecutive hyphens
    text = re.sub(r"-{2,}", "-", text)
    # Strip leading/trailing hyphens
    text = text.strip("-")
    # Truncate
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "untitled"


def content_hash(text: str) -> str:
    """Return a SHA-256 hash of the text content, prefixed with 'sha256:'."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{h}"


def to_frontmatter(data: dict) -> str:
    """Convert a dict to a YAML frontmatter block (--- delimited).

    Excludes keys with None or empty string values.
    """
    filtered = {k: v for k, v in data.items() if v is not None and v != ""}
    dumped = yaml.dump(filtered, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{dumped}---\n"


def sanitize_filename(name: str, max_len: int = 180) -> str:
    """Sanitize a string for use as a filename, preserving spaces and casing.

    Strips filesystem-unsafe characters but keeps the name human-readable.
    """
    # Replace invalid characters with spaces
    trans = {ord(c): " " for c in INVALID_FILENAME_CHARS}
    name = name.translate(trans)
    # Remove control characters
    name = re.sub(r"[\x00-\x1f\x7f]", " ", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Strip trailing dots and spaces
    name = name.rstrip(" .")
    # Truncate
    if len(name) > max_len:
        name = name[:max_len].rstrip(" .")
    return name or "Untitled"
