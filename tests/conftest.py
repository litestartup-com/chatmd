"""Shared fixtures and automatic test markers for the ChatMD test suite.

Markers are assigned automatically based on file name convention:
    test_e2e.py          -> @pytest.mark.e2e + @pytest.mark.integration
    test_*_integration.py -> @pytest.mark.integration
    everything else      -> @pytest.mark.unit

Usage:
    pytest                      # run ALL tests
    pytest -m unit              # fast unit tests only
    pytest -m integration       # integration tests
    pytest -m e2e               # end-to-end only
    pytest -m "not e2e"         # skip slow e2e tests
    pytest --changed            # (with pytest-testmon) only affected tests
"""

from __future__ import annotations

import pytest

# Files whose tests are integration-level (touch filesystem or combine modules)
_INTEGRATION_FILES = frozenset({
    "test_e2e.py",
    "test_file_writer.py",
    "test_git_sync.py",
    "test_init.py",
    "test_index_manager.py",
    "test_offline_queue.py",
    "test_hot_reload.py",
    "test_upgrade.py",
})

_E2E_FILES = frozenset({
    "test_e2e.py",
})


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item],
) -> None:
    """Auto-apply markers based on test file names."""
    for item in items:
        filename = item.path.name if item.path else ""

        if filename in _E2E_FILES:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.integration)
        elif filename in _INTEGRATION_FILES:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
