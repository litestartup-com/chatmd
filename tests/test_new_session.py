"""Tests for /new session command (T-040).

Archives chat.md to chat/ directory, creates fresh chat.md,
and updates chat/_index.md.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock

from chatmd.skills.base import SkillContext
from chatmd.skills.infra import NewSessionSkill


def _ctx(tmp_path: Path) -> SkillContext:
    return SkillContext(
        source_file=tmp_path / "chat.md", source_line=1,
        workspace=tmp_path, interaction_root=tmp_path,
    )


def _setup_workspace(tmp_path: Path, content: str = "") -> Path:
    """Create a minimal workspace with chat.md."""
    chatmd_dir = tmp_path / ".chatmd"
    chatmd_dir.mkdir()
    chat_md = tmp_path / "chat.md"
    if not content:
        content = "# ChatMD\n\n---\n\nHello, this is some content.\n\n---\n\n"
    chat_md.write_text(content, encoding="utf-8")
    return chat_md


class TestNewSessionBasic:
    """Basic /new command behavior."""

    def test_archive_creates_file_in_chat_dir(self, tmp_path):
        _setup_workspace(tmp_path)
        skill = NewSessionSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success

        chat_dir = tmp_path / "chat"
        assert chat_dir.is_dir()
        archived = list(chat_dir.glob("*.md"))
        assert len(archived) == 1
        assert archived[0].name != "_index.md"

    def test_archive_filename_format(self, tmp_path):
        _setup_workspace(tmp_path)
        skill = NewSessionSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success

        archived = list((tmp_path / "chat").glob("*.md"))
        # Format: YYYY-MMDD-HHmm-topic.md
        pattern = r"\d{4}-\d{4}-\d{4}-.+\.md"
        assert re.match(pattern, archived[0].name)

    def test_fresh_chat_md_created(self, tmp_path):
        _setup_workspace(tmp_path)
        skill = NewSessionSkill()
        skill.execute("", {}, _ctx(tmp_path))

        chat_md = tmp_path / "chat.md"
        content = chat_md.read_text(encoding="utf-8")
        assert "# ChatMD" in content
        assert "---" in content
        # Should NOT contain old content
        assert "Hello, this is some content" not in content

    def test_archived_content_matches_original(self, tmp_path):
        original = "# ChatMD\n\n---\n\nOriginal content here.\n\n---\n\n"
        _setup_workspace(tmp_path, original)
        skill = NewSessionSkill()
        skill.execute("", {}, _ctx(tmp_path))

        archived = list((tmp_path / "chat").glob("*.md"))
        archived_content = archived[0].read_text(encoding="utf-8")
        assert archived_content == original

    def test_success_message_contains_archive_name(self, tmp_path):
        _setup_workspace(tmp_path)
        skill = NewSessionSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "chat/" in result.output or ".md" in result.output


class TestNewSessionTopic:
    """Topic extraction and naming."""

    def test_explicit_topic(self, tmp_path):
        _setup_workspace(tmp_path)
        skill = NewSessionSkill()
        result = skill.execute("my-topic", {}, _ctx(tmp_path))
        assert result.success

        archived = list((tmp_path / "chat").glob("*.md"))
        assert "my-topic" in archived[0].name

    def test_auto_topic_from_body(self, tmp_path):
        content = "# ChatMD\n\n---\n\nAI discussion notes\n\n---\n\n"
        _setup_workspace(tmp_path, content)
        skill = NewSessionSkill()
        skill.execute("", {}, _ctx(tmp_path))

        archived = list((tmp_path / "chat").glob("*.md"))
        assert "AI discussion notes" in archived[0].name

    def test_auto_topic_truncated_at_20_chars(self, tmp_path):
        content = "# ChatMD\n\n---\n\nThis is a very long topic that should be truncated\n\n---\n\n"
        _setup_workspace(tmp_path, content)
        skill = NewSessionSkill()
        skill.execute("", {}, _ctx(tmp_path))

        archived = list((tmp_path / "chat").glob("*.md"))
        # Topic part should be <= 20 chars
        # Filename: YYYY-MMDD-HHmm-topic.md
        name = archived[0].stem  # without .md
        topic_part = name.split("-", 3)[3]  # after YYYY-MMDD-HHmm-
        assert len(topic_part) <= 20

    def test_fallback_topic_when_body_empty(self, tmp_path):
        content = "# ChatMD\n\n---\n\n/date\n\n---\n\n"
        _setup_workspace(tmp_path, content)
        skill = NewSessionSkill()
        # Body extraction skips commands and headings — only /date remains
        # which is a command, so body is empty → fallback topic
        result = skill.execute("", {}, _ctx(tmp_path))
        # This should fail since no substantive content
        assert not result.success


class TestNewSessionSanitize:
    """Filename sanitization."""

    def test_unsafe_chars_replaced(self):
        assert NewSessionSkill._sanitize_topic('hello/world') == "hello-world"
        assert NewSessionSkill._sanitize_topic('a:b*c?d') == "a-b-c-d"
        assert NewSessionSkill._sanitize_topic('test<>file') == "test-file"

    def test_multiple_hyphens_collapsed(self):
        assert NewSessionSkill._sanitize_topic('a///b') == "a-b"

    def test_empty_sanitized_falls_back(self):
        assert NewSessionSkill._sanitize_topic('***') == "chat"

    def test_normal_text_unchanged(self):
        assert NewSessionSkill._sanitize_topic("hello world") == "hello world"


class TestNewSessionConflict:
    """Filename conflict resolution."""

    def test_no_conflict(self, tmp_path):
        path = tmp_path / "test.md"
        assert NewSessionSkill._resolve_conflict(path) == path

    def test_conflict_appends_counter(self, tmp_path):
        path = tmp_path / "test.md"
        path.write_text("existing", encoding="utf-8")
        resolved = NewSessionSkill._resolve_conflict(path)
        assert resolved.name == "test-2.md"

    def test_multiple_conflicts(self, tmp_path):
        (tmp_path / "test.md").write_text("1", encoding="utf-8")
        (tmp_path / "test-2.md").write_text("2", encoding="utf-8")
        resolved = NewSessionSkill._resolve_conflict(tmp_path / "test.md")
        assert resolved.name == "test-3.md"


class TestNewSessionEdgeCases:
    """Edge cases."""

    def test_no_chat_md(self, tmp_path):
        (tmp_path / ".chatmd").mkdir()
        skill = NewSessionSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert not result.success
        assert "not found" in result.error or "不存在" in result.error

    def test_empty_chat_md(self, tmp_path):
        _setup_workspace(tmp_path, "# ChatMD\n\n---\n\n")
        skill = NewSessionSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert not result.success

    def test_index_manager_called(self, tmp_path):
        _setup_workspace(tmp_path)
        mock_index = MagicMock()
        skill = NewSessionSkill(index_manager=mock_index)
        skill.execute("", {}, _ctx(tmp_path))
        mock_index.update.assert_called_once()

    def test_no_index_manager_still_works(self, tmp_path):
        _setup_workspace(tmp_path)
        skill = NewSessionSkill(index_manager=None)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success

    def test_new_from_chat_subdir_no_recursive_chat(self, tmp_path):
        """Regression: /new triggered from chat/xxx.md must NOT create chat/chat/."""
        _setup_workspace(tmp_path)
        chat_dir = tmp_path / "chat"
        chat_dir.mkdir()
        sub_file = chat_dir / "session.md"
        sub_file.write_text("/new", encoding="utf-8")

        # source_file is inside chat/, but interaction_root is tmp_path
        ctx = SkillContext(
            source_file=sub_file, source_line=1,
            workspace=tmp_path, interaction_root=tmp_path,
        )
        skill = NewSessionSkill()
        result = skill.execute("", {}, ctx)
        assert result.success

        # chat/ should exist but chat/chat/ must NOT
        assert chat_dir.is_dir()
        assert not (chat_dir / "chat").exists()


class TestExtractBody:
    """Test body extraction from chat.md content."""

    def test_skips_frontmatter(self):
        content = "---\ntitle: test\n---\n\nReal content here\n"
        body = NewSessionSkill._extract_body(content)
        assert "Real content here" in body
        assert "title: test" not in body

    def test_skips_commands(self):
        content = "/date\n/ask hello\nReal text\n"
        body = NewSessionSkill._extract_body(content)
        assert body == "Real text"

    def test_skips_blockquotes(self):
        content = "> chatmd /ask 1.0s\nReal text\n"
        body = NewSessionSkill._extract_body(content)
        assert body == "Real text"

    def test_skips_headings(self):
        content = "# Title\n## Subtitle\nReal text\n"
        body = NewSessionSkill._extract_body(content)
        assert body == "Real text"

    def test_skips_horizontal_rules(self):
        content = "Some intro\n---\nReal text\n---\nMore text\n"
        body = NewSessionSkill._extract_body(content)
        assert "Real text" in body
        # --- lines themselves are skipped
        assert body.count("---") == 0

    def test_empty_content(self):
        body = NewSessionSkill._extract_body("")
        assert body == ""

    def test_only_boilerplate(self):
        content = "# ChatMD\n\n---\n\n> Welcome\n\n---\n\n"
        body = NewSessionSkill._extract_body(content)
        assert body.strip() == ""


class TestNewSessionAttributes:
    """Test skill attributes."""

    def test_name_and_aliases(self):
        skill = NewSessionSkill()
        assert skill.name == "new"
        assert "n" in skill.aliases
        assert skill.category == "builtin"
