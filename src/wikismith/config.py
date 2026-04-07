"""Configuration loading from YAML with dataclass defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class SourceConfig:
    path: Path = field(default_factory=lambda: Path("."))
    include: List[str] = field(default_factory=lambda: ["**/*.md"])
    exclude: List[str] = field(default_factory=lambda: [".obsidian/**", "_wiki/**", ".trash/**"])


@dataclass
class OutputConfig:
    path: Path = field(default_factory=lambda: Path("./_wiki"))
    path_template: str = "concepts/{slug}.md"
    index_file: str = "_index.md"
    sources_file: str = "_sources.md"


@dataclass
class CompileConfig:
    max_concepts: int = 150
    language: str = "en"
    strategy: str = "incremental"
    parallel: int = 5


@dataclass
class ClipConfig:
    output_path: str = "Storage/Clippings/{year}/{month_num} - {month_abbr}"
    filename_template: str = "{date} - {domain} - {title}"
    clipper_settings: Optional[str] = None
    download_images: bool = True


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    compile_model: str = "claude-sonnet-4-6"
    query_model: str = "claude-sonnet-4-6"
    lint_model: str = "claude-haiku-4-5-20251001"
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: Optional[str] = None

    def get_api_key(self) -> Optional[str]:
        return os.environ.get(self.api_key_env)


@dataclass
class StateConfig:
    path: str = ".wikismith/"


@dataclass
class Config:
    version: int = 1
    name: str = "My Knowledge Base"
    source: SourceConfig = field(default_factory=SourceConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    compile: CompileConfig = field(default_factory=CompileConfig)
    clip: ClipConfig = field(default_factory=ClipConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    state: StateConfig = field(default_factory=StateConfig)


def _merge_dataclass(dc_class, data: dict):
    """Create a dataclass instance from a dict, ignoring unknown keys."""
    if not data:
        return dc_class()
    valid_fields = {f.name for f in dc_class.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    return dc_class(**filtered)


def load_config(path: Path) -> Config:
    """Load configuration from a YAML file, applying defaults for missing fields."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text) or {}

    config = Config(
        version=raw.get("version", 1),
        name=raw.get("name", "My Knowledge Base"),
        source=_merge_dataclass(SourceConfig, raw.get("source")),
        output=_merge_dataclass(OutputConfig, raw.get("output")),
        compile=_merge_dataclass(CompileConfig, raw.get("compile")),
        clip=_merge_dataclass(ClipConfig, raw.get("clip")),
        llm=_merge_dataclass(LLMConfig, raw.get("llm")),
        state=_merge_dataclass(StateConfig, raw.get("state")),
    )

    # Resolve paths to absolute
    config.source.path = Path(config.source.path).resolve()
    config.output.path = Path(config.output.path).resolve()

    return config
