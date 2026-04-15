"""Tests for /inbox skill (T-105 + T-106)."""

from __future__ import annotations

from pathlib import Path

from chatmd.skills.base import SkillContext
from chatmd.skills.inbox import InboxSkill, _first_meaningful_line

# ---------------------------------------------------------------------------
# Sample inbox content
# ---------------------------------------------------------------------------

_SAMPLE_INBOX = """\
# 2026-04-14 Inbox

## 10:30:05

今天的想法：需要把项目计划整理一下……

---

## 14:15:22

会议记录：讨论了 API 方案，确定使用 REST 风格

---

## 18:00:00

晚餐提醒

---
"""

_EMPTY_INBOX = """\
# 2026-04-14 Inbox

"""


class TestInboxSkillParsing:
    """Test the internal _parse_entries method."""

    def test_parse_three_entries(self) -> None:
        skill = InboxSkill()
        entries = skill._parse_entries(_SAMPLE_INBOX)
        assert len(entries) == 3
        assert entries[0]["time"] == "10:30:05"
        assert entries[1]["time"] == "14:15:22"
        assert entries[2]["time"] == "18:00:00"

    def test_parse_preview_content(self) -> None:
        skill = InboxSkill()
        entries = skill._parse_entries(_SAMPLE_INBOX)
        assert "项目计划" in entries[0]["preview"]
        assert "API" in entries[1]["preview"]
        assert "晚餐" in entries[2]["preview"]

    def test_parse_empty_inbox(self) -> None:
        skill = InboxSkill()
        entries = skill._parse_entries(_EMPTY_INBOX)
        assert len(entries) == 0

    def test_parse_no_entries(self) -> None:
        skill = InboxSkill()
        entries = skill._parse_entries("# 2026-04-14 Inbox\n\nSome random text\n")
        assert len(entries) == 0

    def test_parse_hhmm_format(self) -> None:
        """Also support ## HH:MM (without seconds)."""
        content = "# 2026-04-14 Inbox\n\n## 10:30\n\nHello\n\n---\n"
        skill = InboxSkill()
        entries = skill._parse_entries(content)
        assert len(entries) == 1
        assert entries[0]["time"] == "10:30"


class TestInboxSkillExecute:
    """Test the execute method with real files."""

    def _ctx(self, workspace: Path) -> SkillContext:
        return SkillContext(
            source_file=workspace / "chat.md",
            source_line=1,
            workspace=workspace,
            interaction_root=workspace,
        )

    def test_today_with_messages(self, tmp_path: Path) -> None:
        from datetime import date

        today = date.today().isoformat()
        inbox_dir = tmp_path / "chatmd" / "inbox"
        inbox_dir.mkdir(parents=True)
        inbox_file = inbox_dir / f"{today}.md"
        inbox_file.write_text(_SAMPLE_INBOX, encoding="utf-8")

        skill = InboxSkill()
        result = skill.execute("", {}, self._ctx(tmp_path))
        assert result.success
        assert "3" in result.output  # 3 messages
        assert "10:30:05" in result.output
        assert "18:00:00" in result.output

    def test_specific_date(self, tmp_path: Path) -> None:
        inbox_dir = tmp_path / "chatmd" / "inbox"
        inbox_dir.mkdir(parents=True)
        inbox_file = inbox_dir / "2026-04-14.md"
        inbox_file.write_text(_SAMPLE_INBOX, encoding="utf-8")

        skill = InboxSkill()
        result = skill.execute("2026-04-14", {}, self._ctx(tmp_path))
        assert result.success
        assert "3" in result.output

    def test_no_inbox_file(self, tmp_path: Path) -> None:
        skill = InboxSkill()
        result = skill.execute("2026-01-01", {}, self._ctx(tmp_path))
        assert result.success
        assert "2026-01-01" in result.output  # "No inbox messages for ..."

    def test_invalid_date_format(self, tmp_path: Path) -> None:
        skill = InboxSkill()
        result = skill.execute("not-a-date", {}, self._ctx(tmp_path))
        assert not result.success
        assert result.error

    def test_empty_inbox_file(self, tmp_path: Path) -> None:
        from datetime import date

        today = date.today().isoformat()
        inbox_dir = tmp_path / "chatmd" / "inbox"
        inbox_dir.mkdir(parents=True)
        (inbox_dir / f"{today}.md").write_text(_EMPTY_INBOX, encoding="utf-8")

        skill = InboxSkill()
        result = skill.execute("", {}, self._ctx(tmp_path))
        assert result.success
        assert today in result.output


class TestFirstMeaningfulLine:
    """Test the helper function."""

    def test_normal(self) -> None:
        assert _first_meaningful_line(["hello", "world"]) == "hello"

    def test_empty_list(self) -> None:
        assert _first_meaningful_line([]) == "(empty)"

    def test_blank_lines(self) -> None:
        assert _first_meaningful_line(["", "  ", "actual"]) == "actual"
