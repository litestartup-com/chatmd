"""Tests for the i18n module — translation, locale switching, key completeness."""

import pytest

from chatmd.i18n import get_all_keys, get_locale, set_locale, t


class TestTranslationFunction:
    """Test the t() function basics."""

    def setup_method(self):
        set_locale("en")

    def test_basic_key(self):
        assert t("skill.date.description") == "Insert today's date"

    def test_key_with_kwargs(self):
        result = t("output.status.active_tasks", count=5)
        assert "5" in result

    def test_missing_key_returns_key(self):
        assert t("nonexistent.key") == "nonexistent.key"

    def test_format_error_returns_template(self):
        # Pass wrong kwargs — should return the raw template, not crash
        result = t("output.status.active_tasks", wrong_param=1)
        assert "{count}" in result


class TestLocale:
    """Test locale switching."""

    def setup_method(self):
        set_locale("en")

    def test_default_locale(self):
        assert get_locale() == "en"

    def test_switch_to_chinese(self):
        set_locale("zh-CN")
        assert get_locale() == "zh-CN"
        assert t("skill.date.description") == "插入今天的日期"

    def test_switch_back_to_english(self):
        set_locale("zh-CN")
        set_locale("en")
        assert t("skill.date.description") == "Insert today's date"

    def test_unknown_locale_falls_back_to_english(self):
        set_locale("fr")
        # Should fall back to English
        assert t("skill.date.description") == "Insert today's date"

    def teardown_method(self):
        set_locale("en")


class TestKeyCompleteness:
    """Verify all locales have the same set of keys."""

    def test_zh_CN_has_all_english_keys(self):
        en_keys = get_all_keys("en")
        zh_keys = get_all_keys("zh-CN")
        missing = en_keys - zh_keys
        assert not missing, f"zh-CN missing keys: {missing}"

    def test_english_has_all_zh_CN_keys(self):
        en_keys = get_all_keys("en")
        zh_keys = get_all_keys("zh-CN")
        extra = zh_keys - en_keys
        assert not extra, f"zh-CN has extra keys not in en: {extra}"

    def test_key_count_matches(self):
        en_keys = get_all_keys("en")
        zh_keys = get_all_keys("zh-CN")
        assert len(en_keys) == len(zh_keys)

    def test_no_empty_values_in_en(self):
        from chatmd.i18n.en import MESSAGES

        empty = [k for k, v in MESSAGES.items() if not v.strip()]
        assert not empty, f"Empty values in en: {empty}"

    def test_no_empty_values_in_zh_CN(self):
        from chatmd.i18n.zh_CN import MESSAGES

        empty = [k for k, v in MESSAGES.items() if not v.strip()]
        assert not empty, f"Empty values in zh-CN: {empty}"


class TestSkillDescriptionKeys:
    """Verify all built-in skill descriptions have i18n keys."""

    @pytest.mark.parametrize("skill_name", [
        "date", "time", "now", "help", "status", "list",
        "ask", "translate", "sync", "log",
    ])
    def test_skill_description_key_exists(self, skill_name):
        key = f"skill.{skill_name}.description"
        en_keys = get_all_keys("en")
        assert key in en_keys, f"Missing en key: {key}"
        zh_keys = get_all_keys("zh-CN")
        assert key in zh_keys, f"Missing zh-CN key: {key}"

    @pytest.mark.parametrize("skill_name", [
        "date", "time", "now", "help", "status", "list",
        "ask", "translate", "sync", "log",
    ])
    def test_skill_description_not_empty(self, skill_name):
        set_locale("en")
        assert t(f"skill.{skill_name}.description") != f"skill.{skill_name}.description"
        set_locale("zh-CN")
        assert t(f"skill.{skill_name}.description") != f"skill.{skill_name}.description"
        set_locale("en")
