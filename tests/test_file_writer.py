"""Tests for the safe file writer."""


from chatmd.infra.file_writer import FileWriter


class TestFileWriter:
    """Test FileWriter operations."""

    def test_write_result_replaces_text(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("/date\n", encoding="utf-8")

        writer = FileWriter()
        ok = writer.write_result(f, 1, "/date", "> 2026-03-30")
        assert ok
        assert "> 2026-03-30" in f.read_text(encoding="utf-8")

    def test_write_result_missing_text(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("Hello\n", encoding="utf-8")

        writer = FileWriter()
        ok = writer.write_result(f, 1, "/date", "> result")
        assert not ok

    def test_replace_by_task_id(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text(
            "Line 1\n"
            "> ⏳ 翻译中... `#task-abc1`\n"
            "Line 3\n",
            encoding="utf-8",
        )

        writer = FileWriter()
        ok = writer.replace_by_task_id(f, "task-abc1", "> ✅ こんにちは")
        assert ok
        content = f.read_text(encoding="utf-8")
        assert "> ✅ こんにちは" in content
        assert "⏳" not in content

    def test_replace_by_task_id_not_found(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("No task here\n", encoding="utf-8")

        writer = FileWriter()
        ok = writer.replace_by_task_id(f, "task-none", "> result")
        assert not ok

    def test_append_line(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("Line 1\n", encoding="utf-8")

        writer = FileWriter()
        writer.append_line(f, "> New line")
        content = f.read_text(encoding="utf-8")
        assert content.endswith("> New line\n")

    def test_agent_write_flag(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("/date\n", encoding="utf-8")

        writer = FileWriter()
        assert not writer.is_agent_write(f)
        # During write_result, the flag is set and then cleared
        writer.write_result(f, 1, "/date", "> result")
        # After write, flag should be cleared
        assert not writer.is_agent_write(f)

    def test_line_based_replace_avoids_wrong_match(self, tmp_path):
        """Regression: /list in help table must not be replaced instead of
        the user's actual /list command on a later line."""
        f = tmp_path / "test.md"
        f.write_text(
            "| `/list` | `/ls` | 列出 Session |\n"
            "| `/date` | `/d` | 日期 |\n"
            "\n"
            "/list\n",
            encoding="utf-8",
        )
        writer = FileWriter()
        # line 4 is the user's /list command
        ok = writer.write_result(f, 4, "/list", "## Sessions\n- chat.md")
        assert ok
        content = f.read_text(encoding="utf-8")
        # The table row must be untouched
        assert "| `/list` | `/ls` | 列出 Session |" in content
        # The user's command must be replaced
        assert "## Sessions" in content
        assert "\n/list\n" not in content
