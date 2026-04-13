"""Auto-upload handler — detects new local image references and uploads them.

Integrates with the FileWatcher callback in Agent. When ``upload.auto``
is enabled, each file-change event triggers a scan for *new* local
image references that were not present in the previous snapshot.
Only genuinely new references are uploaded, preventing re-upload loops.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from chatmd.skills.upload import (
    find_local_images,
    resolve_image_path,
)

if TYPE_CHECKING:
    from chatmd.providers.litestartup import LiteStartupProvider

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2


class AutoUploadHandler:
    """Detects and uploads new local images on every file change.

    Keeps a per-file snapshot of known local image paths so that only
    *new* references trigger an upload.  After successful upload the
    file content is rewritten with remote URLs.
    """

    def __init__(
        self,
        provider: LiteStartupProvider,
        *,
        max_size_mb: float = 10,
        extensions: set[str] | None = None,
    ) -> None:
        self._provider = provider
        self._max_size_mb = max_size_mb
        self._extensions = extensions or {
            "jpg", "jpeg", "png", "gif", "webp", "svg", "ico",
        }
        # Per-file set of local_path strings already seen / uploaded
        self._known: dict[str, set[str]] = {}

    # -- Public API -----------------------------------------------------------

    def process(self, filepath: Path, content: str) -> bool:
        """Scan *content* for new local images, upload and rewrite.

        Returns ``True`` if the file was modified (caller should re-read).
        """
        file_key = str(filepath)
        images = find_local_images(content)
        local_paths = {img["local_path"] for img in images}

        # Initialise known set on first call (empty — so existing local
        # images are treated as "new" and will be uploaded).
        if file_key not in self._known:
            self._known[file_key] = set()
            logger.info(
                "Auto-upload: first scan for %s, found %d local image(s)",
                filepath.name, len(local_paths),
            )

        # Find genuinely new references
        known = self._known[file_key]
        new_images = [img for img in images if img["local_path"] not in known]

        if not new_images:
            # Update known set (some may have been removed)
            self._known[file_key] = local_paths
            return False

        logger.info("Auto-upload: %d new image(s) in %s", len(new_images), filepath.name)

        new_content = content
        uploaded_count = 0

        for img in new_images:
            local_path = img["local_path"]
            resolved = resolve_image_path(local_path, filepath)
            if not resolved:
                logger.warning("Auto-upload: file not found: %s", local_path)
                known.add(local_path)  # mark as known to avoid retry
                continue

            if not self._validate(resolved):
                known.add(local_path)
                continue

            result = self._upload_with_retry(resolved)
            if result["success"]:
                remote_url = result["url"]
                old_ref = img["full_match"]
                if img["format"] == "html":
                    new_ref = f'{img["html_prefix"]}{remote_url}{img["html_suffix"]}'
                else:
                    new_ref = f'![{img["alt_text"]}]({remote_url})'
                new_content = new_content.replace(old_ref, new_ref, 1)
                uploaded_count += 1
                logger.info("Auto-upload: %s -> %s", local_path, remote_url)
            else:
                logger.warning(
                    "Auto-upload: failed %s: %s", local_path, result["error"],
                )

            # Mark as known regardless of success/failure
            known.add(local_path)

        if uploaded_count > 0:
            try:
                filepath.write_text(new_content, encoding="utf-8")
                logger.info("Auto-upload: rewrote %s (%d uploads)", filepath.name, uploaded_count)
            except OSError as exc:
                logger.error("Auto-upload: failed to write %s: %s", filepath, exc)
                return False

        # Refresh known set from new content
        self._known[file_key] = {
            img["local_path"] for img in find_local_images(new_content)
        }

        return uploaded_count > 0

    def reset(self, filepath: Path | None = None) -> None:
        """Clear known images for a file, or all files if None."""
        if filepath is None:
            self._known.clear()
        else:
            self._known.pop(str(filepath), None)

    # -- Internal helpers -----------------------------------------------------

    def _validate(self, path: Path) -> bool:
        """Check extension and size."""
        ext = path.suffix.lstrip(".").lower()
        if ext not in self._extensions:
            logger.debug("Auto-upload: skipping unsupported ext: %s", path.suffix)
            return False
        try:
            if path.stat().st_size > self._max_size_mb * 1024 * 1024:
                logger.debug("Auto-upload: skipping too large: %s", path.name)
                return False
        except OSError:
            return False
        return True

    def _upload_with_retry(self, path: Path) -> dict:
        """Upload with retry logic."""
        last: dict = {"success": False, "error": "unknown"}
        for attempt in range(_MAX_RETRIES + 1):
            last = self._provider.upload(path)
            if last["success"]:
                return last
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "Auto-upload retry %d/%d for %s",
                    attempt + 1, _MAX_RETRIES, path.name,
                )
        return last
