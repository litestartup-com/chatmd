"""Command parser — extracts structured commands from Markdown text changes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CommandType(Enum):
    """Types of parsed commands."""

    SLASH_CMD = "slash_cmd"
    AT_AI = "at_ai"
    OPEN_CHAT = "open_chat"
    INLINE_CMD = "inline_cmd"


@dataclass
class ParsedCommand:
    """A structured command extracted from user text."""

    type: CommandType
    command: str = ""
    args: dict = None
    input_text: str = ""
    source_file: Path | None = None
    source_line: int = 0
    end_line: int = 0
    raw_text: str = ""

    def __post_init__(self) -> None:
        if self.args is None:
            self.args = {}


# Regex patterns
_SLASH_CMD_RE = re.compile(
    r"^/(?P<cmd>[a-zA-Z_][\w-]*)"  # /command_name
    r"(?:\((?P<params>[^)]*)\))?"   # optional (params)
    r"(?:\s+(?P<input>.+))?$"       # optional input text
)

# @ai{...} — single-line: @ai{text here}
# Also matches inline: some text @ai{query} more text
_AT_AI_INLINE_RE = re.compile(
    r"@ai\{(?P<text>[^}]+)\}"       # @ai{natural language text} anywhere in line
)
_AT_AI_BLOCK_START_RE = re.compile(r"^@ai\{\s*$")   # @ai{ on its own line (block start)
_AT_AI_BLOCK_END_RE = re.compile(r"^\}\s*$")         # } on its own line (block end)

_CODE_FENCE_RE = re.compile(r"^```")
_BLOCKQUOTE_RE = re.compile(r"^>")
_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_CONTENT_FENCE_RE = re.compile(r"^:::$")
# /cmd{text} or /cmd(params){text} — inline command with braces
# Supports \} escaping inside braces.  Does NOT match empty braces {}.
_INLINE_CMD_RE = re.compile(
    r"/(?P<cmd>[a-zA-Z_][\w-]*)"
    r"(?:\((?P<params>[^)]*)\))?"
    r"\{(?P<text>(?:[^}\\]|\\.)+)\}"
)
# Detect /command ending with ::: (inline fence opener)
# Matches: /cmd:::  /cmd(params):::  /cmd :::  /cmd(params) :::
_CMD_FENCE_RE = re.compile(
    r"^/(?P<cmd>[a-zA-Z_][\w-]*)"   # /command_name
    r"(?:\((?P<params>[^)]*)\))?"    # optional (params)
    r"\s*:::$"                       # optional space then ::: at end
)


def _parse_params(param_str: str) -> dict:
    """Parse parameter string like ``lang=Japanese`` or positional ``Japanese``."""
    params: dict = {}
    if not param_str or not param_str.strip():
        return params

    parts = [p.strip() for p in param_str.split(",")]
    positional_idx = 0

    for part in parts:
        if "=" in part:
            key, _, value = part.partition("=")
            params[key.strip()] = value.strip().strip("'\"")
        else:
            # Positional parameter — store by index, also as first unnamed
            params[f"_pos_{positional_idx}"] = part.strip().strip("'\"")
            if positional_idx == 0:
                params["_positional"] = part.strip().strip("'\"")
            positional_idx += 1

    return params


class Parser:
    """Parses text lines into structured commands."""

    def __init__(self, command_prefix: str = "/") -> None:
        self._prefix = command_prefix
        self._suffix_trigger = None  # Optional SuffixTrigger instance

    def set_suffix_trigger(self, trigger: object) -> None:
        """Attach a SuffixTrigger instance for suffix signal detection."""
        self._suffix_trigger = trigger

    def parse_lines(
        self,
        lines: list[str],
        source_file: Path | None = None,
    ) -> list[ParsedCommand]:
        """Parse a list of text lines, returning any commands found.

        Skips lines inside code fences or blockquotes (protected regions).
        Supports multi-line @ai{ ... } blocks and ::: content fences.

        A ::: fence is opened when a slash command line ends with ``:::``
        (e.g. ``/translate(English) :::`` or ``/translate(English):::``).
        The fence collects all subsequent lines until a closing ``:::``
        on its own line.
        """
        commands: list[ParsedCommand] = []
        in_code_fence = False
        in_ai_block = False
        ai_block_lines: list[str] = []
        ai_block_start_line = 0
        # ::: fence state
        in_content_fence = False
        fence_lines: list[str] = []
        fence_cmd: ParsedCommand | None = None

        for line_num, raw_line in enumerate(lines, start=1):
            line = raw_line.rstrip()

            # Track code fence state (only outside content fence)
            if not in_content_fence and _CODE_FENCE_RE.match(line):
                in_code_fence = not in_code_fence
                continue

            # Skip protected regions
            if in_code_fence:
                continue

            # ::: content fence — collecting lines until closing :::
            if in_content_fence:
                if _CONTENT_FENCE_RE.match(line.strip()):
                    # Closing ::: — attach collected text to pending command
                    in_content_fence = False
                    if fence_cmd is not None:
                        fence_cmd.input_text = "\n".join(fence_lines).strip()
                        fence_cmd.end_line = line_num
                        # Build raw_text covering command + fence
                        start = fence_cmd.source_line - 1
                        fence_cmd.raw_text = "\n".join(
                            ln.rstrip() for ln in lines[start:line_num]
                        )
                        commands.append(fence_cmd)
                        fence_cmd = None
                    fence_lines = []
                else:
                    fence_lines.append(line)
                continue

            if _BLOCKQUOTE_RE.match(line):
                continue

            # Multi-line @ai{ ... } block
            if in_ai_block:
                if _AT_AI_BLOCK_END_RE.match(line):
                    in_ai_block = False
                    text = "\n".join(ai_block_lines).strip()
                    if text:
                        commands.append(ParsedCommand(
                            type=CommandType.AT_AI,
                            input_text=text,
                            source_file=source_file,
                            source_line=ai_block_start_line,
                            raw_text=f"@ai{{{text}}}",
                        ))
                    ai_block_lines = []
                else:
                    ai_block_lines.append(line)
                continue

            if _AT_AI_BLOCK_START_RE.match(line):
                in_ai_block = True
                ai_block_start_line = line_num
                ai_block_lines = []
                continue

            # Check for /command::: or /command ::: → inline fence opener
            fence_m = _CMD_FENCE_RE.match(line.strip())
            if fence_m:
                params_str = fence_m.group("params") or ""
                fence_cmd = ParsedCommand(
                    type=CommandType.SLASH_CMD,
                    command=fence_m.group("cmd"),
                    args=_parse_params(params_str),
                    input_text="",
                    source_file=source_file,
                    source_line=line_num,
                    raw_text=line,
                )
                in_content_fence = True
                fence_lines = []
                continue

            # Try inline /cmd{text} first (multiple per line possible),
            # then fall back to regular line-start /command or @ai{}.
            inline_cmds = self._parse_inline_cmds(
                line, source_file, line_num,
            )
            if inline_cmds:
                commands.extend(inline_cmds)
            else:
                cmd = self._parse_single_line(line, source_file, line_num)
                if cmd is not None:
                    commands.append(cmd)

        # Unclosed fence — discard the pending command (safety)
        return commands

    @staticmethod
    def _parse_inline_cmds(
        line: str,
        source_file: Path | None,
        line_num: int,
    ) -> list[ParsedCommand]:
        """Extract ``/cmd{text}`` inline commands from a line.

        Returns an empty list when:
        - The line contains ``@ai{...}`` (higher priority).
        - All matches are inside backtick spans.
        - No valid matches exist.
        """
        stripped = line.strip()
        if not stripped:
            return []

        # Strip backtick spans for matching
        clean = _INLINE_CODE_RE.sub(lambda m: " " * len(m.group()), line)

        # @ai{} takes priority — if present, skip inline cmd detection
        if _AT_AI_INLINE_RE.search(clean):
            return []

        matches = list(_INLINE_CMD_RE.finditer(clean))
        if not matches:
            return []

        results: list[ParsedCommand] = []
        for m in matches:
            text = m.group("text")
            if not text:
                continue
            params_str = m.group("params") or ""
            # Use the original line span for raw_text
            raw = line[m.start():m.end()]
            results.append(ParsedCommand(
                type=CommandType.INLINE_CMD,
                command=m.group("cmd"),
                args=_parse_params(params_str),
                input_text=text,
                source_file=source_file,
                source_line=line_num,
                raw_text=raw,
            ))
        return results

    def parse_changed_line(
        self,
        line: str,
        source_file: Path | None = None,
        line_num: int = 0,
    ) -> ParsedCommand | None:
        """Parse a single changed line into a command (or None)."""
        return self._parse_single_line(line.rstrip(), source_file, line_num)

    def _parse_single_line(
        self,
        line: str,
        source_file: Path | None,
        line_num: int,
    ) -> ParsedCommand | None:
        """Attempt to parse one line as a slash command, @ai{}, or suffix trigger."""
        stripped = line.strip()
        if not stripped:
            return None

        # 0. Skip lines where command-like text is inside inline backticks
        clean_for_check = _INLINE_CODE_RE.sub("", stripped)
        if not clean_for_check.strip():
            return None

        # 1. Try inline @ai{...} (only if @ai{ exists outside backticks)
        m = _AT_AI_INLINE_RE.search(clean_for_check)
        if m:
            return ParsedCommand(
                type=CommandType.AT_AI,
                input_text=m.group("text").strip(),
                source_file=source_file,
                source_line=line_num,
                raw_text=line,
            )

        # 2. Check suffix trigger — strip marker before further parsing
        effective_line = clean_for_check.strip()
        has_suffix = False
        suffix_enabled = (
            self._suffix_trigger is not None and self._suffix_trigger.enabled
        )
        if self._suffix_trigger is not None:
            signal = self._suffix_trigger.detect(effective_line, line_num)
            if signal is not None:
                effective_line = signal.clean_text
                has_suffix = True

        # When suffix mode is active, only lines WITH the suffix marker
        # are processed.  This prevents auto-save editors from triggering
        # commands while the user is still typing.
        # (Naturally-closed syntaxes like @ai{}, /cmd{}, ::: are handled
        # earlier and are NOT gated by the suffix requirement.)
        if suffix_enabled and not has_suffix:
            return None

        # 3. Try /command (must start at beginning of cleaned line)
        m = _SLASH_CMD_RE.match(effective_line)
        if m:
            params_str = m.group("params") or ""
            return ParsedCommand(
                type=CommandType.SLASH_CMD,
                command=m.group("cmd"),
                args=_parse_params(params_str),
                input_text=(m.group("input") or "").strip(),
                source_file=source_file,
                source_line=line_num,
                raw_text=line,
            )

        # 4. Suffix-triggered open chat (non-slash text with suffix marker)
        if has_suffix:
            return ParsedCommand(
                type=CommandType.OPEN_CHAT,
                input_text=effective_line,
                source_file=source_file,
                source_line=line_num,
                raw_text=line,
            )

        return None
