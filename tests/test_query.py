"""Tests for wikismith.query — Q&A against compiled wiki."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from wikismith.config import load_config


def _make_wiki(tmp_path: Path) -> Path:
    """Create a fixture wiki with index and articles."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "concepts").mkdir()
    (wiki / "_index.md").write_text(
        "# Wiki Index\n\n| Concept | Summary |\n|---|---|\n"
        "| [[topic-a]] | About topic A. |\n"
        "| [[topic-b]] | About topic B. |\n"
    )
    (wiki / "concepts" / "topic-a.md").write_text("---\ntitle: Topic A\n---\n\n# Topic A\n\nDetailed content about A.")
    (wiki / "concepts" / "topic-b.md").write_text("---\ntitle: Topic B\n---\n\n# Topic B\n\nDetailed content about B.")
    return wiki


def _make_config(tmp_path: Path, wiki: Path) -> "Config":
    cfg = tmp_path / "wikismith.yaml"
    cfg.write_text(f"version: 1\nsource:\n  path: \"{tmp_path}\"\noutput:\n  path: \"{wiki}\"\n")
    return load_config(cfg)


class TestRunQuery:
    def test_returns_answer(self, tmp_path: Path):
        from wikismith.query import run_query
        wiki = _make_wiki(tmp_path)
        config = _make_config(tmp_path, wiki)

        mock_answer = "Topic A is about detailed content. See [[topic-a]]."
        with patch("wikismith.query._call_llm_query", return_value=mock_answer):
            result = run_query("What is topic A?", config)

        assert "Topic A" in result
        assert "topic-a" in result

    def test_save_writes_file(self, tmp_path: Path):
        from wikismith.query import run_query
        wiki = _make_wiki(tmp_path)
        config = _make_config(tmp_path, wiki)

        with patch("wikismith.query._call_llm_query", return_value="Answer here."):
            result = run_query("Question?", config, save=True)

        queries_dir = wiki / "queries"
        assert queries_dir.exists()
        files = list(queries_dir.glob("*.md"))
        assert len(files) == 1

    def test_empty_wiki(self, tmp_path: Path):
        from wikismith.query import run_query
        wiki = tmp_path / "empty_wiki"
        wiki.mkdir()
        config = _make_config(tmp_path, wiki)
        result = run_query("Anything?", config)
        assert "no wiki" in result.lower() or "not compiled" in result.lower()
