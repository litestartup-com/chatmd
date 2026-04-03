"""Lightweight i18n module — dict-based translation with t() function."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_current_locale: str = "en"
_catalogs: dict[str, dict[str, str]] = {}


def _load_catalog(locale: str) -> dict[str, str]:
    """Lazily load a message catalog for the given locale."""
    if locale in _catalogs:
        return _catalogs[locale]

    normalized = locale.replace("-", "_")  # "zh-CN" -> "zh_CN"
    try:
        mod = __import__(f"chatmd.i18n.{normalized}", fromlist=["MESSAGES"])
        _catalogs[locale] = mod.MESSAGES
    except (ImportError, AttributeError):
        logger.warning("No i18n catalog for locale '%s', falling back to 'en'", locale)
        _catalogs[locale] = {}
    return _catalogs[locale]


def set_locale(locale: str) -> None:
    """Set the active locale (e.g. 'en', 'zh-CN')."""
    global _current_locale
    _current_locale = locale
    _load_catalog(locale)


def get_locale() -> str:
    """Return the current locale string."""
    return _current_locale


def t(key: str, **kwargs: Any) -> str:
    """Translate a message key using the current locale.

    Falls back to English if the key is missing in the active locale.
    Supports ``str.format``-style placeholders::

        t("output.status.active_tasks", count=3)
        # -> "Active tasks: 3"
    """
    # Try current locale
    catalog = _load_catalog(_current_locale)
    text = catalog.get(key)

    # Fallback to English
    if text is None and _current_locale != "en":
        en_catalog = _load_catalog("en")
        text = en_catalog.get(key)

    # Ultimate fallback: return the key itself
    if text is None:
        logger.debug("Missing i18n key: '%s' (locale=%s)", key, _current_locale)
        return key

    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            logger.warning("Format error for key '%s': %s", key, kwargs)
            return text
    return text


def get_all_keys(locale: str = "en") -> set[str]:
    """Return all message keys for a given locale (useful for tests)."""
    catalog = _load_catalog(locale)
    return set(catalog.keys())
