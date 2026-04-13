"""File watcher — watchdog-based monitoring with debounce and agent write filtering."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from chatmd.infra.file_writer import FileWriter

logger = logging.getLogger(__name__)

_EXCLUDED_DIRS = {".chatmd", ".git", "node_modules", ".obsidian", ".vscode", ".idea", "__pycache__"}


class _ChangeHandler(FileSystemEventHandler):
    """Handle file system events, filtering and debouncing.

    Uses a **trailing-edge** debounce with a **max-wait ceiling** so that
    editors with atomic-save (Sublime Text: write-tmp → rename) do not
    keep resetting the timer indefinitely.

    *   ``debounce_ms`` — quiet period after the **last** event before firing.
    *   ``max_wait_ms`` — hard ceiling from the **first** event in a burst.
        Once this time elapses the callback fires on the next event
        regardless of whether more events follow.
    """

    def __init__(
        self,
        workspace: Path,
        callback: Callable[[Path], None],
        file_writer: FileWriter,
        debounce_ms: int = 300,
        max_wait_ms: int = 600,
        watch_dirs: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._workspace = workspace
        self._callback = callback
        self._file_writer = file_writer
        self._debounce_ms = debounce_ms
        self._max_wait_ms = max_wait_ms
        self._watch_dirs = set(watch_dirs or ["chatmd/"])
        self._ignore_patterns = set(ignore_patterns or ["_index.md"])
        self._timers: dict[str, threading.Timer] = {}
        self._first_event_ts: dict[str, float] = {}
        self._lock = threading.Lock()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Called when a file is modified."""
        if event.is_directory:
            return

        filepath = Path(event.src_path).resolve()

        # Only process .md files
        if filepath.suffix.lower() != ".md":
            return

        # Skip hidden/dotfiles (e.g. .~chat.md, .DS_Store)
        if filepath.name.startswith("."):
            return

        # Skip Agent's own writes
        if self._file_writer.is_agent_write(filepath):
            logger.debug("Skipping agent write: %s", filepath)
            return

        # Check if file is in watched scope
        if not self._is_watched(filepath):
            return

        # Check ignore patterns
        if filepath.name in self._ignore_patterns:
            return

        # Debounce with max-wait ceiling
        key = str(filepath)
        now = time.monotonic()
        with self._lock:
            if key in self._timers:
                self._timers[key].cancel()
                logger.debug("Debounce reset for %s", filepath.name)
                # If max-wait ceiling exceeded, fire immediately
                first_ts = self._first_event_ts.get(key, now)
                if (now - first_ts) * 1000 >= self._max_wait_ms:
                    logger.debug("Max-wait reached for %s, firing now", filepath.name)
                    del self._timers[key]
                    self._first_event_ts.pop(key, None)
                    threading.Thread(
                        target=self._fire, args=[filepath], daemon=True,
                    ).start()
                    return
            else:
                logger.debug("Debounce start for %s", filepath.name)
                self._first_event_ts[key] = now

            timer = threading.Timer(
                self._debounce_ms / 1000.0,
                self._fire,
                args=[filepath],
            )
            self._timers[key] = timer
            timer.start()

    def _is_watched(self, filepath: Path) -> bool:
        """Check if the file falls within the watched scope."""
        try:
            rel = filepath.relative_to(self._workspace)
        except ValueError:
            return False

        # Exclude internal directories and any dot-prefixed directory
        if any(part in _EXCLUDED_DIRS or part.startswith(".") for part in rel.parts):
            return False

        rel_str = str(rel).replace("\\", "/")

        # Directory match
        for d in self._watch_dirs:
            if d == ".":
                return True
            d_clean = d.rstrip("/")
            if rel_str.startswith(d_clean + "/"):
                return True

        return False

    def _fire(self, filepath: Path) -> None:
        """Actually invoke the callback after debounce period."""
        key = str(filepath)
        with self._lock:
            self._timers.pop(key, None)
            self._first_event_ts.pop(key, None)
        logger.info("File change detected: %s", filepath)
        try:
            self._callback(filepath)
        except Exception:
            logger.exception("Error processing file change: %s", filepath)


class FileWatcher:
    """Watches workspace files for changes using watchdog."""

    def __init__(
        self,
        workspace: Path,
        callback: Callable[[Path], None],
        file_writer: FileWriter,
        debounce_ms: int = 300,
        max_wait_ms: int = 600,
        watch_dirs: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        self._workspace = workspace
        self._observer = Observer()
        self._handler = _ChangeHandler(
            workspace=workspace,
            callback=callback,
            file_writer=file_writer,
            debounce_ms=debounce_ms,
            max_wait_ms=max_wait_ms,
            watch_dirs=watch_dirs,
            ignore_patterns=ignore_patterns,
        )

    def start(self) -> None:
        """Start watching the workspace directory."""
        self._observer.schedule(self._handler, str(self._workspace), recursive=True)
        self._observer.start()
        logger.info("FileWatcher started: %s", self._workspace)

    def stop(self) -> None:
        """Stop watching."""
        self._observer.stop()
        self._observer.join(timeout=5)
        logger.info("FileWatcher stopped")
