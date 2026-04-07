"""Lint engine: wiki health checks."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

from wikismith.compile import scan_sources
from wikismith.config import Config


@dataclass
class LintReport:
    findings: List[dict] = field(default_factory=list)


def _parse_article_sources(article_path: Path) -> List[str]:
    """Extract the sources list from an article's YAML frontmatter."""
    text = article_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return []
    end = text.index("---", 4)
    fm = yaml.safe_load(text[4:end])
    if not fm or not isinstance(fm, dict):
        return []
    sources = fm.get("sources", [])
    return sources if isinstance(sources, list) else []


def run_lint(config: Config) -> LintReport:
    """Run health checks on the compiled wiki."""
    report = LintReport()
    source_path = config.source.path
    wiki_path = config.output.path
    concepts_dir = wiki_path / "concepts"

    # Get all source files
    source_files = set(scan_sources(config))

    # Get all concept articles and their declared sources
    article_sources: dict[str, List[str]] = {}
    if concepts_dir.exists():
        for f in concepts_dir.glob("*.md"):
            article_sources[f.stem] = _parse_article_sources(f)

    # All sources referenced by any article
    referenced_sources = set()
    for sources in article_sources.values():
        referenced_sources.update(sources)

    # Check 1: Orphaned articles (reference deleted sources)
    for article_id, sources in article_sources.items():
        for src in sources:
            if src not in source_files:
                report.findings.append({
                    "type": "orphaned_article",
                    "detail": f"Article '{article_id}' references missing source: {src}",
                    "article": article_id,
                    "source": src,
                })

    # Check 2: Coverage gaps (sources not referenced by any article)
    for src in source_files:
        if src not in referenced_sources:
            report.findings.append({
                "type": "coverage_gap",
                "detail": f"Source '{src}' is not referenced by any concept article.",
                "source": src,
            })

    # Check 3: Stale content (source modified after article)
    for article_id, sources in article_sources.items():
        article_path = concepts_dir / f"{article_id}.md"
        article_mtime = article_path.stat().st_mtime
        for src in sources:
            src_path = source_path / src
            if src_path.exists() and src_path.stat().st_mtime > article_mtime:
                report.findings.append({
                    "type": "stale_content",
                    "detail": f"Source '{src}' is newer than article '{article_id}'.",
                    "article": article_id,
                    "source": src,
                })

    return report
