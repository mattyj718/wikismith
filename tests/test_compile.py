"""Tests for wikismith.compile — source scanning, concept extraction, article generation, full pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wikismith.config import load_config


def _make_vault(tmp_path: Path) -> Path:
    """Create a fixture vault with sample files."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "config.json").write_text("{}")
    (vault / "_wiki").mkdir()
    (vault / "notes").mkdir()
    (vault / "notes" / "topic-a.md").write_text("# Topic A\n\nContent about topic A and its details.")
    (vault / "notes" / "topic-b.md").write_text("# Topic B\n\nContent about topic B and how it relates to A.")
    (vault / "clippings").mkdir()
    (vault / "clippings" / "article.md").write_text("---\ntitle: Clipped Article\n---\n\nSome clipped content.")
    return vault


def _make_config(tmp_path: Path, vault: Path) -> "Config":
    cfg_file = tmp_path / "wikismith.yaml"
    wiki_path = vault / "_wiki"
    cfg_file.write_text(f"""\
version: 1
name: Test
source:
  path: "{vault}"
  include:
    - "**/*.md"
  exclude:
    - ".obsidian/**"
    - "_wiki/**"
output:
  path: "{wiki_path}"
compile:
  max_concepts: 50
  language: en
  strategy: incremental
  parallel: 2
""")
    return load_config(cfg_file)


# ===========================================================================
# Step 3.1: Source scanning
# ===========================================================================

class TestScanSources:
    def test_returns_relative_paths(self, tmp_path: Path):
        from wikismith.compile import scan_sources
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)
        sources = scan_sources(config)
        assert all(not Path(s).is_absolute() for s in sources)

    def test_finds_all_md_files(self, tmp_path: Path):
        from wikismith.compile import scan_sources
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)
        sources = scan_sources(config)
        names = {Path(s).name for s in sources}
        assert "topic-a.md" in names
        assert "topic-b.md" in names
        assert "article.md" in names

    def test_excludes_obsidian_dir(self, tmp_path: Path):
        from wikismith.compile import scan_sources
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)
        sources = scan_sources(config)
        assert all(".obsidian" not in s for s in sources)

    def test_excludes_wiki_dir(self, tmp_path: Path):
        from wikismith.compile import scan_sources
        vault = _make_vault(tmp_path)
        # Put a file in _wiki
        (vault / "_wiki" / "index.md").write_text("# Index")
        config = _make_config(tmp_path, vault)
        sources = scan_sources(config)
        assert all("_wiki" not in s for s in sources)

    def test_empty_vault(self, tmp_path: Path):
        from wikismith.compile import scan_sources
        vault = tmp_path / "empty_vault"
        vault.mkdir()
        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text(f"version: 1\nsource:\n  path: \"{vault}\"\n")
        config = load_config(cfg_file)
        sources = scan_sources(config)
        assert sources == []


# ===========================================================================
# Step 3.2: Concept extraction (mocked LLM)
# ===========================================================================

MOCK_CONCEPTS_RESPONSE = [
    {"id": "topic-a", "title": "Topic A", "summary": "About topic A.", "related_sources": ["notes/topic-a.md"]},
    {"id": "topic-b", "title": "Topic B", "summary": "About topic B.", "related_sources": ["notes/topic-b.md"]},
    {"id": "../../.env", "title": "Evil", "summary": "Path traversal attempt.", "related_sources": []},
]


class TestExtractConcepts:
    def test_returns_concepts(self, tmp_path: Path):
        from wikismith.compile import extract_concepts
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)
        sources = {"notes/topic-a.md": "# Topic A\n\nContent.", "notes/topic-b.md": "# Topic B\n\nContent."}

        with patch("wikismith.compile._call_llm_extract", return_value=MOCK_CONCEPTS_RESPONSE):
            concepts = extract_concepts(sources, config)

        assert len(concepts) >= 2
        ids = {c["id"] for c in concepts}
        assert "topic-a" in ids
        assert "topic-b" in ids

    def test_concept_ids_slugified(self, tmp_path: Path):
        from wikismith.compile import extract_concepts
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)

        with patch("wikismith.compile._call_llm_extract", return_value=MOCK_CONCEPTS_RESPONSE):
            concepts = extract_concepts({"a.md": "content"}, config)

        for c in concepts:
            assert ".." not in c["id"]
            assert "/" not in c["id"]

    def test_respects_max_concepts(self, tmp_path: Path):
        from wikismith.compile import extract_concepts
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)
        config.compile.max_concepts = 1

        many = [{"id": f"c{i}", "title": f"C{i}", "summary": ".", "related_sources": []} for i in range(10)]
        with patch("wikismith.compile._call_llm_extract", return_value=many):
            concepts = extract_concepts({"a.md": "content"}, config)

        assert len(concepts) <= 1

    def test_empty_sources(self, tmp_path: Path):
        from wikismith.compile import extract_concepts
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)
        concepts = extract_concepts({}, config)
        assert concepts == []


# ===========================================================================
# Step 3.3: Article generation (mocked LLM)
# ===========================================================================

class TestGenerateArticle:
    def test_returns_markdown_with_frontmatter(self, tmp_path: Path):
        from wikismith.compile import generate_article
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)
        concept = {"id": "topic-a", "title": "Topic A", "summary": "About A.", "related_sources": ["notes/topic-a.md"]}
        sources = {"notes/topic-a.md": "# Topic A\n\nDetailed content about A."}

        mock_article = "---\ntitle: Topic A\nsources:\n  - notes/topic-a.md\n---\n\n# Topic A\n\nSynthesized article about Topic A.\n\nRelated: [[topic-b]]\n\n---\n\n## Sources\n\n- [[notes/topic-a.md]]\n"
        with patch("wikismith.compile._call_llm_article", return_value=mock_article):
            result = generate_article(concept, sources, ["topic-a", "topic-b"], config)

        assert "---" in result
        assert "Topic A" in result
        assert "## Sources" in result
        assert "[[notes/topic-a.md]]" in result


# ===========================================================================
# Step 3.4: Index generation
# ===========================================================================

class TestGenerateIndex:
    def test_index_has_concepts(self):
        from wikismith.compile import generate_index
        concepts = [
            {"id": "topic-b", "title": "Topic B", "summary": "About B."},
            {"id": "topic-a", "title": "Topic A", "summary": "About A."},
        ]
        result = generate_index(concepts)
        assert "Topic A" in result
        assert "Topic B" in result
        # Should be sorted alphabetically
        assert result.index("Topic A") < result.index("Topic B")

    def test_index_empty_concepts(self):
        from wikismith.compile import generate_index
        result = generate_index([])
        assert "# Wiki Index" in result

    def test_sources_catalog(self):
        from wikismith.compile import generate_sources_catalog
        hashes = {"notes/a.md": "sha256:aaa", "notes/b.md": "sha256:bbb"}
        concepts = [
            {"id": "c1", "title": "C1", "summary": ".", "related_sources": ["notes/a.md"]},
            {"id": "c2", "title": "C2", "summary": ".", "related_sources": ["notes/a.md", "notes/b.md"]},
        ]
        result = generate_sources_catalog(hashes, concepts)
        assert "notes/a.md" in result
        assert "notes/b.md" in result


# ===========================================================================
# Step 3.5: Full compile pipeline (integration, mocked LLM)
# ===========================================================================

class TestRunCompile:
    def test_first_compile_creates_wiki(self, tmp_path: Path):
        from wikismith.compile import run_compile
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)

        mock_concepts = [
            {"id": "topic-a", "title": "Topic A", "summary": "About A.", "related_sources": ["notes/topic-a.md"]},
        ]
        mock_article = "---\ntitle: Topic A\nsources:\n  - notes/topic-a.md\n---\n\n# Topic A\n\nArticle content.\n\n---\n\n## Sources\n\n- [[notes/topic-a.md]]\n"

        with patch("wikismith.compile._call_llm_extract", return_value=mock_concepts), \
             patch("wikismith.compile._call_llm_article", return_value=mock_article):
            result = run_compile(config)

        assert result.new > 0
        wiki_dir = config.output.path
        assert (wiki_dir / "_index.md").exists()
        assert (wiki_dir / "_sources.md").exists()
        assert (wiki_dir / "concepts" / "topic-a.md").exists()

    def test_incremental_noop(self, tmp_path: Path):
        from wikismith.compile import run_compile
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)

        mock_concepts = [
            {"id": "topic-a", "title": "Topic A", "summary": "About A.", "related_sources": ["notes/topic-a.md"]},
        ]
        mock_article = "---\ntitle: Topic A\nsources:\n  - notes/topic-a.md\n---\n\n# Topic A\n\nArticle.\n\n---\n\n## Sources\n\n- [[notes/topic-a.md]]\n"

        with patch("wikismith.compile._call_llm_extract", return_value=mock_concepts), \
             patch("wikismith.compile._call_llm_article", return_value=mock_article):
            run_compile(config)

        # Second compile with no changes
        with patch("wikismith.compile._call_llm_extract") as mock_extract:
            result = run_compile(config)
            # Should NOT call the LLM again
            mock_extract.assert_not_called()

        assert result.new == 0
        assert result.updated == 0
        assert result.removed == 0

    def test_incremental_detects_changes(self, tmp_path: Path):
        from wikismith.compile import run_compile
        vault = _make_vault(tmp_path)
        config = _make_config(tmp_path, vault)

        mock_concepts = [
            {"id": "topic-a", "title": "Topic A", "summary": "About A.", "related_sources": ["notes/topic-a.md"]},
        ]
        mock_article = "---\ntitle: Topic A\nsources:\n  - notes/topic-a.md\n---\n\n# Topic A\n\nArticle.\n\n---\n\n## Sources\n\n- [[notes/topic-a.md]]\n"

        with patch("wikismith.compile._call_llm_extract", return_value=mock_concepts), \
             patch("wikismith.compile._call_llm_article", return_value=mock_article):
            run_compile(config)

        # Modify a source
        (vault / "notes" / "topic-a.md").write_text("# Topic A\n\nUpdated content!!!")

        with patch("wikismith.compile._call_llm_extract", return_value=mock_concepts), \
             patch("wikismith.compile._call_llm_article", return_value="---\ntitle: Topic A\nsources:\n  - notes/topic-a.md\n---\n\nUpdated.\n\n---\n\n## Sources\n\n- [[notes/topic-a.md]]\n"):
            result = run_compile(config)

        assert result.updated > 0 or result.new > 0
