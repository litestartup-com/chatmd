"""Tests for /upload image upload skill (T-043)."""

from pathlib import Path
from unittest.mock import MagicMock

from chatmd.skills.base import SkillContext
from chatmd.skills.upload import (
    UploadSkill,
    find_local_images,
    is_local_path,
    resolve_image_path,
)


def _ctx(tmp_path: Path, filename: str = "chat.md") -> SkillContext:
    return SkillContext(
        source_file=tmp_path / filename,
        source_line=1,
        workspace=tmp_path,
    )


def _mock_provider(url: str = "https://cdn.example.com/img.png"):
    """Create a mock LiteStartupProvider with upload() method."""
    provider = MagicMock()
    provider.upload.return_value = {"success": True, "url": url}
    return provider


def _fail_provider(error: str = "timeout"):
    """Create a mock provider that fails upload."""
    provider = MagicMock()
    provider.upload.return_value = {"success": False, "error": error}
    return provider


# ── is_local_path tests ──────────────────────────────────────────────────


class TestIsLocalPath:
    def test_http_url(self):
        assert not is_local_path("http://example.com/img.png")

    def test_https_url(self):
        assert not is_local_path("https://cdn.example.com/img.png")

    def test_data_uri(self):
        assert not is_local_path("data:image/png;base64,abc")

    def test_protocol_relative(self):
        assert not is_local_path("//cdn.example.com/img.png")

    def test_relative_path(self):
        assert is_local_path("images/photo.png")

    def test_absolute_path(self):
        assert is_local_path("/home/user/photo.png")

    def test_file_uri(self):
        assert is_local_path("file:///home/user/photo.png")


# ── resolve_image_path tests ─────────────────────────────────────────────


class TestResolveImagePath:
    def test_relative_to_md_file(self, tmp_path):
        img = tmp_path / "images" / "photo.png"
        img.parent.mkdir()
        img.write_bytes(b"PNG")
        md = tmp_path / "chat.md"
        result = resolve_image_path("images/photo.png", md)
        assert result is not None
        assert result.name == "photo.png"

    def test_not_found(self, tmp_path):
        md = tmp_path / "chat.md"
        result = resolve_image_path("nonexistent.png", md)
        assert result is None

    def test_absolute_path(self, tmp_path):
        img = tmp_path / "abs.png"
        img.write_bytes(b"PNG")
        md = tmp_path / "chat.md"
        result = resolve_image_path(str(img), md)
        assert result is not None


# ── find_local_images tests ──────────────────────────────────────────────


class TestFindLocalImages:
    def test_markdown_image(self):
        content = "Text ![photo](images/photo.png) more"
        images = find_local_images(content)
        assert len(images) == 1
        assert images[0]["local_path"] == "images/photo.png"
        assert images[0]["alt_text"] == "photo"
        assert images[0]["format"] == "markdown"

    def test_html_image(self):
        content = 'Text <img src="images/photo.png" /> more'
        images = find_local_images(content)
        assert len(images) == 1
        assert images[0]["local_path"] == "images/photo.png"
        assert images[0]["format"] == "html"

    def test_skip_remote_url(self):
        content = "![photo](https://cdn.example.com/photo.png)"
        images = find_local_images(content)
        assert len(images) == 0

    def test_multiple_images(self):
        content = (
            "![a](a.png)\n"
            "![b](b.jpg)\n"
            '<img src="c.gif" />\n'
        )
        images = find_local_images(content)
        assert len(images) == 3

    def test_mixed_local_and_remote(self):
        content = (
            "![local](photo.png)\n"
            "![remote](https://cdn.example.com/photo.png)\n"
        )
        images = find_local_images(content)
        assert len(images) == 1
        assert images[0]["local_path"] == "photo.png"

    def test_no_images(self):
        content = "Just plain text, no images."
        images = find_local_images(content)
        assert len(images) == 0


# ── UploadSkill attribute tests ──────────────────────────────────────────


class TestUploadSkillAttributes:
    def test_name_and_aliases(self):
        skill = UploadSkill()
        assert skill.name == "upload"
        assert "up" in skill.aliases
        assert skill.is_async is True
        assert skill.requires_network is True

    def test_no_provider(self, tmp_path):
        skill = UploadSkill(provider=None)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert not result.success
        assert "not configured" in result.error.lower() or "未配置" in result.error


# ── Single file upload tests ─────────────────────────────────────────────


class TestUploadSingle:
    def test_upload_single_success(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"PNG data")
        provider = _mock_provider("https://cdn.example.com/photo.png")
        skill = UploadSkill(provider=provider)
        result = skill.execute(
            "", {"_positional": "photo.png"}, _ctx(tmp_path),
        )
        assert result.success
        assert "photo.png" in result.output
        assert "https://cdn.example.com/photo.png" in result.output

    def test_upload_single_not_found(self, tmp_path):
        provider = _mock_provider()
        skill = UploadSkill(provider=provider)
        result = skill.execute(
            "", {"_positional": "nonexistent.png"}, _ctx(tmp_path),
        )
        assert not result.success
        assert "not found" in result.error.lower() or "未找到" in result.error

    def test_upload_single_failed(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"PNG data")
        provider = _fail_provider("server error")
        skill = UploadSkill(provider=provider)
        result = skill.execute(
            "", {"_positional": "photo.png"}, _ctx(tmp_path),
        )
        assert not result.success
        assert "server error" in result.error

    def test_upload_single_unsupported_ext(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"PDF")
        provider = _mock_provider()
        skill = UploadSkill(provider=provider)
        result = skill.execute(
            "", {"_positional": "doc.pdf"}, _ctx(tmp_path),
        )
        assert not result.success
        assert "ext" in result.error.lower() or "扩展" in result.error

    def test_upload_single_too_large(self, tmp_path):
        img = tmp_path / "big.png"
        img.write_bytes(b"x" * (11 * 1024 * 1024))  # 11MB
        provider = _mock_provider()
        skill = UploadSkill(provider=provider, max_size_mb=10)
        result = skill.execute(
            "", {"_positional": "big.png"}, _ctx(tmp_path),
        )
        assert not result.success
        assert "size" in result.error.lower() or "大小" in result.error


# ── Batch scan upload tests ──────────────────────────────────────────────


class TestUploadScan:
    def test_scan_no_images(self, tmp_path):
        md = tmp_path / "chat.md"
        md.write_text("Just text, no images.\n", encoding="utf-8")
        provider = _mock_provider()
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "no" in result.output.lower() or "未发现" in result.output

    def test_scan_and_replace_markdown(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"PNG data")
        md = tmp_path / "chat.md"
        md.write_text(
            "Hello\n![pic](photo.png)\nWorld\n", encoding="utf-8",
        )
        url = "https://cdn.example.com/photo.png"
        provider = _mock_provider(url)
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "1" in result.output  # 1 uploaded

        # Verify file was updated
        new_content = md.read_text(encoding="utf-8")
        assert url in new_content
        # Original local ref ![pic](photo.png) should be gone
        assert "](photo.png)" not in new_content

    def test_scan_and_replace_html(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"PNG data")
        md = tmp_path / "chat.md"
        md.write_text(
            'Hello\n<img src="photo.png" />\nWorld\n',
            encoding="utf-8",
        )
        url = "https://cdn.example.com/photo.png"
        provider = _mock_provider(url)
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        new_content = md.read_text(encoding="utf-8")
        assert url in new_content

    def test_scan_skips_remote_urls(self, tmp_path):
        md = tmp_path / "chat.md"
        md.write_text(
            "![pic](https://cdn.example.com/existing.png)\n",
            encoding="utf-8",
        )
        provider = _mock_provider()
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "no" in result.output.lower() or "未发现" in result.output
        provider.upload.assert_not_called()

    def test_scan_missing_file_skipped(self, tmp_path):
        md = tmp_path / "chat.md"
        md.write_text(
            "![pic](nonexistent.png)\n", encoding="utf-8",
        )
        provider = _mock_provider()
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "skipped" in result.output.lower() or "跳过" in result.output

    def test_scan_multiple_images(self, tmp_path):
        for name in ["a.png", "b.jpg"]:
            (tmp_path / name).write_bytes(b"IMG")
        md = tmp_path / "chat.md"
        md.write_text(
            "![a](a.png)\n![b](b.jpg)\n", encoding="utf-8",
        )
        call_count = [0]
        urls = [
            "https://cdn.example.com/a.png",
            "https://cdn.example.com/b.jpg",
        ]

        def mock_upload(path):
            idx = call_count[0]
            call_count[0] += 1
            return {"success": True, "url": urls[idx]}

        provider = MagicMock()
        provider.upload.side_effect = mock_upload
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "2" in result.output  # 2 uploaded

    def test_scan_partial_failure(self, tmp_path):
        (tmp_path / "ok.png").write_bytes(b"IMG")
        (tmp_path / "fail.jpg").write_bytes(b"IMG")
        md = tmp_path / "chat.md"
        md.write_text(
            "![ok](ok.png)\n![fail](fail.jpg)\n", encoding="utf-8",
        )

        def mock_upload(path):
            if "ok" in path.name:
                return {"success": True, "url": "https://cdn/ok.png"}
            return {"success": False, "error": "server error"}

        provider = MagicMock()
        provider.upload.side_effect = mock_upload
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "1" in result.output  # summary contains counts


# ── Retry logic tests ────────────────────────────────────────────────────


class TestUploadRetry:
    def test_retry_on_failure(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"PNG data")
        md = tmp_path / "chat.md"
        md.write_text("![pic](photo.png)\n", encoding="utf-8")

        call_count = [0]

        def mock_upload(path):
            call_count[0] += 1
            if call_count[0] <= 2:
                return {"success": False, "error": "timeout"}
            return {
                "success": True,
                "url": "https://cdn.example.com/photo.png",
            }

        provider = MagicMock()
        provider.upload.side_effect = mock_upload
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        # Should have been called 3 times (2 failures + 1 success)
        assert call_count[0] == 3

    def test_exhaust_retries(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"PNG data")
        md = tmp_path / "chat.md"
        md.write_text("![pic](photo.png)\n", encoding="utf-8")

        provider = _fail_provider("persistent error")
        skill = UploadSkill(provider=provider)
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success  # scan itself succeeds
        assert "failed" in result.output.lower() or "失败" in result.output
        # Should have been called 3 times total (initial + 2 retries)
        assert provider.upload.call_count == 3


# ── Config override tests ────────────────────────────────────────────────


class TestUploadConfig:
    def test_custom_extensions(self, tmp_path):
        img = tmp_path / "photo.tiff"
        img.write_bytes(b"TIFF")
        provider = _mock_provider()
        # Default extensions don't include tiff
        skill = UploadSkill(provider=provider)
        result = skill.execute(
            "", {"_positional": "photo.tiff"}, _ctx(tmp_path),
        )
        assert not result.success

        # Custom extensions include tiff
        skill2 = UploadSkill(
            provider=provider,
            extensions={"tiff", "png"},
        )
        result2 = skill2.execute(
            "", {"_positional": "photo.tiff"}, _ctx(tmp_path),
        )
        assert result2.success

    def test_custom_max_size(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB
        provider = _mock_provider()
        # Small limit
        skill = UploadSkill(provider=provider, max_size_mb=1)
        result = skill.execute(
            "", {"_positional": "photo.png"}, _ctx(tmp_path),
        )
        assert not result.success

    def test_set_provider(self, tmp_path):
        img = tmp_path / "photo.png"
        img.write_bytes(b"PNG")
        skill = UploadSkill()
        skill.set_provider(_mock_provider())
        result = skill.execute(
            "", {"_positional": "photo.png"}, _ctx(tmp_path),
        )
        assert result.success
