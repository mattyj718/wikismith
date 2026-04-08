"""YouTube video clipping: metadata, transcript, note builder."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from wikismith.config import Config
from wikismith.utils import sanitize_filename


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    u = urlparse(url)
    host = u.netloc.replace("www.", "")
    if host == "youtu.be":
        return u.path.strip("/") or None
    if "youtube.com" in host:
        qs = parse_qs(u.query)
        ids = qs.get("v")
        return ids[0] if ids else None
    return None


def format_timestamp(seconds: float) -> str:
    """Format seconds as M:SS or H:MM:SS."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def build_youtube_note(
    meta: dict,
    transcript: List[dict],
    summary: Optional[str],
    config: Config,
) -> Tuple[str, str, str]:
    """Build an Obsidian note for a YouTube video. Returns (rel_dir, filename, note)."""
    today = dt.date.today()
    video_id = meta.get("id", "")
    title = meta.get("title", "Untitled")
    description = (meta.get("description") or "").strip()
    channel = meta.get("channel") or meta.get("uploader") or ""
    channel_url = meta.get("channel_url") or ""
    upload_date_raw = meta.get("upload_date") or ""
    duration_str = meta.get("duration_string") or ""
    webpage_url = meta.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}"

    upload_date = ""
    if upload_date_raw and len(upload_date_raw) == 8:
        upload_date = f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:8]}"

    # Frontmatter
    fm_lines = ["---"]
    fm_props = [
        ("type", "youtube"),
        ("URL", webpage_url),
        ("URL_Retrieved", today.strftime("%Y-%m-%d")),
        ("URL_Published", upload_date),
        ("URL_Title", title),
        ("Youtube_Channel_Name", channel),
        ("Youtube_Channel_URL", channel_url),
        ("Youtube_ID", video_id),
        ("Youtube_Duration", duration_str),
        ("speakers", ""),
    ]
    for key, val in fm_props:
        if isinstance(val, str) and val and any(c in val for c in ':#[]{}|>*&!%@`"\',?'):
            fm_lines.append(f'{key}: "{val}"')
        else:
            fm_lines.append(f"{key}: {val}")
    fm_lines.extend(["tags:", "  - youtube", "  - clippings", "---"])

    # Body
    embed_url = f"https://www.youtube.com/embed/{video_id}"
    body = [
        "",
        f"# {title}",
        "",
        f"![{title}]({embed_url})",
        "",
    ]

    if description:
        body.append("> [!summary]+ Description")
        for ln in description.split("\n"):
            body.append(f"> {ln}")
        body.append("")

    body.append("> [!summary]+ Summary of Transcript")
    if summary:
        for ln in summary.split("\n"):
            body.append(f"> {ln}")
    elif transcript:
        body.append("> [summary placeholder]")
    else:
        body.append("> No transcript available for summarization.")
    body.append("")

    if transcript:
        body.append("> [!transcript]- Transcript (Youtube)")
        for snip in transcript:
            ts = format_timestamp(snip["start"])
            body.append(f"> {ts} {snip['text']}")
        body.append("")
    else:
        body.append("> [!warning]+ Transcript")
        body.append("> Transcript unavailable (no captions found).")
        body.append("")

    note = "\n".join(fm_lines) + "\n" + "\n".join(body)

    # Path and filename
    rel_dir = config.clip.output_path.format(
        year=today.strftime("%Y"),
        month_num=today.strftime("%m"),
        month_abbr=today.strftime("%b"),
    )
    safe_title = sanitize_filename(title)
    date_str = today.strftime("%Y-%m-%d")
    parts = [date_str, "youtube.com", safe_title]
    if upload_date:
        parts.append(upload_date)
    filename = " - ".join(parts) + ".md"

    return rel_dir, filename, note


def clip_youtube(url: str, config: Config) -> Tuple[str, str, str]:
    """Fetch YouTube metadata and transcript, build note. Returns (rel_dir, filename, note)."""
    import json
    import subprocess

    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from: {url}")

    canonical = f"https://www.youtube.com/watch?v={video_id}"

    # Metadata via yt-dlp (resolve from same venv as this package)
    import sys
    yt_dlp_bin = str(Path(sys.executable).parent / "yt-dlp")
    result = subprocess.run(
        [yt_dlp_bin, "--dump-json", "--no-download", "--no-warnings", canonical],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
    meta = json.loads(result.stdout)

    # Transcript
    transcript = []
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        tlist = api.list(video_id)
        tr = None
        for lang_codes in [["en", "en-US", "en-GB"]]:
            try:
                tr = tlist.find_transcript(lang_codes)
                break
            except Exception:
                try:
                    tr = tlist.find_generated_transcript(lang_codes)
                    break
                except Exception:
                    pass
        if tr is None:
            try:
                tr = next(iter(tlist))
            except StopIteration:
                tr = None
        if tr:
            for s in tr.fetch():
                text = getattr(s, "text", None)
                start = getattr(s, "start", 0.0)
                if text:
                    transcript.append({"start": start, "text": text.replace("\n", " ").strip()})
    except Exception:
        pass

    return build_youtube_note(meta, transcript, None, config)
