"""CLI entrypoint for wikismith."""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint

app = typer.Typer(
    name="wikismith",
    help="LLM-powered wiki compiler for Obsidian vaults.",
    no_args_is_help=True,
)

DEFAULT_CONFIG = """\
# wikismith.yaml — configuration for your wiki compiler
# See https://github.com/mattyj718/wikismith for full docs.

version: 1
name: "My Knowledge Base"

source:
  path: "."                              # path to your Obsidian vault or source folder
  include:
    - "**/*.md"
  exclude:
    - ".obsidian/**"
    - "_wiki/**"
    - ".trash/**"

output:
  path: "./_wiki"                        # where compiled wiki goes
  path_template: "concepts/{slug}.md"
  index_file: "_index.md"
  sources_file: "_sources.md"

compile:
  max_concepts: 150
  language: "en"
  strategy: "incremental"                # incremental | full
  parallel: 5

clip:
  output_path: "Storage/Clippings/{year}/{month_num} - {month_abbr}"
  filename_template: "{date} - {domain} - {title}"

llm:
  provider: "anthropic"
  compile_model: "claude-sonnet-4-6"
  query_model: "claude-sonnet-4-6"
  lint_model: "claude-haiku-4-5-20251001"
  api_key_env: "ANTHROPIC_API_KEY"

state:
  path: ".wikismith/"
"""


@app.command()
def init() -> None:
    """Initialize a new wikismith project in the current directory."""
    config_path = Path("wikismith.yaml")
    if config_path.exists():
        rprint("[red]Error:[/red] wikismith.yaml already exists in this directory.")
        raise typer.Exit(code=1)
    config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    rprint("[green]Created wikismith.yaml[/green]")


@app.command()
def clip(
    source: str = typer.Argument(..., help="URL, file path, or PDF to clip into the vault"),
    config: str = typer.Option("wikismith.yaml", "--config", "-c", help="Path to config file"),
    template: str = typer.Option(None, "--template", "-t", help="Force a specific template name"),
    list_templates: bool = typer.Option(False, "--list-templates", help="List available clip templates"),
) -> None:
    """Clip a URL, PDF, or local file into the vault."""
    rprint(f"[dim]clip: {source}[/dim]")
    raise typer.Exit(code=0)


@app.command()
def compile(
    config: str = typer.Option("wikismith.yaml", "--config", "-c", help="Path to config file"),
    full: bool = typer.Option(False, "--full", help="Force full recompile (ignore incremental state)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be compiled without writing"),
) -> None:
    """Compile source notes into a structured wiki."""
    rprint("[dim]compile: not yet implemented[/dim]")
    raise typer.Exit(code=0)


@app.command()
def query(
    question: str = typer.Argument(..., help="Question to ask against the wiki"),
    config: str = typer.Option("wikismith.yaml", "--config", "-c", help="Path to config file"),
    save: bool = typer.Option(False, "--save", help="Save the answer to a file in the wiki"),
) -> None:
    """Query the compiled wiki knowledge base."""
    rprint("[dim]query: not yet implemented[/dim]")
    raise typer.Exit(code=0)


@app.command()
def lint(
    config: str = typer.Option("wikismith.yaml", "--config", "-c", help="Path to config file"),
    deep: bool = typer.Option(False, "--deep", help="Use LLM for deeper analysis (costs tokens)"),
) -> None:
    """Run health checks on the compiled wiki."""
    rprint("[dim]lint: not yet implemented[/dim]")
    raise typer.Exit(code=0)
