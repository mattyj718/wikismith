"""Wiki compilation engine: scan sources, extract concepts, generate articles."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from wikismith.config import Config
from wikismith.state import CompileState, detect_changes
from wikismith.utils import content_hash, slugify


@dataclass
class CompileResult:
    new: int = 0
    updated: int = 0
    removed: int = 0


def scan_sources(config: Config) -> List[str]:
    """Scan the source vault for files matching include/exclude patterns. Returns relative paths."""
    source_path = config.source.path
    if not source_path.exists():
        return []

    results = []
    for pattern in config.source.include:
        for path in source_path.glob(pattern):
            if not path.is_file():
                continue
            rel = str(path.relative_to(source_path))
            excluded = any(fnmatch.fnmatch(rel, ex) for ex in config.source.exclude)
            if not excluded:
                results.append(rel)

    return sorted(set(results))


def _call_llm_extract(sources_text: str, config: Config) -> List[dict]:
    """Call the LLM to extract concepts from source content. Mockable in tests."""
    raise NotImplementedError("LLM call not implemented for standalone mode yet")


def _call_llm_article(concept: dict, sources_text: str, concept_ids: List[str], config: Config) -> str:
    """Call the LLM to generate a wiki article. Mockable in tests."""
    raise NotImplementedError("LLM call not implemented for standalone mode yet")


def extract_concepts(sources: Dict[str, str], config: Config) -> List[dict]:
    """Extract concepts from source content using the LLM."""
    if not sources:
        return []

    combined = "\n\n---\n\n".join(f"## {path}\n\n{content}" for path, content in sources.items())
    raw_concepts = _call_llm_extract(combined, config)

    # Slugify IDs and cap at max_concepts
    concepts = []
    for c in raw_concepts[: config.compile.max_concepts]:
        c["id"] = slugify(c.get("id", "untitled"))
        concepts.append(c)

    return concepts


def generate_article(
    concept: dict,
    sources: Dict[str, str],
    all_concept_ids: List[str],
    config: Config,
) -> str:
    """Generate a wiki article for a concept."""
    sources_text = "\n\n---\n\n".join(f"## {p}\n\n{c}" for p, c in sources.items())
    return _call_llm_article(concept, sources_text, all_concept_ids, config)


def generate_index(concepts: List[dict]) -> str:
    """Generate the wiki index markdown."""
    lines = ["# Wiki Index", "", "| Concept | Summary |", "|---|---|"]
    for c in sorted(concepts, key=lambda x: x.get("title", "").lower()):
        title = c.get("title", "")
        summary = c.get("summary", "")
        cid = c.get("id", "")
        lines.append(f"| [[{cid}|{title}]] | {summary} |")
    return "\n".join(lines) + "\n"


def generate_sources_catalog(source_hashes: Dict[str, str], concepts: List[dict]) -> str:
    """Generate the sources catalog markdown."""
    # Build reverse map: source -> list of concept titles
    source_to_concepts: Dict[str, List[str]] = {}
    for s in sorted(source_hashes.keys()):
        source_to_concepts[s] = []

    for c in concepts:
        for src in c.get("related_sources", []):
            if src in source_to_concepts:
                source_to_concepts[src].append(c.get("title", c.get("id", "")))

    lines = ["# Source Catalog", "", "| Source | Referenced By |", "|---|---|"]
    for src in sorted(source_to_concepts.keys()):
        refs = ", ".join(source_to_concepts[src]) or "(none)"
        lines.append(f"| {src} | {refs} |")
    return "\n".join(lines) + "\n"


def run_compile(config: Config) -> CompileResult:
    """Run the full compilation pipeline."""
    source_path = config.source.path
    output_path = config.output.path
    state_path = output_path / config.state.path / "state.json"
    concepts_dir = output_path / "concepts"

    # Load previous state
    state = CompileState.load(state_path)

    # Scan and hash sources
    source_files = scan_sources(config)
    new_hashes = {}
    for rel in source_files:
        full = source_path / rel
        new_hashes[rel] = content_hash(full.read_text(encoding="utf-8"))

    # Detect changes
    added, changed, deleted = detect_changes(state.source_hashes, new_hashes)

    if not added and not changed and not deleted:
        return CompileResult(new=0, updated=0, removed=0)

    # Read all source content for changed/new files
    all_sources = {}
    for rel in source_files:
        all_sources[rel] = (source_path / rel).read_text(encoding="utf-8")

    # Extract concepts
    concepts = _call_llm_extract(
        "\n\n---\n\n".join(f"## {p}\n\n{c}" for p, c in all_sources.items()),
        config,
    )
    for c in concepts:
        c["id"] = slugify(c.get("id", "untitled"))
    concepts = concepts[: config.compile.max_concepts]

    # Generate articles
    concepts_dir.mkdir(parents=True, exist_ok=True)
    concept_ids = [c["id"] for c in concepts]
    new_count = 0
    updated_count = 0

    for concept in concepts:
        cid = concept["id"]
        article_path = concepts_dir / f"{cid}.md"
        was_existing = article_path.exists()

        related = {s: all_sources[s] for s in concept.get("related_sources", []) if s in all_sources}
        if not related:
            related = all_sources

        article = _call_llm_article(concept, "\n".join(related.values()), concept_ids, config)
        article_path.write_text(article, encoding="utf-8")

        if was_existing:
            updated_count += 1
        else:
            new_count += 1

    # Generate index and catalog
    (output_path / config.output.index_file).write_text(generate_index(concepts), encoding="utf-8")
    (output_path / config.output.sources_file).write_text(
        generate_sources_catalog(new_hashes, concepts), encoding="utf-8"
    )

    # Remove orphaned concept articles
    removed_count = 0
    current_ids = {c["id"] for c in concepts}
    if concepts_dir.exists():
        for f in concepts_dir.glob("*.md"):
            if f.stem not in current_ids:
                f.unlink()
                removed_count += 1

    # Save state
    new_state = CompileState(
        source_hashes=new_hashes,
        concepts={c["id"]: {"title": c["title"], "sources": c.get("related_sources", []), "hash": ""} for c in concepts},
        last_compile=datetime.now(timezone.utc).isoformat(),
    )
    new_state.save(state_path)

    return CompileResult(new=new_count, updated=updated_count, removed=removed_count)
