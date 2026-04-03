"""Tests for @ reference resolver — resolves @above, @section, @all, @file, @clip."""

from unittest.mock import patch

from chatmd.engine.reference_resolver import ReferenceResolver, resolve_references


class TestResolveAbove:
    """Test @above and @above(N) references."""

    def test_above_gets_last_paragraph(self):
        lines = [
            "First paragraph line 1.",
            "First paragraph line 2.",
            "",
            "Second paragraph.",
            "",
            "/summary @above",
        ]
        result = resolve_references("@above", lines, cmd_line=6)
        assert result == "Second paragraph."

    def test_above_n_gets_nth_paragraph(self):
        lines = [
            "Paragraph 1.",
            "",
            "Paragraph 2.",
            "",
            "Paragraph 3.",
            "",
            "/summary @above(2)",
        ]
        result = resolve_references("@above(2)", lines, cmd_line=7)
        assert result == "Paragraph 2."

    def test_above_1_same_as_above(self):
        lines = [
            "Para A.",
            "",
            "Para B.",
            "",
            "/cmd @above(1)",
        ]
        result = resolve_references("@above(1)", lines, cmd_line=5)
        assert result == "Para B."

    def test_above_multi_line_paragraph(self):
        lines = [
            "Line 1 of para.",
            "Line 2 of para.",
            "Line 3 of para.",
            "",
            "/cmd @above",
        ]
        result = resolve_references("@above", lines, cmd_line=5)
        assert "Line 1 of para." in result
        assert "Line 2 of para." in result
        assert "Line 3 of para." in result

    def test_above_no_paragraph_returns_empty(self):
        lines = [
            "/cmd @above",
        ]
        result = resolve_references("@above", lines, cmd_line=1)
        assert result == ""

    def test_above_n_out_of_range(self):
        lines = [
            "Only one paragraph.",
            "",
            "/cmd @above(5)",
        ]
        result = resolve_references("@above(5)", lines, cmd_line=3)
        assert result == ""

    def test_above_skips_empty_and_blockquote_lines(self):
        """Blockquote (agent output) lines are not part of user paragraphs."""
        lines = [
            "User paragraph.",
            "",
            "> chatmd /date 0.01s",
            "> Result here",
            "",
            "/cmd @above",
        ]
        result = resolve_references("@above", lines, cmd_line=6)
        assert result == "User paragraph."


class TestResolveSection:
    """Test @section reference."""

    def test_section_gets_current_section(self):
        lines = [
            "## Introduction",
            "",
            "Intro content here.",
            "More intro.",
            "",
            "## Methods",
            "",
            "Methods content.",
            "",
            "/cmd @section",
        ]
        result = resolve_references("@section", lines, cmd_line=10)
        assert "Methods content." in result
        assert "Intro content" not in result

    def test_section_no_heading_returns_all_above(self):
        lines = [
            "No heading here.",
            "Some content.",
            "",
            "/cmd @section",
        ]
        result = resolve_references("@section", lines, cmd_line=4)
        assert "No heading here." in result
        assert "Some content." in result

    def test_section_excludes_heading_line(self):
        lines = [
            "## My Section",
            "",
            "Section body.",
            "",
            "/cmd @section",
        ]
        result = resolve_references("@section", lines, cmd_line=5)
        assert "Section body." in result
        assert "## My Section" not in result


class TestResolveAll:
    """Test @all reference."""

    def test_all_returns_full_content(self):
        lines = [
            "# Title",
            "",
            "Paragraph 1.",
            "",
            "Paragraph 2.",
            "",
            "/cmd @all",
        ]
        result = resolve_references("@all", lines, cmd_line=7)
        assert "# Title" in result
        assert "Paragraph 1." in result
        assert "Paragraph 2." in result
        assert "/cmd @all" not in result

    def test_all_excludes_command_line(self):
        lines = [
            "Some text.",
            "/cmd @all",
        ]
        result = resolve_references("@all", lines, cmd_line=2)
        assert "Some text." in result
        assert "/cmd" not in result


class TestResolveFile:
    """Test @file(path) reference."""

    def test_file_reads_content(self, tmp_path):
        target = tmp_path / "notes.md"
        target.write_text("File content here.", encoding="utf-8")

        lines = ["/cmd @file(notes.md)"]
        result = resolve_references(
            f"@file({target})", lines, cmd_line=1,
            source_file=tmp_path / "chat.md",
        )
        assert "File content here." in result

    def test_file_relative_path(self, tmp_path):
        target = tmp_path / "data" / "notes.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Relative content.", encoding="utf-8")

        result = resolve_references(
            "@file(data/notes.md)", [], cmd_line=1,
            source_file=tmp_path / "chat.md",
        )
        assert "Relative content." in result

    def test_file_not_found(self, tmp_path):
        result = resolve_references(
            "@file(nonexistent.md)", [], cmd_line=1,
            source_file=tmp_path / "chat.md",
        )
        assert result == ""


class TestResolveClip:
    """Test @clip reference."""

    @patch("chatmd.engine.reference_resolver._get_clipboard_text")
    def test_clip_returns_clipboard(self, mock_clip):
        mock_clip.return_value = "Clipboard content"
        result = resolve_references("@clip", [], cmd_line=1)
        assert result == "Clipboard content"

    @patch("chatmd.engine.reference_resolver._get_clipboard_text")
    def test_clip_empty(self, mock_clip):
        mock_clip.return_value = ""
        result = resolve_references("@clip", [], cmd_line=1)
        assert result == ""


class TestResolverClass:
    """Test the ReferenceResolver class interface."""

    def test_no_reference_passthrough(self):
        resolver = ReferenceResolver(
            lines=["Some text.", "", "/cmd Hello"],
            cmd_line=3,
        )
        result = resolver.resolve("Hello")
        assert result == "Hello"

    def test_mixed_text_and_reference(self):
        """Text with embedded @above should resolve the reference part."""
        lines = [
            "My paragraph.",
            "",
            "/cmd @above",
        ]
        resolver = ReferenceResolver(lines=lines, cmd_line=3)
        result = resolver.resolve("@above")
        assert result == "My paragraph."

    def test_is_reference(self):
        assert ReferenceResolver.is_reference("@above")
        assert ReferenceResolver.is_reference("@above(3)")
        assert ReferenceResolver.is_reference("@section")
        assert ReferenceResolver.is_reference("@all")
        assert ReferenceResolver.is_reference("@file(test.md)")
        assert ReferenceResolver.is_reference("@clip")
        assert not ReferenceResolver.is_reference("hello")
        assert not ReferenceResolver.is_reference("@ai{query}")
        assert not ReferenceResolver.is_reference("")
