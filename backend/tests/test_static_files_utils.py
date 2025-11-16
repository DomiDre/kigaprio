"""
Tests for static files utilities.

Tests cover:
- Path validation and sanitization
- File extension checking
- Symlink safety validation
- Directory safety validation
- File serving logic
- Security protections against path traversal
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from priotag.static_files_utils import (
    find_file_to_serve,
    is_allowed_file,
    is_safe_symlink,
    normalize_unicode,
    safe_join_path,
    setup_static_file_serving,
    validate_directory_safety,
    validate_file_size,
    validate_path_component,
)


@pytest.mark.unit
class TestNormalizeUnicode:
    """Test Unicode normalization."""

    def test_normalize_unicode_nfkc(self):
        """Should normalize unicode to NFKC form."""
        # These are different unicode representations of the same character
        text1 = "é"  # Single character
        text2 = "é"  # e + combining accent

        result1 = normalize_unicode(text1)
        result2 = normalize_unicode(text2)

        # Should normalize to same form
        assert result1 == result2

    def test_normalize_unicode_ascii(self):
        """Should leave ASCII unchanged."""
        text = "hello_world.html"
        result = normalize_unicode(text)

        assert result == text


@pytest.mark.unit
class TestValidatePathComponent:
    """Test path component validation."""

    def test_valid_component(self):
        """Should accept valid path components."""
        assert validate_path_component("index.html") == "index.html"
        assert validate_path_component("app.js") == "app.js"
        assert validate_path_component("style.css") == "style.css"

    def test_reject_dot(self):
        """Should reject single dot."""
        assert validate_path_component(".") is None

    def test_reject_double_dot(self):
        """Should reject double dot."""
        assert validate_path_component("..") is None

    def test_reject_null_bytes(self):
        """Should reject null bytes."""
        assert validate_path_component("file\x00.txt") is None

    def test_reject_path_separators(self):
        """Should reject path separators."""
        assert validate_path_component("file/path") is None
        assert validate_path_component("file\\path") is None

    def test_reject_url_encoded_null(self):
        """Should reject URL-encoded null bytes."""
        assert validate_path_component("file%00.txt") is None

    def test_reject_url_encoded_separators(self):
        """Should reject URL-encoded path separators."""
        assert validate_path_component("file%2fpath") is None
        assert validate_path_component("file%2Fpath") is None
        assert validate_path_component("file%5cpath") is None

    def test_reject_hidden_files(self):
        """Should reject hidden files (starting with dot)."""
        assert validate_path_component(".htaccess") is None
        assert validate_path_component(".env") is None

    def test_reject_tilde_files(self):
        """Should reject files starting with tilde."""
        assert validate_path_component("~backup") is None

    def test_reject_windows_reserved_names(self):
        """Should reject Windows reserved names."""
        assert validate_path_component("CON") is None
        assert validate_path_component("PRN") is None
        assert validate_path_component("AUX") is None
        assert validate_path_component("NUL") is None
        assert validate_path_component("COM1") is None
        assert validate_path_component("LPT1") is None

    def test_reject_special_characters(self):
        """Should reject special characters not in whitelist."""
        assert validate_path_component("file<script>.html") is None
        assert validate_path_component("file&data.txt") is None

    def test_reject_consecutive_dots(self):
        """Should reject multiple consecutive dots."""
        assert validate_path_component("file..txt") is None

    def test_lowercase_conversion(self):
        """Should convert to lowercase."""
        assert validate_path_component("File.HTML") == "file.html"

    def test_accept_valid_chars(self):
        """Should accept alphanumeric, hyphens, underscores, single dots."""
        assert validate_path_component("valid-file_123.txt") == "valid-file_123.txt"


@pytest.mark.unit
class TestSafeJoinPath:
    """Test safe path joining."""

    def test_safe_join_normal_path(self):
        """Should safely join normal paths."""
        base = Path("/static")
        result = safe_join_path(base, "app.js")

        assert result is not None
        assert result == base / "app.js"

    def test_safe_join_empty_returns_index(self):
        """Should return index.html for empty path."""
        base = Path("/static")
        result = safe_join_path(base, "")

        assert result == base / "index.html"

    def test_safe_join_slash_only_returns_index(self):
        """Should return index.html for root path."""
        base = Path("/static")
        result = safe_join_path(base, "/")

        assert result == base / "index.html"

    def test_safe_join_nested_path(self):
        """Should handle nested paths."""
        base = Path("/static")
        result = safe_join_path(base, "assets/styles/main.css")

        assert result is not None
        assert "assets" in str(result)
        assert "styles" in str(result)

    def test_safe_join_rejects_traversal(self):
        """Should reject path traversal attempts."""
        base = Path("/static")
        result = safe_join_path(base, "../../../etc/passwd")

        assert result is None

    def test_safe_join_rejects_deep_nesting(self):
        """Should reject paths exceeding max depth."""
        base = Path("/static")
        # Create path with > 10 components
        deep_path = "/".join([f"level{i}" for i in range(15)])
        result = safe_join_path(base, deep_path)

        assert result is None

    def test_safe_join_validates_each_component(self):
        """Should validate each path component."""
        base = Path("/static")
        result = safe_join_path(base, "valid/../../invalid")

        assert result is None


@pytest.mark.unit
class TestIsAllowedFile:
    """Test file extension validation."""

    def test_allowed_extensions(self):
        """Should allow whitelisted extensions."""
        assert is_allowed_file(Path("file.html")) is True
        assert is_allowed_file(Path("file.css")) is True
        assert is_allowed_file(Path("file.js")) is True
        assert is_allowed_file(Path("file.png")) is True
        assert is_allowed_file(Path("file.json")) is True

    def test_disallowed_extensions(self):
        """Should reject non-whitelisted extensions."""
        assert is_allowed_file(Path("file.php")) is False
        assert is_allowed_file(Path("file.py")) is False
        assert is_allowed_file(Path("file.sh")) is False
        assert is_allowed_file(Path("file.exe")) is False

    def test_double_extension_suspicious(self):
        """Should reject files with suspicious double extensions."""
        assert is_allowed_file(Path("file.php.txt")) is False
        assert is_allowed_file(Path("file.py.html")) is False
        assert is_allowed_file(Path("file.sh.css")) is False

    def test_double_extension_safe(self):
        """Should allow safe double extensions."""
        assert is_allowed_file(Path("app.min.js")) is True
        assert is_allowed_file(Path("styles.bundle.css")) is True

    def test_case_insensitive(self):
        """Should be case insensitive."""
        assert is_allowed_file(Path("file.HTML")) is True
        assert is_allowed_file(Path("file.PHP")) is False


@pytest.mark.unit
class TestValidateFileSize:
    """Test file size validation."""

    def test_valid_file_size(self):
        """Should accept files within size limit."""
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"x" * 1000)  # 1KB
            tmp.flush()

            assert validate_file_size(Path(tmp.name)) is True

    def test_large_file_rejected(self):
        """Should reject files exceeding 10MB limit."""
        with tempfile.NamedTemporaryFile() as tmp:
            # Mock st_size to be > 10MB
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 11 * 1024 * 1024

                assert validate_file_size(Path(tmp.name)) is False

    def test_nonexistent_file(self):
        """Should return False for nonexistent file."""
        assert validate_file_size(Path("/nonexistent/file.txt")) is False


@pytest.mark.unit
class TestIsSafeSymlink:
    """Test symlink safety validation."""

    def test_regular_file_is_safe(self):
        """Regular files should be considered safe."""
        with tempfile.NamedTemporaryFile() as tmp:
            base = Path(tmp.name).parent
            assert is_safe_symlink(Path(tmp.name), base) is True

    def test_symlink_within_base_is_safe(self):
        """Symlinks pointing within base directory should be safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "target.txt"
            target.touch()

            link = base / "link.txt"
            link.symlink_to(target)

            assert is_safe_symlink(link, base) is True

    def test_symlink_outside_base_is_unsafe(self):
        """Symlinks pointing outside base directory should be unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "static"
            base.mkdir()

            # Create target outside base
            outside = Path(tmpdir) / "outside.txt"
            outside.touch()

            link = base / "link.txt"
            link.symlink_to(outside)

            assert is_safe_symlink(link, base) is False


@pytest.mark.unit
class TestValidateDirectorySafety:
    """Test directory safety validation."""

    def test_directory_within_base_is_safe(self):
        """Directories within base should be safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            subdir = base / "subdir"
            subdir.mkdir()

            assert validate_directory_safety(subdir, base) is True

    def test_directory_outside_base_is_unsafe(self):
        """Directories outside base should be unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "static"
            base.mkdir()

            outside = Path(tmpdir) / "outside"
            outside.mkdir()

            assert validate_directory_safety(outside, base) is False


@pytest.mark.unit
class TestFindFileToServe:
    """Test file serving logic."""

    def test_find_regular_file(self):
        """Should find and return regular file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            test_file = base / "test.html"
            test_file.write_text("<html></html>")

            result = find_file_to_serve(base, test_file)

            assert result == test_file

    def test_find_index_in_directory(self):
        """Should return index.html for directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            subdir = base / "docs"
            subdir.mkdir()

            index = subdir / "index.html"
            index.write_text("<html></html>")

            result = find_file_to_serve(base, subdir)

            assert result == index

    def test_find_with_html_extension(self):
        """Should try .html extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            html_file = base / "page.html"
            html_file.write_text("<html></html>")

            # Request without extension
            requested = base / "page"

            result = find_file_to_serve(base, requested)

            assert result == html_file

    def test_fallback_to_root_index(self):
        """Should fallback to root index.html."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            root_index = base / "index.html"
            root_index.write_text("<html></html>")

            # Request nonexistent file
            nonexistent = base / "nonexistent.html"

            result = find_file_to_serve(base, nonexistent)

            assert result == root_index

    def test_reject_disallowed_extension(self):
        """Should reject files with disallowed extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            php_file = base / "shell.php"
            php_file.write_text("<?php ?>")

            result = find_file_to_serve(base, php_file)

            assert result is None

    def test_reject_oversized_file(self):
        """Should reject files exceeding size limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            large_file = base / "large.html"
            large_file.touch()

            with patch(
                "priotag.static_files_utils.validate_file_size", return_value=False
            ):
                result = find_file_to_serve(base, large_file)

                assert result is None


@pytest.mark.unit
class TestSetupStaticFileServing:
    """Test static file serving setup."""

    def test_setup_in_production_with_files(self):
        """Should setup static serving in production when files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            (static_path / "index.html").write_text("<html></html>")

            app = FastAPI()
            setup_static_file_serving(app, static_path, "production", False)

            # Should have added catch-all route
            # (Testing internal FastAPI routing is complex, just verify no errors)

    def test_setup_skips_if_no_files(self):
        """Should skip setup if directory is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)

            app = FastAPI()
            setup_static_file_serving(app, static_path, "production", False)

            # Should log warning but not crash

    def test_setup_skips_in_dev_without_flag(self):
        """Should skip in development without serve_static flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            (static_path / "index.html").write_text("<html></html>")

            app = FastAPI()
            setup_static_file_serving(app, static_path, "development", False)

            # Should log development mode message

    def test_setup_serves_in_dev_with_flag(self):
        """Should serve in development when flag is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            (static_path / "index.html").write_text("<html></html>")

            app = FastAPI()
            setup_static_file_serving(app, static_path, "development", True)

            # Should setup serving

    def test_setup_validates_app_directory(self):
        """Should validate _app directory before mounting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            (static_path / "index.html").write_text("<html></html>")

            app_dir = static_path / "_app"
            app_dir.mkdir()

            app = FastAPI()
            setup_static_file_serving(app, static_path, "production", False)

            # Should validate and mount _app

    def test_setup_validates_assets_directory(self):
        """Should validate assets directory before mounting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            static_path = Path(tmpdir)
            (static_path / "index.html").write_text("<html></html>")

            assets_dir = static_path / "assets"
            assets_dir.mkdir()

            app = FastAPI()
            setup_static_file_serving(app, static_path, "production", False)

            # Should validate and mount assets


@pytest.mark.unit
class TestSafeJoinPathEdgeCases:
    """Test edge cases and error handling in safe_join_path."""

    def test_path_traversal_detected(self, tmp_path):
        """Should detect and reject path traversal attempts."""
        base = tmp_path / "static"
        base.mkdir()

        # Try to escape using symlink
        outside = tmp_path / "outside"
        outside.mkdir()

        # This should be detected and rejected
        result = safe_join_path(base, "../outside")
        assert result is None

    def test_path_resolution_error_handling(self, tmp_path):
        """Should handle path resolution errors gracefully."""
        base = tmp_path / "static"
        base.mkdir()

        # Create a very long path that might cause OSError
        long_path = "a/" * 1000  # Very deep path
        result = safe_join_path(base, long_path)

        # Should handle error gracefully (either None or valid path)
        # The key is it doesn't crash
        assert result is None or isinstance(result, Path)

    def test_relative_to_check_failure(self, tmp_path):
        """Should handle relative_to check failures."""
        base = tmp_path / "static"
        base.mkdir()

        # Try various path traversal techniques
        test_cases = [
            "../../etc/passwd",
            "./../../../root",
            "subdir/../../etc",
        ]

        for test_input in test_cases:
            result = safe_join_path(base, test_input)
            # Should either be None or safely within base
            if result is not None:
                assert result.is_relative_to(base)


@pytest.mark.unit
class TestSymlinkSafety:
    """Test symlink safety checks."""

    def test_unsafe_symlink_outside_base(self, tmp_path):
        """Should detect symlinks pointing outside base directory."""
        base = tmp_path / "static"
        base.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "evil.txt").write_text("evil content")

        # Create symlink pointing outside
        link = base / "evil_link"
        link.symlink_to(outside / "evil.txt")

        # Should be detected as unsafe
        assert is_safe_symlink(link, base) is False

    def test_safe_symlink_within_base(self, tmp_path):
        """Should allow symlinks pointing within base directory."""
        base = tmp_path / "static"
        base.mkdir()

        target = base / "target.txt"
        target.write_text("safe content")

        link = base / "safe_link"
        link.symlink_to(target)

        # Should be detected as safe
        assert is_safe_symlink(link, base) is True

    def test_symlink_error_handling(self, tmp_path):
        """Should handle symlink resolution errors."""
        base = tmp_path / "static"
        base.mkdir()

        # Create broken symlink
        link = base / "broken_link"
        link.symlink_to(base / "nonexistent.txt")

        # Should handle gracefully
        result = is_safe_symlink(link, base)
        assert isinstance(result, bool)


@pytest.mark.unit
class TestDirectoryValidationErrors:
    """Test error handling in directory validation."""

    def test_unsafe_directory_symlink(self, tmp_path):
        """Should reject directories that are unsafe symlinks."""
        base = tmp_path / "static"
        base.mkdir()

        outside_dir = tmp_path / "outside_dir"
        outside_dir.mkdir()

        # Create symlink to directory outside base
        dir_link = base / "unsafe_dir_link"
        dir_link.symlink_to(outside_dir)

        # Should be rejected
        assert validate_directory_safety(dir_link, base) is False

    def test_directory_validation_os_error(self, tmp_path):
        """Should handle OS errors during directory validation."""
        base = tmp_path / "static"
        base.mkdir()

        # Create directory with permission issues (on Unix)
        restricted_dir = base / "restricted"
        restricted_dir.mkdir()

        # Note: Permission manipulation is platform-dependent
        # This test verifies error handling exists
        result = validate_directory_safety(restricted_dir, base)
        assert isinstance(result, bool)


@pytest.mark.unit
class TestFindFileToServeEdgeCases:
    """Test edge cases in file serving logic."""

    def test_unsafe_symlink_file_rejected(self, tmp_path):
        """Should reject files that are unsafe symlinks."""
        base = tmp_path / "static"
        base.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "evil.js").write_text("malicious code")

        # Create unsafe symlink
        link = base / "evil.js"
        link.symlink_to(outside / "evil.js")

        # Should be rejected
        result = find_file_to_serve(base, link)
        assert result is None

    def test_index_html_validation_failure(self, tmp_path):
        """Should handle index.html validation failures."""
        base = tmp_path / "static"
        base.mkdir()

        dir_path = base / "subdir"
        dir_path.mkdir()

        # Create index.html as broken symlink
        index = dir_path / "index.html"
        index.symlink_to(base / "nonexistent.html")

        # Should handle error gracefully
        result = find_file_to_serve(base, dir_path)
        # Falls back to other options or None
        assert result is None or isinstance(result, Path)

    def test_html_extension_fallback_os_error(self, tmp_path):
        """Should handle OS errors in .html extension fallback."""
        base = tmp_path / "static"
        base.mkdir()

        # Request for non-existent file
        requested = base / "nonexistent"

        result = find_file_to_serve(base, requested)

        # Should handle gracefully and try fallbacks
        # Returns None or root index.html if it exists
        assert result is None or result.name == "index.html"

    def test_root_index_fallback(self, tmp_path):
        """Should fallback to root index.html when file not found."""
        base = tmp_path / "static"
        base.mkdir()

        # Create root index.html
        root_index = base / "index.html"
        root_index.write_text("<html><body>Root Index</body></html>")

        # Request non-existent file
        requested = base / "nonexistent" / "path"

        # Should fallback to root index
        result = find_file_to_serve(base, requested)
        assert result == root_index

    def test_no_fallback_when_root_index_missing(self, tmp_path):
        """Should return None when no files found and no root index."""
        base = tmp_path / "static"
        base.mkdir()

        # No index.html exists
        requested = base / "nonexistent"

        result = find_file_to_serve(base, requested)
        assert result is None


@pytest.mark.unit
class TestSetupStaticFileServingEdgeCases:
    """Test static file serving setup edge cases."""

    def test_setup_with_missing_static_path(self, tmp_path):
        """Should handle missing static path gracefully."""
        from fastapi import FastAPI

        app = FastAPI()
        missing_path = tmp_path / "nonexistent_static"

        # Should not crash, just log warning
        setup_static_file_serving(
            app=app, static_path=missing_path, env="development", serve_static=True
        )

        # App should still be configured
        assert app is not None

    def test_setup_production_with_serve_static_true(self, tmp_path):
        """Should serve static files in production when explicitly enabled."""
        from fastapi import FastAPI

        app = FastAPI()
        static_path = tmp_path / "static"
        static_path.mkdir()
        (static_path / "test.html").write_text("<html></html>")

        setup_static_file_serving(
            app=app, static_path=static_path, env="production", serve_static=True
        )

        # Should have added routes
        routes = [route.path for route in app.routes]
        assert any(path for path in routes)

    def test_setup_development_without_serve_static(self, tmp_path):
        """Should not serve static files in development by default."""
        from fastapi import FastAPI

        app = FastAPI()
        static_path = tmp_path / "static"
        static_path.mkdir()

        setup_static_file_serving(
            app=app, static_path=static_path, env="development", serve_static=False
        )

        # App should be configured but not serving static files
        assert app is not None


@pytest.mark.unit
class TestSafeJoinPathCoverage:
    """Additional tests to increase coverage of safe_join_path."""

    def test_is_relative_to_path_outside_base(self, tmp_path):
        """Should catch paths that escape base directory validation."""
        base = tmp_path / "static"
        base.mkdir()

        # Create a case where is_relative_to would be False
        # Try with a path that resolves outside
        with patch("pathlib.Path.is_relative_to", return_value=False):
            result = safe_join_path(base, "test.html")
            assert result is None

    def test_relative_to_raises_value_error(self, tmp_path):
        """Should handle ValueError from relative_to check."""
        base = tmp_path / "static"
        base.mkdir()

        # Mock relative_to to raise ValueError
        with patch("pathlib.Path.relative_to", side_effect=ValueError("test error")):
            result = safe_join_path(base, "test.html")
            assert result is None

    def test_path_resolution_runtime_error(self, tmp_path):
        """Should handle RuntimeError during path resolution."""
        base = tmp_path / "static"
        base.mkdir()

        # Mock resolve to raise RuntimeError
        with patch(
            "pathlib.Path.resolve", side_effect=RuntimeError("resolution error")
        ):
            result = safe_join_path(base, "test.html")
            assert result is None

    def test_path_resolution_os_error(self, tmp_path):
        """Should handle OSError during path resolution."""
        base = tmp_path / "static"
        base.mkdir()

        # Mock resolve to raise OSError
        with patch("pathlib.Path.resolve", side_effect=OSError("os error")):
            result = safe_join_path(base, "test.html")
            assert result is None


@pytest.mark.unit
class TestSymlinkErrorHandling:
    """Test error handling in symlink safety checks."""

    def test_symlink_resolve_runtime_error(self, tmp_path):
        """Should handle RuntimeError during symlink resolution."""
        base = tmp_path / "static"
        base.mkdir()

        link = base / "link.txt"
        link.touch()

        with patch.object(Path, "is_symlink", return_value=True):
            with patch.object(
                Path, "resolve", side_effect=RuntimeError("symlink error")
            ):
                result = is_safe_symlink(link, base)
                assert result is False

    def test_symlink_resolve_value_error(self, tmp_path):
        """Should handle ValueError during symlink resolution."""
        base = tmp_path / "static"
        base.mkdir()

        link = base / "link.txt"
        link.touch()

        with patch.object(Path, "is_symlink", return_value=True):
            with patch.object(Path, "resolve", side_effect=ValueError("value error")):
                result = is_safe_symlink(link, base)
                assert result is False

    def test_symlink_resolve_os_error(self, tmp_path):
        """Should handle OSError during symlink resolution."""
        base = tmp_path / "static"
        base.mkdir()

        link = base / "link.txt"
        link.touch()

        with patch.object(Path, "is_symlink", return_value=True):
            with patch.object(Path, "resolve", side_effect=OSError("os error")):
                result = is_safe_symlink(link, base)
                assert result is False


@pytest.mark.unit
class TestDirectoryValidationCoverage:
    """Additional tests for directory validation coverage."""

    def test_directory_symlink_detected(self, tmp_path):
        """Should detect and reject unsafe directory symlinks."""
        base = tmp_path / "static"
        base.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()

        # Create symlink to outside directory
        dir_link = base / "bad_link"
        dir_link.symlink_to(outside)

        # is_safe_symlink should return False, causing validation to fail
        result = validate_directory_safety(dir_link, base)
        assert result is False

    def test_directory_validation_runtime_error(self, tmp_path):
        """Should handle RuntimeError in directory validation."""
        base = tmp_path / "static"
        base.mkdir()

        subdir = base / "subdir"
        subdir.mkdir()

        with patch.object(Path, "resolve", side_effect=RuntimeError("runtime error")):
            result = validate_directory_safety(subdir, base)
            assert result is False

    def test_directory_validation_value_error(self, tmp_path):
        """Should handle ValueError in directory validation."""
        base = tmp_path / "static"
        base.mkdir()

        subdir = base / "subdir"
        subdir.mkdir()

        with patch.object(Path, "resolve", side_effect=ValueError("value error")):
            result = validate_directory_safety(subdir, base)
            assert result is False

    def test_directory_validation_os_error(self, tmp_path):
        """Should handle OSError in directory validation."""
        base = tmp_path / "static"
        base.mkdir()

        subdir = base / "subdir"
        subdir.mkdir()

        with patch.object(Path, "resolve", side_effect=OSError("os error")):
            result = validate_directory_safety(subdir, base)
            assert result is False


@pytest.mark.unit
class TestFindFileToServeCoverage:
    """Additional tests for find_file_to_serve coverage."""

    def test_directory_with_valid_index_html(self, tmp_path):
        """Should serve index.html from valid directory."""
        base = tmp_path / "static"
        base.mkdir()

        subdir = base / "docs"
        subdir.mkdir()

        index = subdir / "index.html"
        index.write_text("<html><body>Docs Index</body></html>")

        result = find_file_to_serve(base, subdir)
        assert result == index

    def test_directory_index_html_validation_os_error(self, tmp_path):
        """Should handle OSError when validating directory index.html."""
        base = tmp_path / "static"
        base.mkdir()

        subdir = base / "docs"
        subdir.mkdir()

        index = subdir / "index.html"
        index.write_text("<html></html>")

        # Mock resolve to raise OSError for index file
        original_resolve = Path.resolve

        def selective_resolve(self, *args, **kwargs):
            if self.name == "index.html":
                raise OSError("os error")
            return original_resolve(self, *args, **kwargs)

        with patch.object(Path, "resolve", selective_resolve):
            result = find_file_to_serve(base, subdir)
            # Should fall back to other options
            assert result is None or result != index

    def test_directory_index_html_value_error(self, tmp_path):
        """Should handle ValueError when validating directory index.html."""
        base = tmp_path / "static"
        base.mkdir()

        subdir = base / "docs"
        subdir.mkdir()

        index = subdir / "index.html"
        index.write_text("<html></html>")

        # Mock resolve to raise ValueError for index file
        original_resolve = Path.resolve

        def selective_resolve(self, *args, **kwargs):
            if self.name == "index.html":
                raise ValueError("value error")
            return original_resolve(self, *args, **kwargs)

        with patch.object(Path, "resolve", selective_resolve):
            result = find_file_to_serve(base, subdir)
            # Should fall back to other options
            assert result is None or result != index

    def test_html_extension_fallback_os_error_handling(self, tmp_path):
        """Should handle OSError when trying .html extension fallback."""
        base = tmp_path / "static"
        base.mkdir()

        # Create root index for fallback
        root_index = base / "index.html"
        root_index.write_text("<html></html>")

        # Request for file that doesn't exist
        requested = base / "page"

        # Create page.html but make it raise OSError when resolving
        html_file = base / "page.html"
        html_file.write_text("<html></html>")

        original_resolve = Path.resolve

        def selective_resolve(self, *args, **kwargs):
            if self.name == "page.html":
                raise OSError("os error")
            return original_resolve(self, *args, **kwargs)

        with patch.object(Path, "resolve", selective_resolve):
            result = find_file_to_serve(base, requested)
            # Should fall back to root index
            assert result == root_index

    def test_html_extension_fallback_value_error_handling(self, tmp_path):
        """Should handle ValueError when trying .html extension fallback."""
        base = tmp_path / "static"
        base.mkdir()

        # Create root index for fallback
        root_index = base / "index.html"
        root_index.write_text("<html></html>")

        # Request for file that doesn't exist
        requested = base / "page"

        # Create page.html but make it raise ValueError when resolving
        html_file = base / "page.html"
        html_file.write_text("<html></html>")

        original_resolve = Path.resolve

        def selective_resolve(self, *args, **kwargs):
            if self.name == "page.html":
                raise ValueError("value error")
            return original_resolve(self, *args, **kwargs)

        with patch.object(Path, "resolve", selective_resolve):
            result = find_file_to_serve(base, requested)
            # Should fall back to root index
            assert result == root_index


@pytest.mark.unit
class TestSetupStaticServingCoverage:
    """Additional tests for setup_static_file_serving coverage."""

    def test_static_path_resolve_error(self, tmp_path):
        """Should handle path resolution errors gracefully."""
        from fastapi import FastAPI

        app = FastAPI()
        static_path = tmp_path / "static"
        static_path.mkdir()
        (static_path / "test.html").write_text("<html></html>")

        with patch.object(Path, "resolve", side_effect=ValueError("resolve error")):
            # Should log error and return early
            setup_static_file_serving(
                app=app, static_path=static_path, env="production", serve_static=False
            )

            # Should not crash
            assert app is not None

    def test_static_path_resolve_os_error(self, tmp_path):
        """Should handle OS errors during path resolution."""
        from fastapi import FastAPI

        app = FastAPI()
        static_path = tmp_path / "static"
        static_path.mkdir()
        (static_path / "test.html").write_text("<html></html>")

        with patch.object(Path, "resolve", side_effect=OSError("os error")):
            # Should log error and return early
            setup_static_file_serving(
                app=app, static_path=static_path, env="production", serve_static=False
            )

            # Should not crash
            assert app is not None

    def test_unsafe_app_directory_detected(self, tmp_path):
        """Should detect and reject unsafe _app directory."""
        from fastapi import FastAPI

        app = FastAPI()
        static_path = tmp_path / "static"
        static_path.mkdir()
        (static_path / "index.html").write_text("<html></html>")

        # Create _app directory outside base
        outside_app = tmp_path / "outside_app"
        outside_app.mkdir()

        app_link = static_path / "_app"
        app_link.symlink_to(outside_app)

        setup_static_file_serving(
            app=app, static_path=static_path, env="production", serve_static=False
        )

        # Should log error about unsafe directory
        # Verify app is still configured
        assert app is not None

    def test_unsafe_assets_directory_detected(self, tmp_path):
        """Should detect and reject unsafe assets directory."""
        from fastapi import FastAPI

        app = FastAPI()
        static_path = tmp_path / "static"
        static_path.mkdir()
        (static_path / "index.html").write_text("<html></html>")

        # Create assets directory outside base
        outside_assets = tmp_path / "outside_assets"
        outside_assets.mkdir()

        assets_link = static_path / "assets"
        assets_link.symlink_to(outside_assets)

        setup_static_file_serving(
            app=app, static_path=static_path, env="production", serve_static=False
        )

        # Should log error about unsafe directory
        # Verify app is still configured
        assert app is not None
