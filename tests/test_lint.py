"""Tests for wikismith.lint — wiki health checks."""

from __future__ import annotations

import time
from pathlib import Path

from wikismith.config import load_config


def _make_wiki_and_sources(tmp_path: Path):
    """Create a vault with sources and a compiled wiki for lint testing."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "notes").mkdir()
    (vault / "notes" / "topic-a.md").write_text("# Topic A\n\nContent A.")
    (vault / "notes" / "topic-b.md").write_text("# Topic B\n\nContent B.")
    (vault / "notes" / "orphan-source.md").write_text("# Orphan\n\nNo concept covers this.")

    wiki = vault / "_wiki"
    wiki.mkdir()
    (wiki / "concepts").mkdir()
    (wiki / "concepts" / "topic-a.md").write_text("---\ntitle: Topic A\nsources:\n  - notes/topic-a.md\n---\n\nArticle A.")
    (wiki / "concepts" / "topic-b.md").write_text("---\ntitle: Topic B\nsources:\n  - notes/topic-b.md\n---\n\nArticle B.")
    (wiki / "concepts" / "orphan-concept.md").write_text("---\ntitle: Orphan Concept\nsources:\n  - notes/deleted.md\n---\n\nOrphan article.")
    (wiki / "_index.md").write_text("# Index\n\ntopic-a, topic-b, orphan-concept")

    # State file
    state_dir = wiki / ".wikismith"
    state_dir.mkdir()

    cfg_file = tmp_path / "wikismith.yaml"
    cfg_file.write_text(f"""\
version: 1
source:
  path: "{vault}"
  exclude:
    - "_wiki/**"
output:
  path: "{wiki}"
""")
    return load_config(cfg_file)


class TestRunLint:
    def test_detects_orphaned_articles(self, tmp_path: Path):
        from wikismith.lint import run_lint
        config = _make_wiki_and_sources(tmp_path)
        report = run_lint(config)
        orphan_findings = [f for f in report.findings if f["type"] == "orphaned_article"]
        assert len(orphan_findings) > 0
        assert any("orphan-concept" in f["detail"] for f in orphan_findings)

    def test_detects_coverage_gaps(self, tmp_path: Path):
        from wikismith.lint import run_lint
        config = _make_wiki_and_sources(tmp_path)
        report = run_lint(config)
        gap_findings = [f for f in report.findings if f["type"] == "coverage_gap"]
        assert len(gap_findings) > 0
        assert any("orphan-source" in f["detail"] for f in gap_findings)

    def test_detects_stale_content(self, tmp_path: Path):
        from wikismith.lint import run_lint
        config = _make_wiki_and_sources(tmp_path)
        # Make source newer than article
        vault = config.source.path
        time.sleep(0.1)
        (vault / "notes" / "topic-a.md").write_text("# Topic A\n\nUpdated content!!!")
        report = run_lint(config)
        stale_findings = [f for f in report.findings if f["type"] == "stale_content"]
        assert len(stale_findings) > 0

    def test_clean_wiki(self, tmp_path: Path):
        from wikismith.lint import run_lint
        vault = tmp_path / "clean_vault"
        vault.mkdir()
        (vault / "notes").mkdir()
        (vault / "notes" / "a.md").write_text("# A")

        wiki = vault / "_wiki"
        wiki.mkdir()
        (wiki / "concepts").mkdir()
        (wiki / "concepts" / "a.md").write_text("---\ntitle: A\nsources:\n  - notes/a.md\n---\n\nArticle A.")
        (wiki / "_index.md").write_text("# Index")

        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text(f"version: 1\nsource:\n  path: \"{vault}\"\n  exclude:\n    - \"_wiki/**\"\noutput:\n  path: \"{wiki}\"\n")
        config = load_config(cfg_file)

        report = run_lint(config)
        assert len(report.findings) == 0
