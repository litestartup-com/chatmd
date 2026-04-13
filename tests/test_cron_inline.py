"""Tests for cron inline_status annotation writeback (T-065 / R-052 / F-104)."""

from __future__ import annotations

from pathlib import Path

from chatmd.engine.cron_inline import write_inline_status


class TestWriteInlineStatus:
    """write_inline_status updates cron.md with job ID + status comments."""

    def test_basic_annotation(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "# Cron\n\n```cron\n0 9 * * *   /ask daily\n```\n",
            encoding="utf-8",
        )
        states = {
            "cron-a1b2": {
                "status": "active",
                "next_run_str": "2026-04-09 09:00",
                "raw_line": "0 9 * * *   /ask daily",
            },
        }
        result = write_inline_status(cron_file, states)
        assert result is True
        content = cron_file.read_text(encoding="utf-8")
        assert "[cron-a1b2]" in content
        assert "next: 2026-04-09 09:00" in content

    def test_paused_status(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "# Cron\n\n```cron\n@hourly   /sync\n```\n",
            encoding="utf-8",
        )
        states = {
            "cron-x1": {
                "status": "paused",
                "next_run_str": "",
                "raw_line": "@hourly   /sync",
            },
        }
        result = write_inline_status(cron_file, states)
        assert result is True
        content = cron_file.read_text(encoding="utf-8")
        assert "⏸ paused" in content

    def test_no_change_if_already_up_to_date(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "# Cron\n\n```cron\n"
            "0 9 * * *   /ask daily    # [cron-a1b2] ✅ next: 2026-04-09 09:00\n"
            "```\n",
            encoding="utf-8",
        )
        states = {
            "cron-a1b2": {
                "status": "active",
                "next_run_str": "2026-04-09 09:00",
                "raw_line": "0 9 * * *   /ask daily",
            },
        }
        result = write_inline_status(cron_file, states)
        assert result is False  # No modification needed

    def test_update_existing_comment(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "# Cron\n\n```cron\n"
            "0 9 * * *   /ask daily    # [cron-a1b2] ✅ next: 2026-04-08 09:00\n"
            "```\n",
            encoding="utf-8",
        )
        states = {
            "cron-a1b2": {
                "status": "active",
                "next_run_str": "2026-04-09 09:00",
                "raw_line": "0 9 * * *   /ask daily",
            },
        }
        result = write_inline_status(cron_file, states)
        assert result is True
        content = cron_file.read_text(encoding="utf-8")
        assert "2026-04-09 09:00" in content
        assert "2026-04-08 09:00" not in content

    def test_multiple_jobs(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "# Cron\n\n```cron\n"
            "0 9 * * *   /ask daily\n"
            "@hourly     /sync\n"
            "```\n",
            encoding="utf-8",
        )
        states = {
            "cron-aaa1": {
                "status": "active",
                "next_run_str": "2026-04-09 09:00",
                "raw_line": "0 9 * * *   /ask daily",
            },
            "cron-bbb2": {
                "status": "paused",
                "next_run_str": "",
                "raw_line": "@hourly     /sync",
            },
        }
        result = write_inline_status(cron_file, states)
        assert result is True
        content = cron_file.read_text(encoding="utf-8")
        assert "[cron-aaa1]" in content
        assert "[cron-bbb2]" in content
        assert "⏸ paused" in content

    def test_preserves_non_cron_content(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "# My Cron Tasks\n\nSome description.\n\n"
            "```cron\n0 9 * * *   /ask daily\n```\n\n"
            "## Notes\n\nMore text here.\n",
            encoding="utf-8",
        )
        states = {
            "cron-a1": {
                "status": "active",
                "next_run_str": "2026-04-09 09:00",
                "raw_line": "0 9 * * *   /ask daily",
            },
        }
        write_inline_status(cron_file, states)
        content = cron_file.read_text(encoding="utf-8")
        assert "Some description." in content
        assert "More text here." in content
        assert "# My Cron Tasks" in content

    def test_ignores_comments_and_empty_lines(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n# This is a comment\n\n0 9 * * *   /ask daily\n```\n",
            encoding="utf-8",
        )
        states = {
            "cron-x1": {
                "status": "active",
                "next_run_str": "2026-04-09 09:00",
                "raw_line": "0 9 * * *   /ask daily",
            },
        }
        write_inline_status(cron_file, states)
        content = cron_file.read_text(encoding="utf-8")
        assert "# This is a comment" in content
        assert "[cron-x1]" in content

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "nope.md"
        result = write_inline_status(cron_file, {})
        assert result is False

    def test_no_jobs_no_change(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n0 9 * * *   /ask daily\n```\n",
            encoding="utf-8",
        )
        result = write_inline_status(cron_file, {})
        assert result is False

    def test_line_to_job_mapping(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n0 9 * * *   /ask daily\n```\n",
            encoding="utf-8",
        )
        states = {
            "cron-mapped": {
                "status": "active",
                "next_run_str": "2026-04-10 09:00",
                "raw_line": "0 9 * * *   /ask daily",
            },
        }
        # Line 2 (1-indexed) is the task line
        result = write_inline_status(
            cron_file, states, line_to_job={2: "cron-mapped"},
        )
        assert result is True
        content = cron_file.read_text(encoding="utf-8")
        assert "[cron-mapped]" in content
