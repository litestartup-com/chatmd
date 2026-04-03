"""Tests for offline queue."""

from chatmd.infra.offline_queue import OfflineQueue, QueuedItem


class TestOfflineQueue:
    def test_enqueue_dequeue(self, tmp_path):
        (tmp_path / ".chatmd").mkdir()
        q = OfflineQueue(tmp_path)
        item = QueuedItem(
            id="task-abc1",
            skill_name="translate",
            input_text="Hello",
            args={"_positional": "日文"},
            source_file="chat.md",
            source_line=5,
            raw_text="/translate(日文) Hello",
        )
        q.enqueue(item)
        assert q.size == 1

        out = q.dequeue()
        assert out is not None
        assert out.id == "task-abc1"
        assert q.is_empty

    def test_peek(self, tmp_path):
        (tmp_path / ".chatmd").mkdir()
        q = OfflineQueue(tmp_path)
        q.enqueue(QueuedItem(
            id="t1", skill_name="ask", input_text="hi",
            args={}, source_file="chat.md", source_line=1, raw_text="/ask hi",
        ))
        q.enqueue(QueuedItem(
            id="t2", skill_name="ask", input_text="bye",
            args={}, source_file="chat.md", source_line=2, raw_text="/ask bye",
        ))
        items = q.peek()
        assert len(items) == 2
        assert q.size == 2  # peek doesn't remove

    def test_remove(self, tmp_path):
        (tmp_path / ".chatmd").mkdir()
        q = OfflineQueue(tmp_path)
        q.enqueue(QueuedItem(
            id="t1", skill_name="ask", input_text="hi",
            args={}, source_file="chat.md", source_line=1, raw_text="/ask hi",
        ))
        assert q.remove("t1")
        assert q.is_empty
        assert not q.remove("nonexistent")

    def test_persistence(self, tmp_path):
        (tmp_path / ".chatmd").mkdir()
        q = OfflineQueue(tmp_path)
        q.enqueue(QueuedItem(
            id="t1", skill_name="translate", input_text="hello",
            args={}, source_file="chat.md", source_line=1, raw_text="/translate hello",
        ))

        # Load into new queue
        q2 = OfflineQueue(tmp_path)
        assert q2.size == 1
        item = q2.dequeue()
        assert item.id == "t1"
        assert item.skill_name == "translate"

    def test_fifo_order(self, tmp_path):
        (tmp_path / ".chatmd").mkdir()
        q = OfflineQueue(tmp_path)
        for i in range(3):
            q.enqueue(QueuedItem(
                id=f"t{i}", skill_name="ask", input_text=str(i),
                args={}, source_file="chat.md", source_line=i, raw_text=f"/ask {i}",
            ))
        assert q.dequeue().id == "t0"
        assert q.dequeue().id == "t1"
        assert q.dequeue().id == "t2"
