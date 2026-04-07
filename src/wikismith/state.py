"""Compile state persistence and change detection."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set, Tuple


@dataclass
class CompileState:
    source_hashes: Dict[str, str] = field(default_factory=dict)
    concepts: Dict[str, dict] = field(default_factory=dict)
    last_compile: Optional[str] = None

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "last_compile": self.last_compile,
            "source_hashes": self.source_hashes,
            "concepts": self.concepts,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> CompileState:
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            source_hashes=data.get("source_hashes", {}),
            concepts=data.get("concepts", {}),
            last_compile=data.get("last_compile"),
        )


def detect_changes(
    old_hashes: Dict[str, str],
    new_hashes: Dict[str, str],
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Compare old and new source hashes. Returns (added, changed, deleted) sets of file paths."""
    old_keys = set(old_hashes.keys())
    new_keys = set(new_hashes.keys())

    added = new_keys - old_keys
    deleted = old_keys - new_keys
    common = old_keys & new_keys
    changed = {k for k in common if old_hashes[k] != new_hashes[k]}

    return added, changed, deleted
