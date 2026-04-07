"""Feature tests — exercise real dependencies, no mocks.

These tests hit the network (YouTube, web) and real file parsers (PDF).
Run with: pytest tests/test_features.py -v
Skip in CI with: pytest -m "not integration"
"""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest

from wikismith.config import load_config

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path, vault: Path = None) -> "Config":
    vault = vault or tmp_path / "vault"
    vault.mkdir(exist_ok=True)
    wiki = tmp_path / "wiki"
    cfg_file = tmp_path / "wikismith.yaml"
    cfg_file.write_text(dedent(f"""\
        version: 1
        source:
          path: "{vault}"
        output:
          path: "{wiki}"
        clip:
          output_path: "Clippings/{{year}}/{{month_num}} - {{month_abbr}}"
          filename_template: "{{date}} - {{domain}} - {{title}}"
    """))
    return load_config(cfg_file)


# ===========================================================================
# Feature: Web clipping — real HTTP fetch
# ===========================================================================

class TestWebClipFeature:
    """Clip a real web page via HTTP."""

    def test_clip_wikipedia_article(self, tmp_path: Path):
        from wikismith.clip.web import clip_web

        config = _make_config(tmp_path)
        rel_dir, filename, note = clip_web("https://en.wikipedia.org/wiki/Obsidian", config)

        # Produces a valid note
        assert note.startswith("---\n")
        assert "title:" in note
        assert "source: https://en.wikipedia.org/wiki/Obsidian" in note
        assert filename.endswith(".md")

        # Extracted real content (not just HTML boilerplate)
        assert "obsidian" in note.lower()
        assert len(note) > 500, "Note should contain substantial content"

    def test_clip_web_writes_to_vault(self, tmp_path: Path):
        from wikismith.clip.web import clip_web

        config = _make_config(tmp_path)
        rel_dir, filename, note = clip_web("https://en.wikipedia.org/wiki/Markdown", config)

        # Write to vault like the CLI would
        vault = config.source.path
        out_dir = vault / rel_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        out_path.write_text(note, encoding="utf-8")

        assert out_path.exists()
        assert out_path.stat().st_size > 500
        content = out_path.read_text()
        assert "---" in content
        assert "markdown" in content.lower()


# ===========================================================================
# Feature: YouTube clipping — real yt-dlp + transcript API
# ===========================================================================

class TestYouTubeClipFeature:
    """Clip a real YouTube video with yt-dlp and transcript extraction.

    Uses a short, stable, well-known video with captions.
    """

    # Karpathy's "Intro to Large Language Models" (1hr, has captions, unlikely to be deleted)
    STABLE_VIDEO_URL = "https://www.youtube.com/watch?v=zjkBMFhNj_g"
    # Shorter fallback: 3Blue1Brown "But what is a neural network?" (~19min)
    FALLBACK_VIDEO_URL = "https://www.youtube.com/watch?v=aircAruvnKk"

    def _pick_video(self):
        """Use the primary video, fall back if unavailable."""
        return self.STABLE_VIDEO_URL

    def test_extract_video_metadata_via_ytdlp(self, tmp_path: Path):
        """yt-dlp can fetch metadata for a real video."""
        import json
        import subprocess

        url = self._pick_video()
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings", url],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": str(Path.home() / "dev/wikismith/.venv/bin") + ":" + os.environ["PATH"]},
        )
        assert result.returncode == 0, f"yt-dlp failed: {result.stderr}"

        meta = json.loads(result.stdout)
        assert "title" in meta
        assert "id" in meta
        assert "channel" in meta
        assert "duration" in meta
        assert meta["duration"] > 0

    def test_fetch_transcript_for_real_video(self):
        """youtube-transcript-api can fetch a transcript."""
        from wikismith.clip.youtube import extract_video_id

        url = self._pick_video()
        video_id = extract_video_id(url)
        assert video_id is not None

        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Should have at least one transcript available
        found = False
        for tr in transcript_list:
            found = True
            break
        assert found, "No transcripts available for this video"

        # Fetch the first available transcript
        tr = next(iter(transcript_list))
        snippets = tr.fetch()
        assert len(snippets) > 10, "Transcript should have many snippets"

        # Snippets have text and timestamps
        first = snippets[0]
        assert hasattr(first, "text") or "text" in first
        assert hasattr(first, "start") or "start" in first

    def test_build_youtube_note_from_real_data(self, tmp_path: Path):
        """Full pipeline: fetch metadata + transcript, build note."""
        import json
        import subprocess

        from wikismith.clip.youtube import build_youtube_note, extract_video_id, format_timestamp

        url = self._pick_video()
        video_id = extract_video_id(url)
        config = _make_config(tmp_path)

        # Fetch metadata
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-warnings", url],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": str(Path.home() / "dev/wikismith/.venv/bin") + ":" + os.environ["PATH"]},
        )
        meta = json.loads(result.stdout)

        # Fetch transcript
        transcript = []
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            tlist = api.list(video_id)
            tr = next(iter(tlist))
            for s in tr.fetch():
                text = getattr(s, "text", None)
                start = getattr(s, "start", 0.0)
                if text:
                    transcript.append({"start": start, "text": text.replace("\n", " ").strip()})
        except Exception:
            pass

        assert len(transcript) > 0, "Should have fetched transcript"

        # Build the note
        rel_dir, filename, note = build_youtube_note(meta, transcript, "Test summary.", config)

        # Validate structure
        assert note.startswith("---\n")
        assert "type: youtube" in note
        assert f"Youtube_ID" in note
        assert video_id in note
        assert meta["title"] in note or meta["title"][:30] in note
        assert "Summary of Transcript" in note
        assert "Test summary." in note
        assert "Transcript (Youtube)" in note
        assert filename.endswith(".md")
        assert "youtube.com" in filename

        # Transcript content is present
        first_line = transcript[0]["text"]
        assert first_line[:20] in note

        # Write it and verify
        out_dir = tmp_path / "vault" / rel_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        out_path.write_text(note, encoding="utf-8")
        assert out_path.stat().st_size > 1000, "YouTube note should be substantial"


# ===========================================================================
# Feature: PDF clipping — real PDF parsing
# ===========================================================================

class TestPDFClipFeature:
    """Clip a real PDF file using pymupdf4llm."""

    def test_clip_real_pdf(self, tmp_path: Path):
        """Parse a known PDF and extract text content."""
        from wikismith.clip.pdf import clip_pdf

        # Use the closing disclosure PDF from Downloads if it exists,
        # otherwise create a minimal test PDF
        real_pdf = Path.home() / "Downloads" / "M1013 final JOHNSON CD.PDF"
        if real_pdf.exists():
            pdf_path = real_pdf
        else:
            pdf_path = self._create_test_pdf(tmp_path)

        config = _make_config(tmp_path)
        rel_dir, filename, note = clip_pdf(pdf_path, config)

        assert note.startswith("---\n")
        assert "title:" in note
        assert "tags:" in note
        assert filename.endswith(".md")
        # Should have extracted real text content
        body = note.split("---\n", 2)[-1]
        assert len(body.strip()) > 100, f"PDF extraction should produce substantial text, got {len(body.strip())} chars"

    def test_clip_pdf_writes_to_vault(self, tmp_path: Path):
        from wikismith.clip.pdf import clip_pdf

        pdf_path = self._create_test_pdf(tmp_path)
        config = _make_config(tmp_path)
        rel_dir, filename, note = clip_pdf(pdf_path, config)

        vault = config.source.path
        out_dir = vault / rel_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        out_path.write_text(note, encoding="utf-8")

        assert out_path.exists()
        content = out_path.read_text()
        assert "Feature test PDF" in content or "test" in content.lower()

    @staticmethod
    def _create_test_pdf(tmp_path: Path) -> Path:
        """Create a minimal PDF with pymupdf for testing."""
        import fitz  # pymupdf

        pdf_path = tmp_path / "test-document.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Feature test PDF document.\n\nThis is paragraph one with real content about knowledge management systems.\n\nParagraph two discusses the architecture of wiki compilers and how they process raw documents into structured output.")
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path


# ===========================================================================
# Feature: Local file clipping — real file I/O
# ===========================================================================

class TestLocalClipFeature:
    """Clip local files through the full pipeline."""

    def test_clip_markdown_with_frontmatter(self, tmp_path: Path):
        from wikismith.clip.local import clip_local

        config = _make_config(tmp_path)
        md_file = tmp_path / "research-notes.md"
        md_file.write_text(dedent("""\
            ---
            title: Research Notes on RAG
            tags: [ai, rag, knowledge-base]
            ---

            # RAG Systems

            Retrieval-Augmented Generation combines search with LLM generation.

            ## Key Components

            1. Document store
            2. Embedding model
            3. Vector database
            4. Generator model
        """))

        rel_dir, filename, note = clip_local(md_file, config)

        assert "title: Research Notes on RAG" in note
        assert "tags:" in note
        assert "RAG Systems" in note
        assert "Vector database" in note

    def test_clip_plain_text(self, tmp_path: Path):
        from wikismith.clip.local import clip_local

        config = _make_config(tmp_path)
        txt_file = tmp_path / "meeting-notes.txt"
        txt_file.write_text("Meeting with team about Q2 roadmap.\nDecided to prioritize the wiki compiler project.\nAction items: set up repo, write tests, implement clip pipeline.")

        rel_dir, filename, note = clip_local(txt_file, config)

        assert note.startswith("---\n")
        assert "title:" in note
        assert "meeting-notes" in note.lower() or "Meeting with team" in note
        assert "wiki compiler" in note
        assert filename.endswith(".md")

    def test_clip_html_file(self, tmp_path: Path):
        from wikismith.clip.local import clip_local

        config = _make_config(tmp_path)
        html_file = tmp_path / "saved-page.html"
        html_file.write_text(dedent("""\
            <html>
            <head><title>Saved Article</title></head>
            <body>
                <script>trackPageView();</script>
                <article>
                    <h1>Understanding Embeddings</h1>
                    <p>Embeddings are dense vector representations of text that capture semantic meaning.</p>
                    <p>They enable similarity search across large document collections.</p>
                </article>
                <footer>Copyright 2026</footer>
            </body>
            </html>
        """))

        rel_dir, filename, note = clip_local(html_file, config)

        assert note.startswith("---\n")
        assert "Embeddings" in note or "embeddings" in note
        assert "semantic meaning" in note
        assert "<script>" not in note
        assert "trackPageView" not in note
        assert "<footer>" not in note


# ===========================================================================
# Feature: Clip router — end-to-end dispatch
# ===========================================================================

class TestClipRouterFeature:
    """Route real sources through the full pipeline."""

    def test_route_local_md(self, tmp_path: Path):
        from wikismith.clip import route_clip

        config = _make_config(tmp_path)
        md_file = tmp_path / "vault" / "test.md"
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_text("# Test\n\nReal content for routing test.")

        rel_dir, filename, note = route_clip(str(md_file), config)
        assert "Real content" in note
        assert filename.endswith(".md")

    def test_route_local_pdf(self, tmp_path: Path):
        from wikismith.clip import route_clip

        config = _make_config(tmp_path)
        pdf_path = TestPDFClipFeature._create_test_pdf(tmp_path)

        rel_dir, filename, note = route_clip(str(pdf_path), config)
        assert note.startswith("---\n")
        assert filename.endswith(".md")
        body = note.split("---\n", 2)[-1]
        assert len(body.strip()) > 50

    def test_route_web_url(self, tmp_path: Path):
        from wikismith.clip import route_clip

        config = _make_config(tmp_path)
        rel_dir, filename, note = route_clip("https://en.wikipedia.org/wiki/Markdown", config)
        assert "markdown" in note.lower()
        assert filename.endswith(".md")


# ===========================================================================
# Feature: Compile — source scanning with real filesystem
# ===========================================================================

class TestCompileScanFeature:
    """Scan real directory structures."""

    def test_scan_vault_with_nested_structure(self, tmp_path: Path):
        from wikismith.compile import scan_sources

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        (vault / ".obsidian" / "app.json").write_text("{}")
        (vault / "_wiki").mkdir()
        (vault / "_wiki" / "old-index.md").write_text("# Old")
        (vault / ".trash").mkdir()
        (vault / ".trash" / "deleted.md").write_text("# Deleted")
        (vault / "notes").mkdir()
        (vault / "notes" / "deep").mkdir()
        (vault / "notes" / "deep" / "nested.md").write_text("# Nested")
        (vault / "notes" / "top-level.md").write_text("# Top Level")
        (vault / "clippings").mkdir()
        (vault / "clippings" / "article.md").write_text("# Article")

        config = _make_config(tmp_path, vault)
        sources = scan_sources(config)

        names = {Path(s).name for s in sources}
        assert "nested.md" in names
        assert "top-level.md" in names
        assert "article.md" in names
        # Excluded directories
        assert "app.json" not in names
        assert "old-index.md" not in names
        assert "deleted.md" not in names

    def test_scan_computes_real_hashes(self, tmp_path: Path):
        from wikismith.compile import scan_sources
        from wikismith.utils import content_hash

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "a.md").write_text("Content A")
        (vault / "b.md").write_text("Content B")

        config = _make_config(tmp_path, vault)
        sources = scan_sources(config)

        # Verify we can hash every scanned file
        for rel in sources:
            full = vault / rel
            h = content_hash(full.read_text())
            assert h.startswith("sha256:")
            assert len(h) > 10


# ===========================================================================
# Feature: Lint — real filesystem checks
# ===========================================================================

class TestLintFeature:
    """Run lint checks against real file structures."""

    def test_full_lint_cycle(self, tmp_path: Path):
        """Create a vault with known issues and verify lint catches them all."""
        import time
        from wikismith.lint import run_lint

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "notes").mkdir()
        (vault / "notes" / "covered.md").write_text("# Covered\n\nThis has a concept.")
        (vault / "notes" / "uncovered.md").write_text("# Uncovered\n\nNo concept covers this.")
        (vault / "notes" / "stale-source.md").write_text("# Original content")

        wiki = vault / "_wiki"
        wiki.mkdir()
        (wiki / "concepts").mkdir()

        # Article for 'covered' — valid
        (wiki / "concepts" / "covered-concept.md").write_text(
            "---\ntitle: Covered Concept\nsources:\n  - notes/covered.md\n---\n\nArticle."
        )

        # Article referencing deleted source — orphaned
        (wiki / "concepts" / "orphan.md").write_text(
            "---\ntitle: Orphan\nsources:\n  - notes/deleted-file.md\n---\n\nOrphan article."
        )

        # Article for stale-source — we'll make the source newer
        (wiki / "concepts" / "stale-concept.md").write_text(
            "---\ntitle: Stale Concept\nsources:\n  - notes/stale-source.md\n---\n\nStale article."
        )
        time.sleep(0.1)
        (vault / "notes" / "stale-source.md").write_text("# Updated content!!!")

        (wiki / "_index.md").write_text("# Index")

        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text(dedent(f"""\
            version: 1
            source:
              path: "{vault}"
              exclude:
                - "_wiki/**"
            output:
              path: "{wiki}"
        """))
        config = load_config(cfg_file)

        report = run_lint(config)

        types = {f["type"] for f in report.findings}
        assert "orphaned_article" in types, f"Should detect orphaned article, got: {report.findings}"
        assert "coverage_gap" in types, f"Should detect uncovered source, got: {report.findings}"
        assert "stale_content" in types, f"Should detect stale article, got: {report.findings}"

        # Verify specific findings
        orphan_details = [f["detail"] for f in report.findings if f["type"] == "orphaned_article"]
        assert any("deleted-file" in d for d in orphan_details)

        gap_details = [f["detail"] for f in report.findings if f["type"] == "coverage_gap"]
        assert any("uncovered" in d for d in gap_details)

        stale_details = [f["detail"] for f in report.findings if f["type"] == "stale_content"]
        assert any("stale-source" in d for d in stale_details)


# ===========================================================================
# Feature: State — real file round-trip
# ===========================================================================

class TestStateFeature:
    """State persistence with real file I/O and change detection."""

    def test_incremental_state_across_compiles(self, tmp_path: Path):
        """Simulate two compile cycles and verify change detection works."""
        from wikismith.state import CompileState, detect_changes
        from wikismith.utils import content_hash

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "a.md").write_text("Version 1 of A")
        (vault / "b.md").write_text("Version 1 of B")

        # First "compile" — hash everything
        hashes_v1 = {
            "a.md": content_hash((vault / "a.md").read_text()),
            "b.md": content_hash((vault / "b.md").read_text()),
        }
        state = CompileState(source_hashes=hashes_v1, last_compile="2026-04-07T12:00:00Z")
        state_file = tmp_path / ".wikismith" / "state.json"
        state.save(state_file)

        # Modify a.md, add c.md, delete b.md
        (vault / "a.md").write_text("Version 2 of A — modified!")
        (vault / "c.md").write_text("Brand new file C")
        (vault / "b.md").unlink()

        # Second "compile" — hash again
        hashes_v2 = {}
        for f in vault.glob("*.md"):
            hashes_v2[f.name] = content_hash(f.read_text())

        loaded = CompileState.load(state_file)
        added, changed, deleted = detect_changes(loaded.source_hashes, hashes_v2)

        assert "c.md" in added
        assert "a.md" in changed
        assert "b.md" in deleted
