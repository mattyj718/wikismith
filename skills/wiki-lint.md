---
name: wiki-lint
description: Run health checks on the compiled wiki. Use when the user says "lint wiki", "check wiki health", "audit wiki", "wiki quality check", or wants to find issues, inconsistencies, or gaps in their knowledge base. Also activates on /wiki-lint.
---

# Wiki Lint

Run health checks on the compiled wiki to find quality issues.

## Steps

1. Read `wikismith.yaml` to find source and output paths.
2. Scan source files (same logic as compile).
3. Read all concept articles from `{output.path}/concepts/`.
4. Parse each article's frontmatter to get its `sources:` list.

## Checks

### Orphaned Articles
Articles that reference source files which no longer exist. These concepts may be stale or based on deleted content.

### Coverage Gaps
Source files that are not referenced by any concept article. These notes exist in the vault but haven't been compiled into the wiki.

### Stale Content
Source files that have been modified more recently than the concept articles that reference them. The articles may need recompilation.

### Missing Backlinks (if --deep)
Concept articles that mention other concepts by name but don't use `[[wikilinks]]` to link them.

### Duplicate Concepts (if --deep)
Multiple concept articles that cover substantially the same topic and could be merged.

## Output

Report findings as a markdown checklist:

```markdown
## Wiki Health Report

### Orphaned Articles (X found)
- [ ] `concept-name` references missing source: `path/to/deleted.md`

### Coverage Gaps (X found)
- [ ] `path/to/uncovered.md` is not referenced by any concept

### Stale Content (X found)
- [ ] `source.md` is newer than article `concept-name`

### Summary
X issues found. Run `wikismith compile` to fix stale content and coverage gaps.
```

If no issues found, report "Wiki is healthy. No issues found."
