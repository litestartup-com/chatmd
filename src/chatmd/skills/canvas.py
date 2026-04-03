"""Canvas skill — /canvas generates Obsidian Canvas mind-map files via AI.

Ported from X-AI prototype ``commands/canvas.py``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillContext, SkillResult

if TYPE_CHECKING:
    from chatmd.providers.base import AIProvider

logger = logging.getLogger(__name__)

# ── Layout constants ─────────────────────────────────────────────────────

NODE_WIDTH = 260
NODE_HEIGHT = 60
NODE_H_GAP = 80
NODE_V_GAP = 30
ROOT_X = 0
ROOT_Y = 0

COLORS = ["1", "2", "3", "4", "5", "6"]


# ── ID generation ────────────────────────────────────────────────────────

def _gen_id(seed: str) -> str:
    """Generate a 16-char hex ID deterministically from seed."""
    return hashlib.md5(seed.encode("utf-8")).hexdigest()[:16]  # noqa: S324


# ── Tree layout ──────────────────────────────────────────────────────────

class LayoutNode:
    """Intermediate node for tree layout computation."""

    def __init__(self, text: str, depth: int = 0, index: int = 0) -> None:
        self.text = text
        self.depth = depth
        self.index = index
        self.children: list[LayoutNode] = []
        self.x = 0.0
        self.y = 0.0
        self.width = NODE_WIDTH
        self.height = NODE_HEIGHT
        line_count = max(1, len(text) // 20 + text.count("\n"))
        if line_count > 2:
            self.height = max(NODE_HEIGHT, 30 + line_count * 22)

    def subtree_height(self) -> float:
        """Compute the total vertical space needed by this subtree."""
        if not self.children:
            return float(self.height)
        child_heights = [c.subtree_height() for c in self.children]
        return max(float(self.height), sum(child_heights) + NODE_V_GAP * (len(child_heights) - 1))


def layout_tree(root: LayoutNode) -> list[LayoutNode]:
    """Assign x, y coordinates using a left-to-right tree layout."""
    all_nodes: list[LayoutNode] = []

    def _collect(node: LayoutNode) -> None:
        all_nodes.append(node)
        for child in node.children:
            _collect(child)

    def _assign(node: LayoutNode, x: float, y_center: float) -> None:
        node.x = x
        node.y = y_center - node.height / 2

        if not node.children:
            return

        child_x = x + node.width + NODE_H_GAP
        total_h = sum(c.subtree_height() for c in node.children)
        total_h += NODE_V_GAP * (len(node.children) - 1)

        current_y = y_center - total_h / 2
        for child in node.children:
            child_h = child.subtree_height()
            child_center = current_y + child_h / 2
            _assign(child, child_x, child_center)
            current_y += child_h + NODE_V_GAP

    _assign(root, ROOT_X, ROOT_Y)
    _collect(root)
    return all_nodes


def build_tree_from_ai(data: dict) -> LayoutNode:
    """Build LayoutNode tree from AI structured response."""
    title = data.get("title", "Topic")
    root = LayoutNode(title, depth=0, index=0)

    def _add(parent: LayoutNode, children_data: list, depth: int) -> None:
        for i, child_data in enumerate(children_data):
            text = child_data.get("text", "")
            if not text:
                continue
            child = LayoutNode(text, depth=depth, index=i)
            parent.children.append(child)
            sub = child_data.get("children", [])
            if sub:
                _add(child, sub, depth + 1)

    _add(root, data.get("nodes", []), depth=1)
    return root


def tree_to_canvas(root: LayoutNode) -> dict:
    """Convert laid-out tree to Obsidian Canvas JSON format."""
    all_nodes = layout_tree(root)

    canvas_nodes = []
    canvas_edges: list[dict] = []
    node_id_map: dict[int, str] = {}

    for i, node in enumerate(all_nodes):
        nid = _gen_id(f"{node.text}_{node.depth}_{node.index}_{i}")
        node_id_map[id(node)] = nid
        color_idx = node.depth % len(COLORS)

        canvas_nodes.append({
            "id": nid,
            "x": int(node.x),
            "y": int(node.y),
            "width": int(node.width),
            "height": int(node.height),
            "type": "text",
            "text": node.text,
            "color": COLORS[color_idx],
        })

    def _edges(node: LayoutNode) -> None:
        parent_id = node_id_map[id(node)]
        for child in node.children:
            child_id = node_id_map[id(child)]
            edge_id = _gen_id(f"edge_{parent_id}_{child_id}")
            canvas_edges.append({
                "id": edge_id,
                "fromNode": parent_id,
                "fromSide": "right",
                "toNode": child_id,
                "toSide": "left",
            })
            _edges(child)

    _edges(root)
    return {"nodes": canvas_nodes, "edges": canvas_edges}


# ── JSON extraction helpers ──────────────────────────────────────────────

_CODE_FENCE_RE_CANVAS = re.compile(r"^```(?:json)?\s*\n([\s\S]*?)\n```\s*$")


def parse_ai_json(raw: str) -> tuple[dict | None, str]:
    """Parse JSON from AI response, stripping code fences if present."""
    cleaned = raw.strip()

    # Strip code fences
    m = _CODE_FENCE_RE_CANVAS.match(cleaned)
    if m:
        cleaned = m.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Try to extract JSON object from response
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                return None, t("error.canvas_invalid_json", detail=str(exc))
        else:
            return None, t("error.canvas_invalid_json", detail=str(exc))

    if "title" not in data or "nodes" not in data:
        return None, t("error.canvas_missing_fields")

    return data, ""


# ── Filename resolution ──────────────────────────────────────────────────

def resolve_canvas_path(workspace: Path, name: str, source_file: Path | None = None) -> Path:
    """Determine the output .canvas file path, handling conflicts."""
    if name.strip():
        stem = name.strip()
    elif source_file:
        stem = source_file.stem
    else:
        stem = "canvas"

    if not stem.endswith(".canvas"):
        stem += ".canvas"

    output = workspace / stem

    # Handle conflict
    if output.exists():
        base = output.stem
        counter = 2
        while True:
            candidate = workspace / f"{base}-{counter}.canvas"
            if not candidate.exists():
                return candidate
            counter += 1

    return output


# ── Skill ────────────────────────────────────────────────────────────────

# Max input chars for AI
_MAX_INPUT_CHARS = 8000


class CanvasSkill(Skill):
    """AI Canvas mind-map generation skill."""

    name = "canvas"
    description = "canvas"
    category = "ai"
    requires_network = True
    is_async = True
    aliases = ["cv"]

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider

    def set_provider(self, provider: AIProvider) -> None:
        """Inject the AI provider after construction."""
        self._provider = provider

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        if not self._provider:
            return SkillResult(
                success=False, output="",
                error=t("error.provider_not_configured"),
            )
        if not input_text.strip():
            return SkillResult(
                success=False, output="",
                error=t("error.canvas_empty_input"),
            )

        # Truncate very long text
        text = input_text
        if len(text) > _MAX_INPUT_CHARS:
            text = text[:_MAX_INPUT_CHARS]
            logger.warning("Canvas input truncated to %d chars", _MAX_INPUT_CHARS)

        # Determine output filename from args
        canvas_name = args.get("_positional", "")

        # Call AI with system prompt
        system_prompt = t("canvas.system_prompt")
        user_prompt = t("canvas.user_prompt", input_text=text)
        messages = [
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = self._provider.chat(
                messages,
                skill_name="canvas",
                system_prompt=system_prompt,
                temperature=0.3,
            )
        except RuntimeError as exc:
            return SkillResult(success=False, output="", error=str(exc))

        if not response or not response.strip():
            return SkillResult(
                success=False, output="",
                error=t("error.canvas_empty_response"),
            )

        # Parse AI response
        data, parse_err = parse_ai_json(response)
        if parse_err:
            return SkillResult(success=False, output="", error=parse_err)

        # Build tree and layout
        try:
            root = build_tree_from_ai(data)
            canvas_data = tree_to_canvas(root)
        except Exception as exc:
            logger.exception("Canvas layout error")
            return SkillResult(
                success=False, output="",
                error=t("error.canvas_layout_failed", detail=str(exc)),
            )

        # Resolve output path
        output_path = resolve_canvas_path(
            context.workspace, canvas_name, context.source_file,
        )

        # Write .canvas file
        try:
            output_path.write_text(
                json.dumps(canvas_data, ensure_ascii=False, indent="\t"),
                encoding="utf-8",
            )
            logger.info(
                "Canvas written: %s (%d nodes, %d edges)",
                output_path, len(canvas_data["nodes"]), len(canvas_data["edges"]),
            )
        except OSError as exc:
            return SkillResult(
                success=False, output="",
                error=t("error.canvas_write_failed", detail=str(exc)),
            )

        node_count = len(canvas_data["nodes"])
        edge_count = len(canvas_data["edges"])

        return SkillResult(
            success=True,
            output=t(
                "output.canvas.success",
                filename=output_path.name,
                nodes=node_count,
                edges=edge_count,
            ),
        )
