"""Text utilities — title formatting, slugify, chapter range compression."""

from __future__ import annotations

import re
import unicodedata


def slugify(text: str) -> str:
    """Convert text to a URL/file-friendly slug.

    Examples:
        >>> slugify("The Devil Butler!")
        'the-devil-butler'
        >>> slugify("Solo Leveling  (나 혼자만 레벨업)")
        'solo-leveling'
    """
    # Normalize unicode and strip accents
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Lowercase
    text = text.lower()
    # Replace non-alphanumeric with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Collapse hyphens and strip
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"


def sanitize_title(title: str) -> str:
    """Clean a manga/chapter title for display or filename use."""
    # Remove excessive whitespace
    title = re.sub(r"\s+", " ", title).strip()
    # Remove control characters
    title = "".join(c for c in title if unicodedata.category(c) != "Cc")
    return title


def format_chapter_range(chapters: list[float]) -> str:
    """Compress a sorted list of chapter numbers into a range string.

    Examples:
        >>> format_chapter_range([1, 2, 3, 5, 7, 8])
        '1-3, 5, 7-8'
        >>> format_chapter_range([10.5, 10.6, 11])
        '10.5-10.6, 11'
    """
    if not chapters:
        return ""

    chapters = sorted(set(chapters))
    ranges: list[str] = []
    start = chapters[0]
    end = chapters[0]

    for ch in chapters[1:]:
        if ch == end + 1 or (ch == end and float(ch) == float(end)):
            end = ch
        else:
            ranges.append(_fmt_range(start, end))
            start = ch
            end = ch

    ranges.append(_fmt_range(start, end))
    return ", ".join(ranges)


def _fmt_range(start: float, end: float) -> str:
    """Format a single range."""
    if start == end:
        return _fmt_ch(start)
    return f"{_fmt_ch(start)}-{_fmt_ch(end)}"


def _fmt_ch(n: float) -> str:
    """Format a chapter number — drop trailing .0."""
    if n == int(n):
        return str(int(n))
    return str(n)


def parse_chapter_range(range_str: str) -> list[float]:
    """Parse a chapter range string into a list of chapter numbers.

    Examples:
        >>> parse_chapter_range("1-5")
        [1.0, 2.0, 3.0, 4.0, 5.0]
        >>> parse_chapter_range("1-3, 5, 7-8")
        [1.0, 2.0, 3.0, 5.0, 7.0, 8.0]
    """
    chapters: list[float] = []
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            bounds = part.split("-", 1)
            start = float(bounds[0].strip())
            end = float(bounds[1].strip())
            step = 1.0
            # Handle decimal ranges
            if start != int(start) or end != int(end):
                step = 0.1
            ch = start
            while ch <= end + 0.001:  # float tolerance
                chapters.append(round(ch, 1))
                ch += step
        elif part:
            chapters.append(float(part))
    return sorted(chapters)
