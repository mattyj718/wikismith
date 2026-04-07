"""Tests for wikismith.cli — CLI skeleton, init, and wired commands."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from wikismith.cli import app

runner = CliRunner()


class TestCLISkeleton:
    def test_help_exits_zero(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_lists_commands(self):
        result = runner.invoke(app, ["--help"])
        output = result.output.lower()
        assert "clip" in output
        assert "compile" in output
        assert "query" in output
        assert "lint" in output
        assert "init" in output

    def test_clip_command_exists(self):
        result = runner.invoke(app, ["clip", "--help"])
        assert result.exit_code == 0

    def test_compile_command_exists(self):
        result = runner.invoke(app, ["compile", "--help"])
        assert result.exit_code == 0

    def test_query_command_exists(self):
        result = runner.invoke(app, ["query", "--help"])
        assert result.exit_code == 0

    def test_lint_command_exists(self):
        result = runner.invoke(app, ["lint", "--help"])
        assert result.exit_code == 0


class TestInitCommand:
    def test_init_creates_config(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "wikismith.yaml").exists()

    def test_init_no_overwrite(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "wikismith.yaml").write_text("existing: true")
        result = runner.invoke(app, ["init"])
        assert result.exit_code != 0 or "already exists" in result.output.lower()
        # Original content preserved
        assert (tmp_path / "wikismith.yaml").read_text() == "existing: true"


class TestClipCLI:
    """Test that the clip command actually calls the clip pipeline (not just --help)."""

    def _write_config(self, tmp_path: Path) -> Path:
        vault = tmp_path / "vault"
        vault.mkdir()
        cfg = tmp_path / "wikismith.yaml"
        cfg.write_text(dedent(f"""\
            version: 1
            source:
              path: "{vault}"
            output:
              path: "{vault}/_wiki"
            clip:
              output_path: "Clippings"
              filename_template: "{{date}} - {{title}}"
        """))
        return cfg

    def test_clip_local_md_produces_file(self, tmp_path: Path):
        cfg = self._write_config(tmp_path)
        src = tmp_path / "raw-note.md"
        src.write_text("# Test Note\n\nSome content for the CLI test.")

        result = runner.invoke(app, ["clip", str(src), "--config", str(cfg)])

        assert result.exit_code == 0, f"clip failed: {result.output}"
        # Output should print the file path
        assert ".md" in result.output
        # File should exist in vault
        vault = tmp_path / "vault"
        clipped = list(vault.rglob("*.md"))
        assert len(clipped) >= 1
        content = clipped[0].read_text()
        assert "Test Note" in content or "Some content" in content

    def test_clip_local_txt_produces_file(self, tmp_path: Path):
        cfg = self._write_config(tmp_path)
        src = tmp_path / "notes.txt"
        src.write_text("Plain text meeting notes about the roadmap.")

        result = runner.invoke(app, ["clip", str(src), "--config", str(cfg)])

        assert result.exit_code == 0, f"clip failed: {result.output}"
        vault = tmp_path / "vault"
        clipped = list(vault.rglob("*.md"))
        assert len(clipped) >= 1
        content = clipped[0].read_text()
        assert "---" in content  # has frontmatter
        assert "roadmap" in content

    def test_clip_invalid_source_fails(self, tmp_path: Path):
        cfg = self._write_config(tmp_path)
        result = runner.invoke(app, ["clip", "not-a-url-or-file", "--config", str(cfg)])
        assert result.exit_code != 0
