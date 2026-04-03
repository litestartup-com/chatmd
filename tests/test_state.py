"""Tests for state manager and chat sessions."""


from chatmd.engine.state import ChatSession, StateManager


class TestChatSession:
    def test_create_session(self, tmp_path):
        session = ChatSession(file_path=tmp_path / "chat.md")
        assert session.messages == []
        assert session.created_at

    def test_add_messages(self, tmp_path):
        session = ChatSession(file_path=tmp_path / "chat.md")
        session.add_user_message("Hello")
        session.add_assistant_message("Hi there")
        assert len(session.messages) == 2
        assert session.messages[0]["role"] == "user"
        assert session.messages[1]["role"] == "assistant"

    def test_get_context_messages(self, tmp_path):
        session = ChatSession(file_path=tmp_path / "chat.md")
        for i in range(30):
            session.add_user_message(f"Q{i}")
            session.add_assistant_message(f"A{i}")
        # max_turns=20 → last 40 messages
        ctx = session.get_context_messages(max_turns=20)
        assert len(ctx) == 40

    def test_clear(self, tmp_path):
        session = ChatSession(file_path=tmp_path / "chat.md")
        session.add_user_message("test")
        session.clear()
        assert session.messages == []

    def test_serialization(self, tmp_path):
        session = ChatSession(file_path=tmp_path / "chat.md")
        session.add_user_message("Hello")
        d = session.to_dict()
        restored = ChatSession.from_dict(d)
        assert len(restored.messages) == 1
        assert restored.messages[0]["content"] == "Hello"


class TestStateManager:
    def test_get_session_creates_new(self, tmp_path):
        mgr = StateManager(tmp_path)
        session = mgr.get_session(tmp_path / "chat.md")
        assert isinstance(session, ChatSession)

    def test_get_session_returns_same(self, tmp_path):
        mgr = StateManager(tmp_path)
        s1 = mgr.get_session(tmp_path / "chat.md")
        s2 = mgr.get_session(tmp_path / "chat.md")
        assert s1 is s2

    def test_multiple_sessions(self, tmp_path):
        mgr = StateManager(tmp_path)
        mgr.get_session(tmp_path / "chat.md")
        mgr.get_session(tmp_path / "chat" / "topic.md")
        assert len(mgr.list_sessions()) == 2

    def test_remove_session(self, tmp_path):
        mgr = StateManager(tmp_path)
        mgr.get_session(tmp_path / "chat.md")
        assert mgr.remove_session(tmp_path / "chat.md")
        assert len(mgr.list_sessions()) == 0

    def test_save_and_load(self, tmp_path):
        (tmp_path / ".chatmd").mkdir()
        mgr = StateManager(tmp_path)
        session = mgr.get_session(tmp_path / "chat.md")
        session.add_user_message("persist me")
        mgr.save_state()

        # Load into a new manager
        mgr2 = StateManager(tmp_path)
        sessions = mgr2.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].messages[0]["content"] == "persist me"

    def test_online_state(self, tmp_path):
        mgr = StateManager(tmp_path)
        assert mgr.is_online
        mgr.is_online = False
        assert not mgr.is_online
