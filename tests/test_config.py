"""Tests for wikismith.config — YAML loading and dataclass defaults."""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest

from wikismith.config import Config, load_config


FULL_YAML = dedent("""\
    version: 1
    name: "Test KB"

    source:
      path: "/tmp/vault"
      include:
        - "**/*.md"
      exclude:
        - ".obsidian/**"

    output:
      path: "/tmp/vault/_wiki"
      path_template: "concepts/{slug}.md"
      index_file: "_index.md"
      sources_file: "_sources.md"

    compile:
      max_concepts: 100
      language: "en"
      strategy: "incremental"
      parallel: 3

    clip:
      output_path: "Clippings/{year}/{month_num} - {month_abbr}"
      filename_template: "{date} - {domain} - {title}"

    llm:
      provider: "anthropic"
      compile_model: "claude-sonnet-4-6"
      query_model: "claude-sonnet-4-6"
      lint_model: "claude-haiku-4-5-20251001"
      api_key_env: "ANTHROPIC_API_KEY"

    state:
      path: ".wikismith/"
""")


class TestLoadConfig:
    def test_load_full_config(self, tmp_path: Path):
        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text(FULL_YAML)
        config = load_config(cfg_file)
        assert config.name == "Test KB"
        assert config.source.path == Path("/tmp/vault").resolve()
        assert config.output.path == Path("/tmp/vault/_wiki").resolve()
        assert config.compile.max_concepts == 100
        assert config.compile.language == "en"
        assert config.compile.parallel == 3
        assert config.llm.provider == "anthropic"

    def test_defaults_applied(self, tmp_path: Path):
        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text("version: 1\nname: Minimal\n")
        config = load_config(cfg_file)
        assert config.compile.language == "en"
        assert config.compile.max_concepts == 150
        assert config.compile.parallel == 5
        assert config.compile.strategy == "incremental"
        assert config.output.index_file == "_index.md"
        assert config.output.sources_file == "_sources.md"

    def test_empty_file_returns_defaults(self, tmp_path: Path):
        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text("")
        config = load_config(cfg_file)
        assert config.compile.language == "en"
        assert config.name == "My Knowledge Base"

    def test_source_path_resolved_to_absolute(self, tmp_path: Path):
        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text("version: 1\nsource:\n  path: ./relative/path\n")
        config = load_config(cfg_file)
        assert config.source.path.is_absolute()

    def test_api_key_env_reads_from_env(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-123")
        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text("version: 1\nllm:\n  api_key_env: TEST_API_KEY\n")
        config = load_config(cfg_file)
        assert config.llm.api_key_env == "TEST_API_KEY"
        assert config.llm.get_api_key() == "sk-test-123"

    def test_api_key_env_missing_returns_none(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_KEY", raising=False)
        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text("version: 1\nllm:\n  api_key_env: NONEXISTENT_KEY\n")
        config = load_config(cfg_file)
        assert config.llm.get_api_key() is None

    def test_invalid_yaml_raises(self, tmp_path: Path):
        cfg_file = tmp_path / "wikismith.yaml"
        cfg_file.write_text(":\n  invalid: [yaml\n  broken")
        with pytest.raises(Exception):
            load_config(cfg_file)

    def test_file_not_found_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")
