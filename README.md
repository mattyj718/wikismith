# wikismith

LLM-powered wiki compiler for Obsidian vaults. Inspired by [Karpathy's LLM Knowledge Bases](https://x.com/karpathy/status/2039805659525644595) workflow.

Clip raw sources, compile them into an interlinked markdown wiki, query your knowledge base, and lint for quality. Works standalone or as Claude Code skills.

## How It Works

```
raw sources ──► wikismith compile ──► interlinked wiki ──► Obsidian views it
     ▲                                       │
     │              wikismith query ◄────────┘
     │              wikismith lint  ◄────────┘
     │
wikismith clip (URLs, PDFs, YouTube, local files)
```

1. **Clip** sources into your vault (web articles, YouTube transcripts, PDFs, local files)
2. **Compile** them into a structured wiki with concept articles, backlinks, and an index
3. **Query** the wiki to find answers grounded in your knowledge
4. **Lint** to find stale content, coverage gaps, and orphaned articles

## Install

```bash
pip install -e ".[all]"      # Full install (YouTube, PDF, API support)
pip install -e "."           # Core only (use with Claude Code skills)
pip install -e ".[dev]"      # With test dependencies
```

## Quick Start

```bash
# Initialize a project
cd ~/Documents/MyVault
wikismith init

# Edit wikismith.yaml — set your source path and output path

# Clip some sources
wikismith clip "https://example.com/article"
wikismith clip "https://youtube.com/watch?v=abc123"
wikismith clip ~/Downloads/paper.pdf
wikismith clip ~/notes/raw-notes.md

# Compile the wiki
wikismith compile

# Query it
wikismith query "What do I know about topic X?"

# Check health
wikismith lint
```

## Claude Code Skills

The primary interface. Copy the skill files into your project:

```bash
cp -r skills/ .claude/commands/
```

Then in a Claude Code session:
- `/wiki-compile` compiles using session tokens (free, no API key needed)
- `/wiki-query "question"` answers inline with wiki citations
- `/wiki-lint` runs health checks
- `/wiki-clip <url>` clips with AI-powered YouTube summaries

Skills use Claude's own reasoning instead of separate API calls, so compilation and querying cost nothing beyond your normal Claude Code usage.

## Configuration

See `wikismith.example.yaml` for all options. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `source.path` | `.` | Path to your Obsidian vault |
| `output.path` | `./_wiki` | Where the compiled wiki goes |
| `compile.max_concepts` | 150 | Cap on generated articles |
| `compile.strategy` | `incremental` | `incremental` or `full` |
| `compile.parallel` | 5 | Max concurrent LLM calls |
| `llm.provider` | `anthropic` | For standalone CLI mode |
| `clip.output_path` | `Storage/Clippings/...` | Where clips land |

## CLI Reference

```
wikismith init              Create wikismith.yaml in current directory
wikismith clip <source>     Clip a URL, PDF, or file into the vault
  --template NAME           Force a specific template
  --list-templates          Show available clip templates
wikismith compile           Compile source notes into wiki
  --full                    Force full recompile
  --dry-run                 Show what would change
wikismith query "question"  Query the compiled wiki
  --save                    Save the answer to a file
wikismith lint              Run wiki health checks
  --deep                    Use LLM for deeper analysis
```

## Obsidian Web Clipper Integration

If you use the Obsidian Web Clipper extension, export your settings JSON and point wikismith at it:

```yaml
clip:
  clipper_settings: ~/Downloads/obsidian-web-clipper-settings.json
```

Wikismith will use your existing templates to match URLs and format clips consistently.

## Architecture

```
src/wikismith/
├── cli.py          Typer CLI entrypoint
├── config.py       YAML config with dataclass defaults
├── utils.py        slugify, frontmatter, content hashing
├── state.py        Incremental compile state (SHA-256 content hashes)
├── compile.py      Wiki compilation engine
├── query.py        Q&A engine
├── lint.py         Health check engine
└── clip/
    ├── __init__.py Router (detects source type, dispatches)
    ├── templates.py Obsidian Web Clipper template loader
    ├── web.py      Generic URL clipping
    ├── youtube.py  YouTube metadata + transcript
    ├── pdf.py      PDF text extraction
    └── local.py    Local file import
```

## Design Decisions

- **Incremental compilation** via content hashing (SHA-256). Only changed files trigger recompilation.
- **Concept IDs are always slugified** before becoming filenames. Prevents path traversal from LLM output.
- **No Jina Reader** or third-party content routing. Direct HTTP fetching for privacy.
- **Rate-limited parallelism** with exponential backoff for API mode.
- **Obsidian-compatible output**: `[[wikilinks]]`, YAML frontmatter, callout blocks.

## License

MIT
