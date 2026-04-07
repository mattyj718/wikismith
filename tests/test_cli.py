"""Tests for wikismith.cli — CLI skeleton and init command."""

from __future__ import annotations

from pathlib import Path

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
