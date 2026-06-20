"""Config management — JSON settings file in project root.

Settings loading order (last wins):
1. Built-in defaults (dataclass defaults)
2. ``settings.json`` in project root
3. Environment variables (``MANGADOTNET_*``)
4. CLI flags (applied at call site)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields, asdict
from pathlib import Path
from typing import Any


SETTINGS_FILE = "settings.json"


# ---------------------------------------------------------------------------
# Sub-configs
# ---------------------------------------------------------------------------


@dataclass
class DownloadConfig:
    """Download concurrency and retry settings."""

    max_concurrent_chapters: int = 4
    max_concurrent_images: int = 8
    max_concurrent_downloads: int = 3
    max_retries: int = 3
    retry_delay: float = 2.0
    timeout: int = 30
    chunk_size: int = 8192


@dataclass
class QualityConfig:
    """Image quality and post-export settings."""

    default: str = "original"  # low | medium | high | original
    convert_webp: bool = True
    jpeg_quality: int = 95
    delete_images_after_export: bool = False


@dataclass
class CacheConfig:
    """API response cache settings."""

    enabled: bool = True
    max_size_mb: int = 500
    ttl_hours: int = 24


@dataclass
class NetworkConfig:
    """HTTP and network settings."""

    user_agent: str = "MangaDotNetDownloader/1.0"
    proxy: str | None = None  # HTTP/SOCKS5 proxy
    dns_over_https: bool = True
    rate_limit_rps: int = 10


@dataclass
class GUIConfig:
    """GUI window and appearance settings."""

    theme: str = "dark"
    window_width: int = 1200
    window_height: int = 800
    sidebar_collapsed: bool = False
    show_thumbnails: bool = True
    thumbnail_size: int = 150


@dataclass
class CLIConfig:
    """CLI display settings."""

    color: bool = True
    progress_style: str = "bar"  # bar | spinner | none
    splash_screen: bool = True


# ---------------------------------------------------------------------------
# Main Config
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Top-level application configuration."""

    # General
    output_dir: Path = field(default_factory=lambda: Path.cwd() / "manga")
    default_format: str = "cbz"
    default_language: str = "en"
    default_scanlator_group: str | None = None
    prefer_user_uploaded: bool = True
    check_updates: bool = True

    # Sub-configs
    download: DownloadConfig = field(default_factory=DownloadConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    gui: GUIConfig = field(default_factory=GUIConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)

    # Internal: path from which this config was loaded
    _settings_path: Path | None = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, settings_path: Path | None = None) -> Config:
        """Load settings with priority: defaults → JSON file → env."""
        config = cls()

        # 1. Find settings.json
        if settings_path is None:
            # Look in project root (cwd) and next to this file's package
            candidates = [
                Path.cwd() / SETTINGS_FILE,
                Path(__file__).resolve().parent.parent.parent.parent / SETTINGS_FILE,
            ]
            for candidate in candidates:
                if candidate.exists():
                    settings_path = candidate
                    break

        # 2. Load from JSON
        if settings_path and settings_path.exists():
            config = cls._load_json(config, settings_path)
            config._settings_path = settings_path

        # 3. Apply environment variable overrides
        config = cls._apply_env_overrides(config)

        return config

    @classmethod
    def _load_json(cls, config: Config, path: Path) -> Config:
        """Merge JSON settings into the config dataclass."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # Merge top-level keys
        config = cls._merge_dict(config, data)

        # Merge sub-configs
        sub_config_map = {
            "download": DownloadConfig,
            "quality": QualityConfig,
            "cache": CacheConfig,
            "network": NetworkConfig,
            "gui": GUIConfig,
            "cli": CLIConfig,
        }
        for key, sub_cls in sub_config_map.items():
            if key in data and isinstance(data[key], dict):
                sub_config = getattr(config, key)
                setattr(config, key, cls._merge_dataclass(sub_config, data[key]))

        return config

    @staticmethod
    def _merge_dataclass(obj: Any, data: dict) -> Any:
        """Merge a dict of values into a dataclass instance."""
        for k, v in data.items():
            if hasattr(obj, k):
                current = getattr(obj, k)
                # Handle Path conversion
                if isinstance(current, Path):
                    v = Path(v)
                setattr(obj, k, v)
        return obj

    @staticmethod
    def _merge_dict(config: Config, data: dict) -> Config:
        """Merge top-level dict values into config."""
        simple_fields = {
            f.name for f in fields(config)
            if f.name not in ("download", "quality", "cache", "network", "gui", "cli", "_settings_path")
        }
        for k, v in data.items():
            if k in simple_fields:
                current = getattr(config, k)
                if isinstance(current, Path):
                    v = Path(v)
                setattr(config, k, v)
        return config

    # ------------------------------------------------------------------
    # Environment overrides
    # ------------------------------------------------------------------

    @classmethod
    def _apply_env_overrides(cls, config: Config) -> Config:
        """Apply MANGADOTNET_* environment variable overrides."""
        env_map: dict[str, tuple[str, type]] = {
            "MANGADOTNET_OUTPUT_DIR": ("output_dir", str),
            "MANGADOTNET_DEFAULT_FORMAT": ("default_format", str),
            "MANGADOTNET_DEFAULT_LANGUAGE": ("default_language", str),
            "MANGADOTNET_MAX_CONCURRENT_CHAPTERS": ("download.max_concurrent_chapters", int),
            "MANGADOTNET_MAX_CONCURRENT_IMAGES": ("download.max_concurrent_images", int),
            "MANGADOTNET_MAX_CONCURRENT_DOWNLOADS": ("download.max_concurrent_downloads", int),
            "MANGADOTNET_MAX_RETRIES": ("download.max_retries", int),
            "MANGADOTNET_TIMEOUT": ("download.timeout", int),
            "MANGADOTNET_PROXY": ("network.proxy", str),
            "MANGADOTNET_RATE_LIMIT": ("network.rate_limit_rps", int),
            "MANGADOTNET_GUI_THEME": ("gui.theme", str),
            "MANGADOTNET_DELETE_IMAGES": ("quality.delete_images_after_export", bool),
        }

        for env_var, (key_path, target_type) in env_map.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    if target_type is bool:
                        converted = value.lower() in ("true", "1", "yes")
                    elif target_type is int:
                        converted = int(value)
                    else:
                        converted = value
                    config.set(key_path, converted)
                except (ValueError, KeyError):
                    pass

        return config

    # ------------------------------------------------------------------
    # Get / Set
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dotted key path (e.g. ``'download.max_retries'``)."""
        parts = key.split(".")
        obj: Any = self
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return default
        return obj

    def set(self, key: str, value: Any) -> None:
        """Set a config value by dotted key path."""
        parts = key.split(".")
        obj: Any = self
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                raise KeyError(f"Invalid config path: {key}")
        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
        else:
            raise KeyError(f"Invalid config key: {key}")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert config to a plain dict (for JSON serialization)."""
        d = asdict(self)
        # Remove internal fields
        d.pop("_settings_path", None)
        # Convert Path objects to strings
        for k, v in d.items():
            if isinstance(v, Path):
                d[k] = str(v)
        return d

    def save(self, path: Path | None = None) -> Path:
        """Save current settings to a JSON file. Returns the path written."""
        if path is None:
            path = self._settings_path or (Path.cwd() / SETTINGS_FILE)

        data = self.to_dict()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Human-readable summary of the active configuration."""
        lines = [
            f"Output dir:    {self.output_dir}",
            f"Format:        {self.default_format}",
            f"Language:      {self.default_language}",
            f"Max chapters:  {self.download.max_concurrent_chapters}",
            f"Max images:    {self.download.max_concurrent_images}",
            f"Max downloads: {self.download.max_concurrent_downloads}",
            f"Max retries:   {self.download.max_retries}",
            f"Timeout:       {self.download.timeout}s",
            f"Delete images: {self.quality.delete_images_after_export}",
            f"Cache:         {'enabled' if self.cache.enabled else 'disabled'} ({self.cache.max_size_mb}MB, {self.cache.ttl_hours}h TTL)",
            f"Proxy:         {self.network.proxy or 'none'}",
            f"GUI theme:     {self.gui.theme}",
        ]
        return "\n".join(lines)
