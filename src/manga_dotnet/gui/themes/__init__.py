"""GUI themes — color palette + theme manager.

Provides:
- ``Colors`` — application color palette constants
- ``get_theme_qss(name)`` — returns QSS for a theme ("dark", "light", "midnight")
- ``DARK_THEME_QSS`` — backward-compatible dark theme QSS constant
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Color palette (from DESIGN.md)
# ---------------------------------------------------------------------------

class Colors:
    """Application color palette (dark theme defaults)."""

    PRIMARY = "#6C5CE7"      # Electric Purple
    SECONDARY = "#00CEC9"    # Turquoise
    ACCENT = "#FD79A8"       # Hot Pink
    SUCCESS = "#00B894"      # Mint Green
    WARNING = "#FDCB6E"      # Sunshine
    ERROR = "#E17055"        # Coral
    BG_DARK = "#0D1117"      # GitHub Dark
    BG_CARD = "#161B22"      # Card Surface
    BG_ELEVATED = "#1C2128"  # Elevated surface (hover, active)
    BORDER = "#21262D"       # Border color
    TEXT = "#E6EDF3"         # Light Gray (primary text)
    MUTED = "#7D8590"        # Dim Gray (secondary text)


# ---------------------------------------------------------------------------
# Theme registry
# ---------------------------------------------------------------------------

_THEME_CACHE: dict[str, str] = {}


def get_theme_qss(name: str = "dark") -> str:
    """Return the QSS stylesheet for the given theme name.

    Supported themes: "dark" (default), "light", "midnight".
    """
    name = name.lower().strip()
    if name in _THEME_CACHE:
        return _THEME_CACHE[name]

    if name == "light":
        from .light import get_light_qss
        qss = get_light_qss()
    elif name == "midnight":
        from .midnight import get_midnight_qss
        qss = get_midnight_qss()
    else:
        # Default: dark
        from .dark import get_dark_qss
        qss = get_dark_qss()

    _THEME_CACHE[name] = qss
    return qss


def clear_theme_cache() -> None:
    """Clear the theme cache so themes are reloaded next time."""
    _THEME_CACHE.clear()


# Backward-compatible constant — used by MainWindow, app.py, etc.
DARK_THEME_QSS = get_theme_qss("dark")
