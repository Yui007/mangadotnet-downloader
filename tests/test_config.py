"""Tests for Config system."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from manga_dotnet.core.config import (
    CacheConfig,
    CLIConfig,
    Config,
    DownloadConfig,
    GUIConfig,
    NetworkConfig,
    QualityConfig,
)


class TestConfigDefaults:
    """Test default config values."""

    def test_defaults(self):
        config = Config()
        assert config.output_dir == Path.cwd() / "manga"
        assert config.default_format == "cbz"
        assert config.default_language == "en"
        assert config.check_updates is True

    def test_download_defaults(self):
        dl = DownloadConfig()
        assert dl.max_concurrent_chapters == 4
        assert dl.max_concurrent_images == 8
        assert dl.max_retries == 3
        assert dl.retry_delay == 2.0
        assert dl.timeout == 30

    def test_quality_defaults(self):
        q = QualityConfig()
        assert q.default == "original"
        assert q.convert_webp is True
        assert q.jpeg_quality == 95
        assert q.delete_images_after_export is False

    def test_gui_defaults(self):
        g = GUIConfig()
        assert g.theme == "dark"
        assert g.window_width == 1200
        assert g.window_height == 800


class TestConfigGetSet:
    """Test dotted key get/set."""

    def test_get_simple(self):
        config = Config()
        assert config.get("default_format") == "cbz"

    def test_get_nested(self):
        config = Config()
        assert config.get("download.max_retries") == 3

    def test_get_missing(self):
        config = Config()
        assert config.get("nonexistent", "fallback") == "fallback"

    def test_set_simple(self):
        config = Config()
        config.set("default_format", "pdf")
        assert config.default_format == "pdf"

    def test_set_nested(self):
        config = Config()
        config.set("download.max_retries", 5)
        assert config.download.max_retries == 5

    def test_set_invalid_key(self):
        config = Config()
        with pytest.raises(KeyError):
            config.set("nonexistent.key", "value")


class TestConfigJSON:
    """Test JSON load/save."""

    def test_save_and_load(self, tmp_path):
        config = Config()
        config.output_dir = tmp_path / "manga"
        config.default_format = "pdf"
        config.download.max_retries = 7

        settings_file = tmp_path / "settings.json"
        config.save(settings_file)

        assert settings_file.exists()
        loaded = Config.load(settings_file)
        assert loaded.default_format == "pdf"
        assert loaded.download.max_retries == 7

    def test_to_dict(self):
        config = Config()
        d = config.to_dict()
        assert "default_format" in d
        assert "download" in d
        assert "gui" in d
        assert "_settings_path" not in d

    def test_load_nonexistent_uses_defaults(self):
        config = Config.load(Path("/nonexistent/settings.json"))
        assert config.default_format == "cbz"

    def test_partial_json(self, tmp_path):
        """Loading partial JSON should merge with defaults."""
        partial = {"default_format": "pdf"}
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps(partial))

        config = Config.load(settings_file)
        assert config.default_format == "pdf"
        # Defaults preserved
        assert config.download.max_retries == 3


class TestConfigEnvOverrides:
    """Test environment variable overrides."""

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("MANGADOTNET_DEFAULT_FORMAT", "pdf")
        config = Config._apply_env_overrides(Config())
        assert config.default_format == "pdf"

    def test_env_bool_override(self, monkeypatch):
        monkeypatch.setenv("MANGADOTNET_DELETE_IMAGES", "true")
        config = Config._apply_env_overrides(Config())
        assert config.quality.delete_images_after_export is True

    def test_env_int_override(self, monkeypatch):
        monkeypatch.setenv("MANGADOTNET_MAX_RETRIES", "10")
        config = Config._apply_env_overrides(Config())
        assert config.download.max_retries == 10
