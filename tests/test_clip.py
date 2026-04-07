"""Tests for wikismith.clip — template loader, web, youtube, pdf, local, router."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wikismith.config import Config, load_config

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helper to build a minimal config for clip tests
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path) -> Config:
    cfg_file = tmp_path / "wikismith.yaml"
    cfg_file.write_text(f"""\
version: 1
source:
  path: "{tmp_path}/vault"
output:
  path: "{tmp_path}/wiki"
clip:
  output_path: "Clippings/{{year}}/{{month_num}} - {{month_abbr}}"
  filename_template: "{{date}} - {{domain}} - {{title}}"
""")
    return load_config(cfg_file)


# ===========================================================================
# Step 2.1: Template loader
# ===========================================================================

class TestTemplateLoader:
    def test_load_templates_from_json(self):
        from wikismith.clip.templates import load_templates
        templates = load_templates(FIXTURES / "clipper_settings.json")
        assert len(templates) == 4

    def test_template_ordering_preserved(self):
        from wikismith.clip.templates import load_templates
        templates = load_templates(FIXTURES / "clipper_settings.json")
        names = [t["name"] for t in templates]
        assert names == ["Default - With Summary", "YouTube Transcript", "GitHub Repository", "Default"]

    def test_match_youtube_url(self):
        from wikismith.clip.templates import load_templates, match_template
        templates = load_templates(FIXTURES / "clipper_settings.json")
        matched = match_template("https://www.youtube.com/watch?v=abc123", templates)
        assert matched["name"] == "YouTube Transcript"

    def test_match_github_url(self):
        from wikismith.clip.templates import load_templates, match_template
        templates = load_templates(FIXTURES / "clipper_settings.json")
        matched = match_template("https://github.com/user/repo", templates)
        assert matched["name"] == "GitHub Repository"

    def test_match_generic_url_falls_back(self):
        from wikismith.clip.templates import load_templates, match_template
        templates = load_templates(FIXTURES / "clipper_settings.json")
        matched = match_template("https://example.com/article", templates)
        assert matched["name"] == "Default - With Summary"

    def test_most_specific_trigger_wins(self):
        from wikismith.clip.templates import load_templates, match_template
        templates = load_templates(FIXTURES / "clipper_settings.json")
        # youtu.be trigger is more specific for short URLs
        matched = match_template("https://youtu.be/abc123", templates)
        assert matched["name"] == "YouTube Transcript"

    def test_no_templates_returns_default(self):
        from wikismith.clip.templates import match_template
        matched = match_template("https://example.com", [])
        assert matched["name"] == "Default"


# ===========================================================================
# Step 2.2: Web clipper
# ===========================================================================

class TestWebClipper:
    def test_extract_meta(self):
        from wikismith.clip.web import extract_meta
        html = (FIXTURES / "sample_article.html").read_text()
        meta = extract_meta(html)
        assert meta["title"] == "Understanding Knowledge Graphs"
        assert "knowledge graphs" in meta["description"].lower()
        assert meta["author"] == "Jane Smith"
        assert meta["published"] == "2026-03-15T10:00:00Z"

    def test_extract_main_html_prefers_article(self):
        from wikismith.clip.web import extract_main_html
        html = (FIXTURES / "sample_article.html").read_text()
        main = extract_main_html(html)
        assert "Knowledge graphs represent" in main
        # Should NOT include nav or footer
        assert "<nav>" not in main

    def test_extract_main_html_fallback(self):
        from wikismith.clip.web import extract_main_html
        html = "<html><body><p>Just some text here that is long enough to be content.</p></body></html>"
        main = extract_main_html(html)
        assert "Just some text" in main

    def test_strip_html_removes_scripts(self):
        from wikismith.clip.web import strip_html
        html = '<p>Hello</p><script>evil();</script><p>World</p>'
        result = strip_html(html)
        assert "evil" not in result
        assert "Hello" in result
        assert "World" in result

    def test_strip_html_removes_styles(self):
        from wikismith.clip.web import strip_html
        html = '<p>Hello</p><style>.x{color:red}</style><p>World</p>'
        result = strip_html(html)
        assert "color" not in result

    def test_strip_html_decodes_entities(self):
        from wikismith.clip.web import strip_html
        html = '<p>Hello &amp; World &lt;3&gt;</p>'
        result = strip_html(html)
        assert "Hello & World <3>" in result

    def test_build_clip(self, tmp_path: Path):
        from wikismith.clip.web import build_clip
        config = _make_config(tmp_path)
        html = (FIXTURES / "sample_article.html").read_text()
        meta = {"title": "Understanding Knowledge Graphs", "description": "A deep dive", "author": "Jane Smith", "published": "2026-03-15"}
        rel_dir, filename, content = build_clip("https://example.com/article", html, meta, config)

        assert "---" in content  # has frontmatter
        assert "title:" in content
        assert "source: https://example.com/article" in content
        assert "Knowledge graphs" in content
        assert filename.endswith(".md")
        # Filename should contain title
        assert "Understanding Knowledge Graphs" in filename

    def test_build_clip_sanitizes_filename(self, tmp_path: Path):
        from wikismith.clip.web import build_clip
        config = _make_config(tmp_path)
        meta = {"title": 'Bad: "Title" <here>', "description": None, "author": None, "published": None}
        _, filename, _ = build_clip("https://example.com", "<html><body>content</body></html>", meta, config)
        assert '"' not in filename
        assert '<' not in filename
        assert '>' not in filename


# ===========================================================================
# Step 2.3: YouTube clipper
# ===========================================================================

class TestYouTubeClipper:
    def test_extract_video_id_standard(self):
        from wikismith.clip.youtube import extract_video_id
        assert extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"

    def test_extract_video_id_short(self):
        from wikismith.clip.youtube import extract_video_id
        assert extract_video_id("https://youtu.be/abc123") == "abc123"

    def test_extract_video_id_mobile(self):
        from wikismith.clip.youtube import extract_video_id
        assert extract_video_id("https://m.youtube.com/watch?v=abc123") == "abc123"

    def test_extract_video_id_non_youtube(self):
        from wikismith.clip.youtube import extract_video_id
        assert extract_video_id("https://example.com/video") is None

    def test_format_timestamp_minutes(self):
        from wikismith.clip.youtube import format_timestamp
        assert format_timestamp(65.0) == "1:05"

    def test_format_timestamp_hours(self):
        from wikismith.clip.youtube import format_timestamp
        assert format_timestamp(3661.0) == "1:01:01"

    def test_format_timestamp_zero(self):
        from wikismith.clip.youtube import format_timestamp
        assert format_timestamp(0.0) == "0:00"

    def test_build_youtube_note_with_transcript(self, tmp_path: Path):
        from wikismith.clip.youtube import build_youtube_note
        config = _make_config(tmp_path)
        meta = {
            "id": "abc123",
            "title": "Test Video",
            "description": "A test video description.",
            "channel": "TestChannel",
            "channel_url": "https://youtube.com/@TestChannel",
            "upload_date": "20260401",
            "duration": 120,
            "duration_string": "2:00",
            "webpage_url": "https://www.youtube.com/watch?v=abc123",
        }
        transcript = [
            {"start": 0.0, "text": "Hello world."},
            {"start": 5.0, "text": "This is a test."},
        ]
        rel_dir, filename, note = build_youtube_note(meta, transcript, "AI summary here.", config)

        assert "type: youtube" in note
        assert "Youtube_ID" in note
        assert "# Test Video" in note
        assert "youtube.com/embed/abc123" in note
        assert "Description" in note
        assert "Summary of Transcript" in note
        assert "AI summary here." in note
        assert "0:00 Hello world." in note
        assert "0:05 This is a test." in note
        assert filename.endswith(".md")
        assert "youtube.com" in filename

    def test_build_youtube_note_no_transcript(self, tmp_path: Path):
        from wikismith.clip.youtube import build_youtube_note
        config = _make_config(tmp_path)
        meta = {
            "id": "xyz789",
            "title": "No Captions Video",
            "description": "",
            "channel": "Ch",
            "channel_url": "",
            "upload_date": "20260101",
            "duration": 60,
            "duration_string": "1:00",
            "webpage_url": "https://www.youtube.com/watch?v=xyz789",
        }
        _, _, note = build_youtube_note(meta, [], None, config)
        assert "Transcript unavailable" in note
        assert "No transcript available" in note or "warning" in note.lower()


# ===========================================================================
# Step 2.4: PDF clipper
# ===========================================================================

class TestPDFClipper:
    def test_clip_pdf_returns_note(self, tmp_path: Path):
        from wikismith.clip.pdf import clip_pdf
        config = _make_config(tmp_path)
        # Create a simple text file pretending to be a PDF (we'll mock the extraction)
        pdf_path = tmp_path / "test-document.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch("wikismith.clip.pdf._extract_pdf_text", return_value="Extracted PDF text content here."):
            rel_dir, filename, note = clip_pdf(pdf_path, config)

        assert "---" in note  # frontmatter
        assert "title:" in note
        assert "Extracted PDF text content" in note
        assert filename.endswith(".md")
        assert "test-document" in filename

    def test_clip_pdf_non_pdf_raises(self, tmp_path: Path):
        from wikismith.clip.pdf import clip_pdf
        config = _make_config(tmp_path)
        txt_path = tmp_path / "not-a-pdf.txt"
        txt_path.write_text("just text")
        with pytest.raises(ValueError, match="[Nn]ot a PDF"):
            clip_pdf(txt_path, config)


# ===========================================================================
# Step 2.5: Local file clipper
# ===========================================================================

class TestLocalClipper:
    def test_clip_md_preserves_frontmatter(self, tmp_path: Path):
        from wikismith.clip.local import clip_local
        config = _make_config(tmp_path)
        md_path = tmp_path / "note.md"
        md_path.write_text("---\ntitle: Existing Note\ntags: [test]\n---\n\nSome content here.")

        rel_dir, filename, note = clip_local(md_path, config)
        assert "title: Existing Note" in note
        assert "Some content here." in note

    def test_clip_md_generates_frontmatter_if_missing(self, tmp_path: Path):
        from wikismith.clip.local import clip_local
        config = _make_config(tmp_path)
        md_path = tmp_path / "raw-note.md"
        md_path.write_text("# Just a heading\n\nSome content.")

        _, _, note = clip_local(md_path, config)
        assert note.startswith("---\n")
        assert "title:" in note
        assert "# Just a heading" in note

    def test_clip_txt_wrapped_in_markdown(self, tmp_path: Path):
        from wikismith.clip.local import clip_local
        config = _make_config(tmp_path)
        txt_path = tmp_path / "notes.txt"
        txt_path.write_text("Plain text notes about something.")

        _, filename, note = clip_local(txt_path, config)
        assert "---" in note
        assert "Plain text notes" in note
        assert filename.endswith(".md")

    def test_clip_html_stripped(self, tmp_path: Path):
        from wikismith.clip.local import clip_local
        config = _make_config(tmp_path)
        html_path = tmp_path / "page.html"
        html_path.write_text("<html><body><p>Hello <b>World</b></p></body></html>")

        _, _, note = clip_local(html_path, config)
        assert "Hello" in note
        assert "World" in note
        assert "<b>" not in note


# ===========================================================================
# Step 2.6: Clip router
# ===========================================================================

class TestClipRouter:
    def test_youtube_url_routes_to_youtube(self, tmp_path: Path):
        from wikismith.clip import route_clip
        config = _make_config(tmp_path)
        with patch("wikismith.clip.youtube.clip_youtube", return_value=("dir", "file.md", "note")) as mock:
            route_clip("https://www.youtube.com/watch?v=abc123", config)
            mock.assert_called_once()

    def test_web_url_routes_to_web(self, tmp_path: Path):
        from wikismith.clip import route_clip
        config = _make_config(tmp_path)
        with patch("wikismith.clip.web.clip_web", return_value=("dir", "file.md", "note")) as mock:
            route_clip("https://example.com/article", config)
            mock.assert_called_once()

    def test_pdf_path_routes_to_pdf(self, tmp_path: Path):
        from wikismith.clip import route_clip
        config = _make_config(tmp_path)
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF")
        with patch("wikismith.clip.pdf.clip_pdf", return_value=("dir", "file.md", "note")) as mock:
            route_clip(str(pdf), config)
            mock.assert_called_once()

    def test_md_path_routes_to_local(self, tmp_path: Path):
        from wikismith.clip import route_clip
        config = _make_config(tmp_path)
        md = tmp_path / "note.md"
        md.write_text("content")
        with patch("wikismith.clip.local.clip_local", return_value=("dir", "file.md", "note")) as mock:
            route_clip(str(md), config)
            mock.assert_called_once()

    def test_invalid_source_raises(self, tmp_path: Path):
        from wikismith.clip import route_clip
        config = _make_config(tmp_path)
        with pytest.raises(ValueError):
            route_clip("not-a-url-or-path", config)
