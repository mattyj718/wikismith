"""Tests for wikismith.utils — slugify, content_hash, to_frontmatter, sanitize_filename."""

from __future__ import annotations

import hashlib

import yaml

from wikismith.utils import content_hash, sanitize_filename, slugify, to_frontmatter


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic_text(self):
        assert slugify("Hello World") == "hello-world"

    def test_path_traversal_stripped(self):
        assert ".." not in slugify("../../.env")
        assert slugify("../../.env") == "env"

    def test_unicode_normalized(self):
        result = slugify("café résumé")
        assert result == "cafe-resume"

    def test_empty_returns_untitled(self):
        assert slugify("") == "untitled"

    def test_whitespace_only_returns_untitled(self):
        assert slugify("   ") == "untitled"

    def test_long_string_truncated(self):
        long = "a" * 300
        result = slugify(long, max_len=100)
        assert len(result) <= 100

    def test_consecutive_special_chars_collapsed(self):
        result = slugify("hello---world___test")
        assert "--" not in result
        assert "__" not in result

    def test_filename_unsafe_chars_stripped(self):
        result = slugify('file<>:"/\\|?*name')
        assert all(c not in result for c in '<>:"/\\|?*')

    def test_leading_trailing_hyphens_stripped(self):
        result = slugify("--hello--")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_dots_in_middle_preserved(self):
        result = slugify("version.2.0")
        assert "." not in result or result == "version-2-0"


# ---------------------------------------------------------------------------
# content_hash
# ---------------------------------------------------------------------------

class TestContentHash:
    def test_known_output(self):
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert content_hash("hello world") == f"sha256:{expected}"

    def test_different_content_different_hash(self):
        assert content_hash("foo") != content_hash("bar")

    def test_deterministic(self):
        assert content_hash("same") == content_hash("same")

    def test_empty_string(self):
        expected = hashlib.sha256(b"").hexdigest()
        assert content_hash("") == f"sha256:{expected}"


# ---------------------------------------------------------------------------
# to_frontmatter
# ---------------------------------------------------------------------------

class TestToFrontmatter:
    def test_basic_dict(self):
        result = to_frontmatter({"title": "Hello", "author": "Matt"})
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        assert "title: Hello" in result
        assert "author: Matt" in result

    def test_special_chars_quoted(self):
        result = to_frontmatter({"title": "Hello: World"})
        parsed = yaml.safe_load(result.strip("---\n"))
        assert parsed["title"] == "Hello: World"

    def test_none_values_excluded(self):
        result = to_frontmatter({"title": "Hello", "author": None})
        assert "author" not in result

    def test_empty_string_excluded(self):
        result = to_frontmatter({"title": "Hello", "author": ""})
        assert "author" not in result

    def test_list_values(self):
        result = to_frontmatter({"tags": ["foo", "bar"]})
        parsed = yaml.safe_load(result.strip("---\n"))
        assert parsed["tags"] == ["foo", "bar"]

    def test_round_trip(self):
        data = {"title": "Test", "count": 42, "tags": ["a", "b"]}
        result = to_frontmatter(data)
        # Strip the --- delimiters and parse
        inner = result.replace("---\n", "", 1).rsplit("---", 1)[0]
        parsed = yaml.safe_load(inner)
        assert parsed == data


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_basic_preserves_spaces(self):
        assert sanitize_filename("My Article Title") == "My Article Title"

    def test_unsafe_chars_stripped(self):
        result = sanitize_filename('file<>name:with|bad*chars')
        assert all(c not in result for c in '<>:"|?*')
        # Spaces where chars were
        assert "file" in result
        assert "name" in result

    def test_length_limit(self):
        long = "a" * 300
        result = sanitize_filename(long, max_len=100)
        assert len(result) <= 100

    def test_trailing_dots_spaces_stripped(self):
        result = sanitize_filename("hello... ")
        assert not result.endswith(".")
        assert not result.endswith(" ")

    def test_control_chars_removed(self):
        result = sanitize_filename("hello\x00\x1fworld")
        assert "\x00" not in result
        assert "\x1f" not in result

    def test_empty_returns_untitled(self):
        assert sanitize_filename("") == "Untitled"

    def test_only_special_chars_returns_untitled(self):
        assert sanitize_filename("***") == "Untitled"

    def test_collapses_whitespace(self):
        result = sanitize_filename("hello     world")
        assert "     " not in result
