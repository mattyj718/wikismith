---
name: wiki-compile
description: Compile raw Obsidian vault notes into a structured, interlinked wiki. Use when the user says "compile wiki", "update wiki", "rebuild wiki", "process my notes", or wants to turn raw notes/clippings into organized concept articles. Also activates when the user mentions wikismith compilation. This skill uses YOUR reasoning (session tokens) instead of external API calls.
---

# Wiki Compile

Compile source notes from an Obsidian vault into a structured wiki of interlinked concept articles.

## Setup

1. Read `wikismith.yaml` from the project root (or `$WIKISMITH_CONFIG`). If it doesn't exist, tell the user to run `wikismith init` first.
2. Read the state file at `{output.path}/.wikismith/state.json` if it exists.

## Compilation Steps

### 1. Scan Sources
Use Glob to find all `.md` files under `{source.path}` matching the include patterns. Exclude anything matching exclude patterns (`.obsidian/`, `_wiki/`, `.trash/`).

### 2. Detect Changes
For each source file, compute a SHA-256 hash of its content. Compare against `state.json`:
- **New files**: hash not in state
- **Changed files**: hash differs from state
- **Deleted files**: in state but not on disk
- **Unchanged files**: skip these (incremental mode)

If `--full` flag is set, treat all files as new.

If no changes detected, report "Wiki is up to date" and stop.

### 3. Read Changed Sources
Read the content of all new/changed source files.

### 4. Extract Concepts
From the source content, identify the key concepts, topics, and themes. For each concept, determine:
- `id`: a URL-safe slug (lowercase, hyphens, no path separators)
- `title`: human-readable title
- `summary`: 1-2 sentence summary
- `related_sources`: which source files discuss this concept

Cap at `{compile.max_concepts}` concepts. Aim for concepts that are distinct and meaningful, not one per source file.

### 5. Generate Articles
For each concept, write a wiki article as a markdown file at `{output.path}/concepts/{id}.md`:

```markdown
---
title: {title}
sources:
  - {source1}
  - {source2}
generated: {today's date}
---

# {title}

{Synthesized article content drawing from the source material.
Cross-reference related concepts with [[concept-id]] wikilinks.}

---

## Sources

- [[{source1}]]
- [[{source2}]]
```

The `sources:` frontmatter list is for programmatic use (lint, compile state). The `## Sources` section at the bottom renders as clickable `[[wikilinks]]` in Obsidian so users can navigate directly to the original notes.

### 6. Generate Index
Write `{output.path}/_index.md`:

```markdown
# Wiki Index

| Concept | Summary |
|---|---|
| [[concept-id|Title]] | Summary text |
```

Sorted alphabetically by title.

### 7. Generate Sources Catalog
Write `{output.path}/_sources.md` listing all source files and which concepts reference them.

### 8. Update State
Write the updated state to `{output.path}/.wikismith/state.json` with current source hashes and concept metadata.

### 9. Clean Up
Remove any concept article files in `concepts/` that are no longer in the concept list.

### 10. Report
Tell the user: X new articles, Y updated, Z removed.

## Important Rules
- NEVER use raw LLM concept IDs as filenames without slugifying. Always strip `..`, `/`, `\` and special characters.
- Write articles in `{compile.language}` (default: English).
- Use `[[wikilinks]]` for cross-references between concepts.
- Keep articles focused and concise. Each should be self-contained but linked.
