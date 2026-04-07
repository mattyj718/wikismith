"""Web URL clipping: fetch, extract, build note."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from wikismith.config import Config
from wikismith.utils import sanitize_filename, to_frontmatter


def extract_meta(html: str) -> dict:
    """Extract metadata from HTML via meta tags and <title>."""
    def find_meta(prop: str) -> str | None:
        m = re.search(
            rf'(?is)<meta[^>]+(?:property|name)=["\']{ re.escape(prop)}["\'][^>]+content=["\'](.*?)["\']',
            html,
        )
        return m.group(1).strip() if m else None

    title = None
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()

    title = find_meta("og:title") or title
    desc = find_meta("description") or find_meta("og:description")
    author = find_meta("author")
    published = find_meta("article:published_time") or find_meta("og:article:published_time")

    return {"title": title, "description": desc, "author": author, "published": published}


def extract_main_html(html: str) -> str:
    """Best-effort: prefer <article>, then <main>, then full body."""
    for tag in ("article", "main"):
        m = re.search(rf"(?is)<{tag}[^>]*>(.*?)</{tag}>", html)
        if m and len(m.group(1)) > 200:
            return m.group(1)
    return html


def strip_html(html: str) -> str:
    """Strip HTML tags, scripts, styles; decode entities; normalize whitespace."""
    html = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)</?(p|div|br|hr|h\d|li|ul|ol|section|article|header|footer|blockquote|pre)[^>]*>", "\n", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = (
        html.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in html.splitlines()]
    out = []
    for ln in lines:
        if not ln:
            if out and out[-1] != "":
                out.append("")
            continue
        out.append(ln)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build_clip(
    url: str,
    html: str,
    meta: dict,
    config: Config,
) -> Tuple[str, str, str]:
    """Build a clipped note. Returns (relative_dir, filename, note_content)."""
    today = dt.date.today()
    title = meta.get("title") or urlparse(url).netloc
    domain = urlparse(url).netloc

    content = strip_html(extract_main_html(html))

    tmpl = config.clip.filename_template
    filename_base = tmpl.format(date=today.strftime("%Y-%m-%d"), domain=domain, title=title)
    filename = sanitize_filename(filename_base) + ".md"

    rel_dir = config.clip.output_path.format(
        year=today.strftime("%Y"),
        month_num=today.strftime("%m"),
        month_abbr=today.strftime("%b"),
    )

    fm_data = {
        "title": title,
        "source": url,
        "created": today.strftime("%Y-%m-%d"),
        "tags": ["clippings"],
    }
    if meta.get("author"):
        fm_data["author"] = meta["author"]
    if meta.get("published"):
        fm_data["published"] = meta["published"]
    if meta.get("description"):
        fm_data["description"] = meta["description"]

    note = to_frontmatter(fm_data) + content + "\n"
    return rel_dir, filename, note


def clip_web(url: str, config: Config) -> Tuple[str, str, str]:
    """Fetch a URL and clip it. Returns (relative_dir, filename, note_content)."""
    import httpx
    resp = httpx.get(url, timeout=30, follow_redirects=True, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Wikismith/0.1; +https://github.com/mattyj718/wikismith)",
    })
    resp.raise_for_status()
    html = resp.text
    meta = extract_meta(html)
    return build_clip(url, html, meta, config)
