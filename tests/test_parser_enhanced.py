"""Tests for enhanced parser features — @ai{} multi-line/inline, suffix trigger."""

from chatmd.engine.parser import CommandType, Parser
from chatmd.watcher.suffix_trigger import SuffixTrigger


class TestAtAiInline:
    def test_inline_at_ai(self):
        parser = Parser()
        cmds = parser.parse_lines(["@ai{翻译成英文}"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.AT_AI
        assert cmds[0].input_text == "翻译成英文"

    def test_inline_at_ai_in_sentence(self):
        parser = Parser()
        cmds = parser.parse_lines(["请帮我 @ai{总结这段话}"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.AT_AI
        assert cmds[0].input_text == "总结这段话"


class TestAtAiMultiLine:
    def test_multi_line_block(self):
        parser = Parser()
        lines = [
            "@ai{",
            "请帮我翻译以下内容：",
            "Hello World",
            "Good morning",
            "}",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.AT_AI
        assert "Hello World" in cmds[0].input_text
        assert "Good morning" in cmds[0].input_text

    def test_empty_block(self):
        parser = Parser()
        lines = ["@ai{", "}"]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 0

    def test_block_in_code_fence_ignored(self):
        parser = Parser()
        lines = [
            "```",
            "@ai{",
            "this should not be parsed",
            "}",
            "```",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 0


class TestSuffixTriggerParsing:
    def test_suffix_triggers_slash_command(self):
        parser = Parser()
        trigger = SuffixTrigger(marker=";", enabled=True)
        parser.set_suffix_trigger(trigger)

        cmds = parser.parse_lines(["/date;"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.SLASH_CMD
        assert cmds[0].command == "date"

    def test_suffix_triggers_open_chat(self):
        parser = Parser()
        trigger = SuffixTrigger(marker=";", enabled=True)
        parser.set_suffix_trigger(trigger)

        cmds = parser.parse_lines(["帮我总结这段话;"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.OPEN_CHAT
        assert cmds[0].input_text == "帮我总结这段话"

    def test_no_suffix_no_trigger(self):
        parser = Parser()
        trigger = SuffixTrigger(marker=";", enabled=True)
        parser.set_suffix_trigger(trigger)

        cmds = parser.parse_lines(["帮我总结这段话"])
        assert len(cmds) == 0

    def test_suffix_disabled_no_trigger(self):
        parser = Parser()
        trigger = SuffixTrigger(marker=";", enabled=False)
        parser.set_suffix_trigger(trigger)

        cmds = parser.parse_lines(["帮我总结这段话;"])
        assert len(cmds) == 0

    def test_slash_command_with_suffix_and_input(self):
        parser = Parser()
        trigger = SuffixTrigger(marker=";", enabled=True)
        parser.set_suffix_trigger(trigger)

        cmds = parser.parse_lines(["/translate 你好;"])
        assert len(cmds) == 1
        assert cmds[0].command == "translate"
        assert cmds[0].input_text == "你好"


class TestInlineBacktickProtection:
    """Commands inside inline backticks should not be parsed."""

    def test_backtick_slash_command_ignored(self):
        parser = Parser()
        cmds = parser.parse_lines(["- `/help` — 查看所有可用命令"])
        assert len(cmds) == 0

    def test_backtick_date_command_ignored(self):
        parser = Parser()
        cmds = parser.parse_lines(["- `/date` — 插入今天的日期"])
        assert len(cmds) == 0

    def test_backtick_at_ai_ignored(self):
        parser = Parser()
        cmds = parser.parse_lines(["使用 `@ai{翻译}` 语法"])
        assert len(cmds) == 0

    def test_bare_command_still_works(self):
        parser = Parser()
        cmds = parser.parse_lines(["/date"])
        assert len(cmds) == 1
        assert cmds[0].command == "date"

    def test_mixed_backtick_and_bare_command(self):
        parser = Parser()
        lines = [
            "- `/help` — 示例",
            "/date",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 1
        assert cmds[0].command == "date"


class TestChatmdCodeFenceProtection:
    """Agent output in ```chatmd code blocks should not be re-parsed."""

    def test_chatmd_fence_skipped(self):
        parser = Parser()
        lines = [
            "```chatmd /help 0.03s",
            "## 可用命令",
            "| /help | /h | 显示命令 |",
            "| /status | /st | 显示状态 |",
            "```",
            "/date",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 1
        assert cmds[0].command == "date"

    def test_commands_inside_chatmd_fence_ignored(self):
        parser = Parser()
        lines = [
            "```chatmd /status 0.01s",
            "/help",
            "/status",
            "/date",
            "```",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 0

    def test_at_ai_inside_chatmd_fence_ignored(self):
        parser = Parser()
        lines = [
            "```chatmd",
            "@ai{翻译}",
            "```",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 0


class TestExistingParserUnchanged:
    """Ensure existing parser functionality is not broken."""

    def test_basic_slash_command(self):
        parser = Parser()
        cmds = parser.parse_lines(["/date"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.SLASH_CMD
        assert cmds[0].command == "date"

    def test_slash_command_with_params(self):
        parser = Parser()
        cmds = parser.parse_lines(["/translate(日文) hello"])
        assert len(cmds) == 1
        assert cmds[0].command == "translate"
        assert cmds[0].args["_positional"] == "日文"
        assert cmds[0].input_text == "hello"

    def test_code_fence_protection(self):
        parser = Parser()
        lines = ["```", "/date", "```"]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 0

    def test_blockquote_protection(self):
        parser = Parser()
        cmds = parser.parse_lines(["> /date"])
        assert len(cmds) == 0
