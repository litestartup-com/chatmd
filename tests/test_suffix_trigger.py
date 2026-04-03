"""Tests for suffix signal trigger."""

from chatmd.watcher.suffix_trigger import SuffixTrigger


class TestSuffixTrigger:
    def test_disabled_by_default(self):
        trigger = SuffixTrigger()
        assert not trigger.enabled
        assert trigger.detect("hello;", 1) is None

    def test_enabled_detects_suffix(self):
        trigger = SuffixTrigger(marker=";", enabled=True)
        signal = trigger.detect("hello world;", 1)
        assert signal is not None
        assert signal.clean_text == "hello world"
        assert signal.marker == ";"
        assert signal.line_num == 1

    def test_trailing_whitespace(self):
        trigger = SuffixTrigger(marker=";", enabled=True)
        signal = trigger.detect("hello;   ", 1)
        assert signal is not None
        assert signal.clean_text == "hello"

    def test_no_suffix(self):
        trigger = SuffixTrigger(marker=";", enabled=True)
        assert trigger.detect("hello world", 1) is None

    def test_empty_content(self):
        trigger = SuffixTrigger(marker=";", enabled=True)
        assert trigger.detect(";", 1) is None

    def test_custom_marker(self):
        trigger = SuffixTrigger(marker=">>", enabled=True)
        signal = trigger.detect("do something>>", 1)
        assert signal is not None
        assert signal.clean_text == "do something"
        assert signal.marker == ">>"

    def test_change_marker(self):
        trigger = SuffixTrigger(marker=";", enabled=True)
        trigger.marker = "!!"
        assert trigger.detect("hello;", 1) is None
        signal = trigger.detect("hello!!", 1)
        assert signal is not None

    def test_slash_command_with_suffix(self):
        trigger = SuffixTrigger(marker=";", enabled=True)
        signal = trigger.detect("/translate hello;", 1)
        assert signal is not None
        assert signal.clean_text == "/translate hello"

    def test_enable_disable(self):
        trigger = SuffixTrigger(marker=";", enabled=False)
        assert trigger.detect("hello;", 1) is None
        trigger.enabled = True
        assert trigger.detect("hello;", 1) is not None
        trigger.enabled = False
        assert trigger.detect("hello;", 1) is None
