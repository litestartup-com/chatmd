"""Tests for /canvas AI Canvas mind-map generation skill (T-041)."""

import json
from pathlib import Path

from chatmd.providers.base import AIProvider
from chatmd.skills.base import SkillContext
from chatmd.skills.canvas import (
    CanvasSkill,
    LayoutNode,
    build_tree_from_ai,
    layout_tree,
    parse_ai_json,
    resolve_canvas_path,
    tree_to_canvas,
)


def _ctx(tmp_path: Path) -> SkillContext:
    return SkillContext(
        source_file=tmp_path / "chat.md", source_line=1, workspace=tmp_path,
    )


# ── Mock providers ───────────────────────────────────────────────────────

_VALID_AI_RESPONSE = json.dumps({
    "title": "AI Overview",
    "nodes": [
        {
            "text": "Machine Learning",
            "children": [
                {"text": "Supervised", "children": []},
                {"text": "Unsupervised", "children": []},
            ],
        },
        {
            "text": "Deep Learning",
            "children": [
                {"text": "CNN", "children": []},
                {"text": "RNN", "children": []},
            ],
        },
    ],
})


class _MockCanvasProvider(AIProvider):
    name = "mock_canvas"

    def __init__(self, response: str = _VALID_AI_RESPONSE):
        self._response = response

    def chat(self, messages: list[dict], **kwargs) -> str:
        return self._response


class _FailProvider(AIProvider):
    name = "fail"

    def chat(self, messages: list[dict], **kwargs) -> str:
        raise RuntimeError("AI API timeout")


# ── Layout algorithm tests ───────────────────────────────────────────────


class TestLayoutNode:
    def test_basic_node(self):
        node = LayoutNode("Hello", depth=0, index=0)
        assert node.text == "Hello"
        assert node.depth == 0
        assert node.width == 260
        assert node.height == 60

    def test_long_text_increases_height(self):
        node = LayoutNode("A" * 100, depth=0, index=0)
        assert node.height > 60

    def test_subtree_height_leaf(self):
        node = LayoutNode("leaf")
        assert node.subtree_height() == 60.0

    def test_subtree_height_with_children(self):
        root = LayoutNode("root")
        root.children = [LayoutNode("a"), LayoutNode("b")]
        h = root.subtree_height()
        # Two children: 60 + 30 (gap) + 60 = 150
        assert h == 150.0


class TestLayoutTree:
    def test_single_node(self):
        root = LayoutNode("root")
        nodes = layout_tree(root)
        assert len(nodes) == 1
        assert nodes[0].x == 0

    def test_two_levels(self):
        root = LayoutNode("root")
        root.children = [LayoutNode("a", 1, 0), LayoutNode("b", 1, 1)]
        nodes = layout_tree(root)
        assert len(nodes) == 3
        # Children should be to the right of root
        for child in root.children:
            assert child.x > root.x

    def test_children_vertically_distributed(self):
        root = LayoutNode("root")
        root.children = [LayoutNode("a", 1, 0), LayoutNode("b", 1, 1), LayoutNode("c", 1, 2)]
        layout_tree(root)
        ys = [c.y for c in root.children]
        # Each child should be below the previous
        assert ys[0] < ys[1] < ys[2]


class TestBuildTreeFromAI:
    def test_basic_structure(self):
        data = {
            "title": "Test",
            "nodes": [
                {"text": "A", "children": [{"text": "A1", "children": []}]},
                {"text": "B", "children": []},
            ],
        }
        root = build_tree_from_ai(data)
        assert root.text == "Test"
        assert len(root.children) == 2
        assert root.children[0].text == "A"
        assert len(root.children[0].children) == 1
        assert root.children[0].children[0].text == "A1"

    def test_empty_nodes(self):
        data = {"title": "Empty", "nodes": []}
        root = build_tree_from_ai(data)
        assert root.text == "Empty"
        assert len(root.children) == 0

    def test_skips_empty_text(self):
        data = {
            "title": "T",
            "nodes": [{"text": "", "children": []}, {"text": "B", "children": []}],
        }
        root = build_tree_from_ai(data)
        assert len(root.children) == 1
        assert root.children[0].text == "B"


class TestTreeToCanvas:
    def test_basic_canvas(self):
        data = {
            "title": "Root",
            "nodes": [
                {"text": "A", "children": []},
                {"text": "B", "children": []},
            ],
        }
        root = build_tree_from_ai(data)
        canvas = tree_to_canvas(root)
        assert "nodes" in canvas
        assert "edges" in canvas
        assert len(canvas["nodes"]) == 3  # root + A + B
        assert len(canvas["edges"]) == 2  # root->A, root->B

    def test_canvas_node_structure(self):
        root = LayoutNode("Test")
        canvas = tree_to_canvas(root)
        node = canvas["nodes"][0]
        assert "id" in node
        assert "x" in node
        assert "y" in node
        assert "width" in node
        assert "height" in node
        assert node["type"] == "text"
        assert node["text"] == "Test"
        assert "color" in node

    def test_edge_structure(self):
        data = {"title": "R", "nodes": [{"text": "A", "children": []}]}
        root = build_tree_from_ai(data)
        canvas = tree_to_canvas(root)
        edge = canvas["edges"][0]
        assert "id" in edge
        assert "fromNode" in edge
        assert "toNode" in edge
        assert edge["fromSide"] == "right"
        assert edge["toSide"] == "left"


# ── JSON parsing tests ───────────────────────────────────────────────────


class TestParseAIJson:
    def test_plain_json(self):
        raw = '{"title": "T", "nodes": []}'
        data, err = parse_ai_json(raw)
        assert data is not None
        assert err == ""
        assert data["title"] == "T"

    def test_code_fence_json(self):
        raw = '```json\n{"title": "T", "nodes": []}\n```'
        data, err = parse_ai_json(raw)
        assert data is not None
        assert data["title"] == "T"

    def test_invalid_json(self):
        raw = "not json at all"
        data, err = parse_ai_json(raw)
        assert data is None
        assert err  # Non-empty error

    def test_missing_fields(self):
        raw = '{"something": "else"}'
        data, err = parse_ai_json(raw)
        assert data is None
        assert "title" in err or "nodes" in err

    def test_json_embedded_in_text(self):
        raw = 'Here is the result:\n{"title": "T", "nodes": []}\nDone.'
        data, err = parse_ai_json(raw)
        assert data is not None
        assert data["title"] == "T"


# ── Path resolution tests ────────────────────────────────────────────────


class TestResolveCanvasPath:
    def test_with_explicit_name(self, tmp_path):
        path = resolve_canvas_path(tmp_path, "mymap")
        assert path.name == "mymap.canvas"
        assert path.parent == tmp_path

    def test_from_source_file(self, tmp_path):
        source = tmp_path / "chat.md"
        path = resolve_canvas_path(tmp_path, "", source)
        assert path.name == "chat.canvas"

    def test_fallback_name(self, tmp_path):
        path = resolve_canvas_path(tmp_path, "")
        assert path.name == "canvas.canvas"

    def test_conflict_resolution(self, tmp_path):
        (tmp_path / "chat.canvas").write_text("{}", encoding="utf-8")
        path = resolve_canvas_path(tmp_path, "", tmp_path / "chat.md")
        assert path.name == "chat-2.canvas"

    def test_multiple_conflicts(self, tmp_path):
        (tmp_path / "chat.canvas").write_text("{}", encoding="utf-8")
        (tmp_path / "chat-2.canvas").write_text("{}", encoding="utf-8")
        path = resolve_canvas_path(tmp_path, "", tmp_path / "chat.md")
        assert path.name == "chat-3.canvas"


# ── Skill execution tests ───────────────────────────────────────────────


class TestCanvasSkill:
    def test_attributes(self):
        skill = CanvasSkill()
        assert skill.name == "canvas"
        assert skill.category == "ai"
        assert skill.is_async is True
        assert "cv" in skill.aliases

    def test_no_provider(self, tmp_path):
        skill = CanvasSkill(provider=None)
        result = skill.execute("some text", {}, _ctx(tmp_path))
        assert not result.success
        assert "not configured" in result.error

    def test_empty_input(self, tmp_path):
        skill = CanvasSkill(provider=_MockCanvasProvider())
        result = skill.execute("", {}, _ctx(tmp_path))
        assert not result.success

    def test_provider_failure(self, tmp_path):
        skill = CanvasSkill(provider=_FailProvider())
        result = skill.execute("some text", {}, _ctx(tmp_path))
        assert not result.success
        assert "timeout" in result.error

    def test_successful_canvas_generation(self, tmp_path):
        skill = CanvasSkill(provider=_MockCanvasProvider())
        result = skill.execute("AI is transforming the world", {}, _ctx(tmp_path))
        assert result.success
        assert "Canvas" in result.output or "canvas" in result.output

        # Check that .canvas file was created
        canvas_files = list(tmp_path.glob("*.canvas"))
        assert len(canvas_files) == 1

        # Validate canvas JSON
        canvas_data = json.loads(canvas_files[0].read_text(encoding="utf-8"))
        assert "nodes" in canvas_data
        assert "edges" in canvas_data
        assert len(canvas_data["nodes"]) == 7  # root + 2 L1 + 4 L2

    def test_explicit_filename(self, tmp_path):
        skill = CanvasSkill(provider=_MockCanvasProvider())
        result = skill.execute("text", {"_positional": "mymap"}, _ctx(tmp_path))
        assert result.success
        assert (tmp_path / "mymap.canvas").exists()

    def test_set_provider(self, tmp_path):
        skill = CanvasSkill()
        skill.set_provider(_MockCanvasProvider())
        result = skill.execute("text", {}, _ctx(tmp_path))
        assert result.success

    def test_invalid_ai_response(self, tmp_path):
        skill = CanvasSkill(provider=_MockCanvasProvider("not json"))
        result = skill.execute("text", {}, _ctx(tmp_path))
        assert not result.success

    def test_empty_ai_response(self, tmp_path):
        skill = CanvasSkill(provider=_MockCanvasProvider(""))
        result = skill.execute("text", {}, _ctx(tmp_path))
        assert not result.success
        assert "empty" in result.error.lower() or "空" in result.error

    def test_canvas_with_code_fence_response(self, tmp_path):
        response = f"```json\n{_VALID_AI_RESPONSE}\n```"
        skill = CanvasSkill(provider=_MockCanvasProvider(response))
        result = skill.execute("text", {}, _ctx(tmp_path))
        assert result.success
