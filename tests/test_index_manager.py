"""Tests for chat/_index.md auto-maintenance."""

from chatmd.infra.index_manager import IndexManager


class TestIndexManager:
    def test_update_creates_index(self, tmp_path):
        chat_dir = tmp_path / "chat"
        chat_dir.mkdir()
        (chat_dir / "session1.md").write_text("hello", encoding="utf-8")
        (chat_dir / "session2.md").write_text("world", encoding="utf-8")

        mgr = IndexManager(tmp_path)
        assert mgr.update() is True
        assert mgr.index_file.exists()

        content = mgr.index_file.read_text(encoding="utf-8")
        assert "session1.md" in content
        assert "session2.md" in content

    def test_excludes_index_file(self, tmp_path):
        chat_dir = tmp_path / "chat"
        chat_dir.mkdir()
        (chat_dir / "_index.md").write_text("old index", encoding="utf-8")
        (chat_dir / "note.md").write_text("data", encoding="utf-8")

        mgr = IndexManager(tmp_path)
        mgr.update()
        content = mgr.index_file.read_text(encoding="utf-8")
        # Should list note.md but not _index.md as a session
        assert "note.md" in content
        assert "| [_index.md]" not in content

    def test_no_update_if_unchanged(self, tmp_path):
        chat_dir = tmp_path / "chat"
        chat_dir.mkdir()
        (chat_dir / "a.md").write_text("x", encoding="utf-8")

        mgr = IndexManager(tmp_path)
        assert mgr.update() is True
        # Second call should return False (no change)
        assert mgr.update() is False

    def test_no_chat_dir(self, tmp_path):
        mgr = IndexManager(tmp_path)
        assert mgr.update() is False

    def test_empty_chat_dir(self, tmp_path):
        (tmp_path / "chat").mkdir()
        mgr = IndexManager(tmp_path)
        assert mgr.update() is True
        content = mgr.index_file.read_text(encoding="utf-8")
        assert "Chat Sessions" in content

    def test_human_size(self):
        assert IndexManager._human_size(500) == "500 B"
        assert IndexManager._human_size(1024) == "1.0 KB"
        assert IndexManager._human_size(1024 * 1024 * 2) == "2.0 MB"
