"""Tests for auto-upload handler (T-044)."""

from unittest.mock import MagicMock

from chatmd.watcher.auto_upload import AutoUploadHandler


def _mock_provider(url: str = "https://cdn.example.com/img.png"):
    """Create a mock LiteStartupProvider with upload() method."""
    provider = MagicMock()
    provider.upload.return_value = {"success": True, "url": url}
    return provider


def _fail_provider(error: str = "timeout"):
    provider = MagicMock()
    provider.upload.return_value = {"success": False, "error": error}
    return provider


# ── Seeding / first-call behavior ────────────────────────────────────────


class TestAutoUploadSeeding:
    def test_first_call_uploads_existing_images(self, tmp_path):
        """First call should upload existing local images."""
        md = tmp_path / "chat.md"
        md.write_text("![pic](photo.png)\n", encoding="utf-8")
        (tmp_path / "photo.png").write_bytes(b"PNG")

        url = "https://cdn.example.com/photo.png"
        provider = _mock_provider(url)
        handler = AutoUploadHandler(provider=provider)
        modified = handler.process(md, md.read_text(encoding="utf-8"))

        assert modified is True
        provider.upload.assert_called_once()
        result = md.read_text(encoding="utf-8")
        assert url in result

    def test_second_call_no_new_images(self, tmp_path):
        """Second call with no new local images should not upload."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")

        provider = _mock_provider()
        handler = AutoUploadHandler(provider=provider)

        # First call — no images
        handler.process(md, md.read_text(encoding="utf-8"))
        # Same content again
        modified = handler.process(md, md.read_text(encoding="utf-8"))

        assert modified is False
        provider.upload.assert_not_called()


# ── New image detection ──────────────────────────────────────────────────


class TestAutoUploadNewImages:
    def test_detects_new_image(self, tmp_path):
        """New image added after seed should trigger upload."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")

        url = "https://cdn.example.com/photo.png"
        provider = _mock_provider(url)
        handler = AutoUploadHandler(provider=provider)

        # Seed with no images
        handler.process(md, md.read_text(encoding="utf-8"))

        # Add a new image
        (tmp_path / "photo.png").write_bytes(b"PNG")
        new_content = "Hello\n![pic](photo.png)\n"
        md.write_text(new_content, encoding="utf-8")

        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is True
        provider.upload.assert_called_once()

        # File should be updated with remote URL
        result = md.read_text(encoding="utf-8")
        assert url in result
        assert "](photo.png)" not in result

    def test_multiple_new_images(self, tmp_path):
        """Multiple new images should all be uploaded."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")

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
        handler = AutoUploadHandler(provider=provider)

        # Seed
        handler.process(md, md.read_text(encoding="utf-8"))

        # Add two images
        (tmp_path / "a.png").write_bytes(b"PNG")
        (tmp_path / "b.jpg").write_bytes(b"JPG")
        new_content = "Hello\n![a](a.png)\n![b](b.jpg)\n"
        md.write_text(new_content, encoding="utf-8")

        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is True
        assert call_count[0] == 2

    def test_skips_already_uploaded_image(self, tmp_path):
        """Image already uploaded should not be re-uploaded."""
        md = tmp_path / "chat.md"
        (tmp_path / "new.png").write_bytes(b"PNG")
        # Start with only a remote image (already uploaded)
        md.write_text("![old](https://cdn.example.com/old.png)\n", encoding="utf-8")

        provider = _mock_provider("https://cdn.example.com/new.png")
        handler = AutoUploadHandler(provider=provider)

        # First call — no local images to upload
        handler.process(md, md.read_text(encoding="utf-8"))
        assert provider.upload.call_count == 0

        # Add new local image
        new_content = "![old](https://cdn.example.com/old.png)\n![new](new.png)\n"
        md.write_text(new_content, encoding="utf-8")

        handler.process(md, md.read_text(encoding="utf-8"))

        # Should only upload new.png
        assert provider.upload.call_count == 1
        uploaded_path = provider.upload.call_args[0][0]
        assert uploaded_path.name == "new.png"

    def test_skips_remote_urls(self, tmp_path):
        """Remote URLs should never trigger upload."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")

        provider = _mock_provider()
        handler = AutoUploadHandler(provider=provider)

        # Seed
        handler.process(md, md.read_text(encoding="utf-8"))

        # Add only remote image
        new_content = "Hello\n![pic](https://example.com/photo.png)\n"
        md.write_text(new_content, encoding="utf-8")

        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is False
        provider.upload.assert_not_called()


# ── Failure handling ─────────────────────────────────────────────────────


class TestAutoUploadFailures:
    def test_file_not_found_skipped(self, tmp_path):
        """Missing local file should be skipped without error."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")

        provider = _mock_provider()
        handler = AutoUploadHandler(provider=provider)

        # Seed
        handler.process(md, md.read_text(encoding="utf-8"))

        # Add image ref but no actual file
        new_content = "Hello\n![pic](nonexistent.png)\n"
        md.write_text(new_content, encoding="utf-8")

        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is False
        provider.upload.assert_not_called()

    def test_upload_failure_marks_as_known(self, tmp_path):
        """Failed upload should mark image as known to avoid retry loop."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")
        (tmp_path / "photo.png").write_bytes(b"PNG")

        provider = _fail_provider("server error")
        handler = AutoUploadHandler(provider=provider)

        # Seed
        handler.process(md, md.read_text(encoding="utf-8"))

        # Add image
        new_content = "Hello\n![pic](photo.png)\n"
        md.write_text(new_content, encoding="utf-8")

        handler.process(md, md.read_text(encoding="utf-8"))
        # 3 attempts (initial + 2 retries)
        assert provider.upload.call_count == 3

        # Second process call should NOT retry (marked as known)
        provider.upload.reset_mock()
        handler.process(md, md.read_text(encoding="utf-8"))
        provider.upload.assert_not_called()

    def test_unsupported_extension_skipped(self, tmp_path):
        """Unsupported file extension should be skipped."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")
        (tmp_path / "doc.pdf").write_bytes(b"PDF")

        provider = _mock_provider()
        handler = AutoUploadHandler(provider=provider)

        handler.process(md, md.read_text(encoding="utf-8"))

        new_content = "Hello\n![doc](doc.pdf)\n"
        md.write_text(new_content, encoding="utf-8")

        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is False
        provider.upload.assert_not_called()

    def test_too_large_file_skipped(self, tmp_path):
        """File exceeding max_size_mb should be skipped."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")
        big = tmp_path / "big.png"
        big.write_bytes(b"x" * (2 * 1024 * 1024))

        provider = _mock_provider()
        handler = AutoUploadHandler(provider=provider, max_size_mb=1)

        handler.process(md, md.read_text(encoding="utf-8"))

        new_content = "Hello\n![big](big.png)\n"
        md.write_text(new_content, encoding="utf-8")

        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is False
        provider.upload.assert_not_called()


# ── HTML image support ───────────────────────────────────────────────────


class TestAutoUploadHtml:
    def test_html_image_uploaded(self, tmp_path):
        """HTML <img> tags should also trigger auto-upload."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")
        (tmp_path / "photo.png").write_bytes(b"PNG")

        url = "https://cdn.example.com/photo.png"
        provider = _mock_provider(url)
        handler = AutoUploadHandler(provider=provider)

        handler.process(md, md.read_text(encoding="utf-8"))

        new_content = 'Hello\n<img src="photo.png" />\n'
        md.write_text(new_content, encoding="utf-8")

        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is True

        result = md.read_text(encoding="utf-8")
        assert url in result


# ── Reset behavior ───────────────────────────────────────────────────────


class TestAutoUploadReset:
    def test_reset_single_file(self, tmp_path):
        """Reset should clear known images so next call re-uploads."""
        md = tmp_path / "chat.md"
        (tmp_path / "photo.png").write_bytes(b"PNG")
        md.write_text("![pic](photo.png)\n", encoding="utf-8")

        url = "https://cdn.example.com/photo.png"
        provider = _mock_provider(url)
        handler = AutoUploadHandler(provider=provider)

        # First call uploads
        handler.process(md, md.read_text(encoding="utf-8"))
        assert provider.upload.call_count == 1

        # Reset
        handler.reset(md)
        provider.upload.reset_mock()

        # Write back a local image (simulate re-adding)
        md.write_text("![pic](photo.png)\n", encoding="utf-8")
        (tmp_path / "photo.png").write_bytes(b"PNG")

        # Next call should upload again after reset
        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is True
        provider.upload.assert_called_once()

    def test_reset_all(self, tmp_path):
        """Reset(None) should clear all known images."""
        md1 = tmp_path / "a.md"
        md2 = tmp_path / "b.md"
        md1.write_text("Hello\n", encoding="utf-8")
        md2.write_text("World\n", encoding="utf-8")

        handler = AutoUploadHandler(provider=_mock_provider())
        handler.process(md1, md1.read_text(encoding="utf-8"))
        handler.process(md2, md2.read_text(encoding="utf-8"))

        handler.reset()

        # Both should re-seed on next call
        assert handler._known == {}


# ── Config override ──────────────────────────────────────────────────────


class TestAutoUploadConfig:
    def test_custom_extensions(self, tmp_path):
        """Custom extensions should be respected."""
        md = tmp_path / "chat.md"
        md.write_text("Hello\n", encoding="utf-8")
        (tmp_path / "photo.tiff").write_bytes(b"TIFF")

        provider = _mock_provider()
        handler = AutoUploadHandler(
            provider=provider,
            extensions={"tiff", "png"},
        )

        handler.process(md, md.read_text(encoding="utf-8"))

        new_content = "Hello\n![pic](photo.tiff)\n"
        md.write_text(new_content, encoding="utf-8")

        modified = handler.process(md, md.read_text(encoding="utf-8"))
        assert modified is True
        provider.upload.assert_called_once()
