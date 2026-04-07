"""Tests for wikismith.state — state persistence and change detection."""

from __future__ import annotations

from pathlib import Path

from wikismith.state import CompileState, detect_changes


class TestCompileState:
    def test_new_state_is_empty(self):
        state = CompileState()
        assert state.source_hashes == {}
        assert state.concepts == {}
        assert state.last_compile is None

    def test_save_and_load(self, tmp_path: Path):
        state = CompileState(
            source_hashes={"file.md": "sha256:abc123"},
            concepts={"test-concept": {"title": "Test", "sources": ["file.md"], "hash": "sha256:def456"}},
            last_compile="2026-04-07T12:00:00Z",
        )
        state_file = tmp_path / ".wikismith" / "state.json"
        state.save(state_file)
        assert state_file.exists()

        loaded = CompileState.load(state_file)
        assert loaded.source_hashes == state.source_hashes
        assert loaded.concepts == state.concepts
        assert loaded.last_compile == state.last_compile

    def test_load_missing_file_returns_empty(self, tmp_path: Path):
        state = CompileState.load(tmp_path / "nonexistent.json")
        assert state.source_hashes == {}
        assert state.concepts == {}

    def test_round_trip_preserves_data(self, tmp_path: Path):
        original = CompileState(
            source_hashes={"a.md": "sha256:aaa", "b.md": "sha256:bbb"},
            concepts={
                "concept-a": {"title": "A", "sources": ["a.md"], "hash": "sha256:ca"},
                "concept-b": {"title": "B", "sources": ["b.md"], "hash": "sha256:cb"},
            },
            last_compile="2026-01-01T00:00:00Z",
        )
        path = tmp_path / "state.json"
        original.save(path)
        loaded = CompileState.load(path)
        assert loaded.source_hashes == original.source_hashes
        assert loaded.concepts == original.concepts
        assert loaded.last_compile == original.last_compile


class TestDetectChanges:
    def test_new_file_detected(self):
        old = {}
        new = {"file.md": "sha256:abc"}
        added, changed, deleted = detect_changes(old, new)
        assert "file.md" in added
        assert changed == set()
        assert deleted == set()

    def test_changed_file_detected(self):
        old = {"file.md": "sha256:old"}
        new = {"file.md": "sha256:new"}
        added, changed, deleted = detect_changes(old, new)
        assert added == set()
        assert "file.md" in changed
        assert deleted == set()

    def test_deleted_file_detected(self):
        old = {"file.md": "sha256:abc"}
        new = {}
        added, changed, deleted = detect_changes(old, new)
        assert added == set()
        assert changed == set()
        assert "file.md" in deleted

    def test_unchanged_file_not_reported(self):
        old = {"file.md": "sha256:same"}
        new = {"file.md": "sha256:same"}
        added, changed, deleted = detect_changes(old, new)
        assert added == set()
        assert changed == set()
        assert deleted == set()

    def test_mixed_changes(self):
        old = {"kept.md": "sha256:same", "changed.md": "sha256:old", "deleted.md": "sha256:del"}
        new = {"kept.md": "sha256:same", "changed.md": "sha256:new", "added.md": "sha256:add"}
        added, changed, deleted = detect_changes(old, new)
        assert added == {"added.md"}
        assert changed == {"changed.md"}
        assert deleted == {"deleted.md"}

    def test_both_empty(self):
        added, changed, deleted = detect_changes({}, {})
        assert added == set()
        assert changed == set()
        assert deleted == set()
