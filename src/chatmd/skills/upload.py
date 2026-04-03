"""Upload skill — /upload scans markdown for local images, uploads, and replaces.

Ported from X-AI prototype ``services/upload.py``.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillContext, SkillResult

if TYPE_CHECKING:
    from chatmd.providers.litestartup import LiteStartupProvider

logger = logging.getLogger(__name__)

# ── Image detection patterns ─────────────────────────────────────────────

# Markdown image: ![alt](local_path)
_MD_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

# HTML image: <img src="local_path" ... />
_HTML_IMG_RE = re.compile(
    r'(<img\s[^>]*?src\s*=\s*["\'])([^"\']+)(["\'][^>]*?/?>)',
    re.IGNORECASE,
)

# Default upload config
_DEFAULT_MAX_SIZE_MB = 10
_DEFAULT_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"}
_MAX_RETRIES = 2


# ── Helpers ──────────────────────────────────────────────────────────────


def is_local_path(path: str) -> bool:
    """Check if a path is a local file path (not a URL)."""
    if path.startswith(("http://", "https://", "data:", "//")):
        return False
    return True


def resolve_image_path(local_path: str, md_file: Path) -> Path | None:
    """Resolve a local image path relative to the markdown file."""
    if local_path.startswith("file:///"):
        clean = local_path[8:] if len(local_path) > 9 and local_path[9] == ":" else local_path[7:]
        p = Path(clean)
        return p if p.exists() else None
    p = md_file.parent / local_path
    if p.exists():
        return p
    abs_p = Path(local_path)
    return abs_p if abs_p.exists() else None


def find_local_images(content: str) -> list[dict]:
    """Find all local image references in markdown content."""
    images: list[dict] = []

    for m in _MD_IMG_RE.finditer(content):
        local_path = m.group(2)
        if is_local_path(local_path):
            images.append({
                "full_match": m.group(0),
                "alt_text": m.group(1),
                "local_path": local_path,
                "format": "markdown",
            })

    for m in _HTML_IMG_RE.finditer(content):
        local_path = m.group(2)
        if is_local_path(local_path):
            images.append({
                "full_match": m.group(0),
                "alt_text": "",
                "local_path": local_path,
                "format": "html",
                "html_prefix": m.group(1),
                "html_suffix": m.group(3),
            })

    return images


def _check_extension(path: Path, allowed: set[str]) -> bool:
    """Check if the file extension is in the allowed set."""
    ext = path.suffix.lstrip(".").lower()
    return ext in allowed


def _check_size(path: Path, max_mb: float) -> bool:
    """Check if the file size is within the limit."""
    try:
        size = path.stat().st_size
        return size <= max_mb * 1024 * 1024
    except OSError:
        return False


# ── Skill ────────────────────────────────────────────────────────────────


class UploadSkill(Skill):
    """Manual image upload skill — /upload or /up."""

    name = "upload"
    description = "upload"
    category = "general"
    requires_network = True
    is_async = True
    aliases = ["up"]

    def __init__(
        self,
        provider: LiteStartupProvider | None = None,
        *,
        max_size_mb: float = _DEFAULT_MAX_SIZE_MB,
        extensions: set[str] | None = None,
    ) -> None:
        self._provider = provider
        self._max_size_mb = max_size_mb
        self._extensions = extensions or _DEFAULT_EXTENSIONS

    def set_provider(self, provider: LiteStartupProvider) -> None:
        """Inject the LiteStartup provider after construction."""
        self._provider = provider

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        if not self._provider:
            return SkillResult(
                success=False, output="",
                error=t("error.upload_not_configured"),
            )

        positional = args.get("_positional", "").strip()

        if positional:
            return self._upload_single(positional, context)
        return self._upload_scan(context)

    # ── Single file upload (/up(path)) ───────────────────────────────────

    def _upload_single(
        self, local_path: str, context: SkillContext,
    ) -> SkillResult:
        """Upload a single image and return markdown reference."""
        resolved = resolve_image_path(local_path, context.source_file)
        if not resolved:
            return SkillResult(
                success=False, output="",
                error=t("error.upload_file_not_found", path=local_path),
            )

        err = self._validate_file(resolved)
        if err:
            return SkillResult(success=False, output="", error=err)

        result = self._do_upload(resolved)
        if not result["success"]:
            return SkillResult(
                success=False, output="",
                error=t("error.upload_failed", path=local_path, detail=result["error"]),
            )

        remote_url = result["url"]
        filename = resolved.name
        return SkillResult(
            success=True,
            output=t(
                "output.upload.single_success",
                filename=filename,
                url=remote_url,
            ),
        )

    # ── Batch scan upload (/up) ──────────────────────────────────────────

    def _upload_scan(self, context: SkillContext) -> SkillResult:
        """Scan source file for local images, upload all, replace paths."""
        source = context.source_file
        if not source.exists():
            return SkillResult(
                success=False, output="",
                error=t("error.upload_source_not_found"),
            )

        try:
            content = source.read_text(encoding="utf-8")
        except OSError as exc:
            return SkillResult(
                success=False, output="",
                error=t("error.upload_read_failed", detail=str(exc)),
            )

        images = find_local_images(content)
        if not images:
            return SkillResult(
                success=True,
                output=t("output.upload.no_images"),
            )

        uploaded = 0
        failed = 0
        skipped = 0
        details: list[str] = []
        new_content = content

        for img in images:
            local_path = img["local_path"]
            resolved = resolve_image_path(local_path, source)

            if not resolved:
                skipped += 1
                details.append(
                    t("output.upload.detail_not_found", path=local_path),
                )
                continue

            err = self._validate_file(resolved)
            if err:
                skipped += 1
                details.append(
                    t("output.upload.detail_skipped", path=local_path, reason=err),
                )
                continue

            # Upload with retry
            result = self._do_upload_with_retry(resolved)
            if result["success"]:
                remote_url = result["url"]
                old_ref = img["full_match"]
                if img["format"] == "html":
                    new_ref = f'{img["html_prefix"]}{remote_url}{img["html_suffix"]}'
                else:
                    new_ref = f'![{img["alt_text"]}]({remote_url})'
                new_content = new_content.replace(old_ref, new_ref, 1)
                uploaded += 1
                details.append(
                    t("output.upload.detail_ok", path=local_path, url=remote_url),
                )
            else:
                failed += 1
                details.append(
                    t(
                        "output.upload.detail_failed",
                        path=local_path,
                        detail=result["error"],
                    ),
                )

        # Write back if any replacements
        if new_content != content:
            try:
                source.write_text(new_content, encoding="utf-8")
            except OSError as exc:
                return SkillResult(
                    success=False, output="",
                    error=t("error.upload_write_failed", detail=str(exc)),
                )

        summary = t(
            "output.upload.scan_summary",
            found=len(images),
            uploaded=uploaded,
            failed=failed,
            skipped=skipped,
        )
        detail_text = "\n".join(details) if details else ""
        output = f"{summary}\n{detail_text}" if detail_text else summary

        return SkillResult(success=True, output=output)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _validate_file(self, path: Path) -> str:
        """Validate file extension and size. Returns error string or ''."""
        if not _check_extension(path, self._extensions):
            return t(
                "error.upload_unsupported_ext",
                ext=path.suffix,
                allowed=", ".join(sorted(self._extensions)),
            )
        if not _check_size(path, self._max_size_mb):
            return t(
                "error.upload_too_large",
                path=path.name,
                max_mb=self._max_size_mb,
            )
        return ""

    def _do_upload(self, path: Path) -> dict:
        """Upload a single file via LiteStartup provider."""
        assert self._provider is not None
        return self._provider.upload(path)

    def _do_upload_with_retry(self, path: Path) -> dict:
        """Upload with retry logic (max 2 retries)."""
        last_result: dict = {"success": False, "error": "unknown"}
        for attempt in range(_MAX_RETRIES + 1):
            last_result = self._do_upload(path)
            if last_result["success"]:
                return last_result
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "Upload retry %d/%d for %s: %s",
                    attempt + 1, _MAX_RETRIES, path.name, last_result["error"],
                )
        return last_result
