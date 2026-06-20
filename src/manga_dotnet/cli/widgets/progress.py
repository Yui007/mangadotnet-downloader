"""Custom progress bar widgets for download tracking."""

from __future__ import annotations

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


def create_download_progress() -> Progress:
    """Create a Rich progress bar for downloads."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        TimeRemainingColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
    )


class DownloadProgressTracker:
    """Rich-powered progress tracking for CLI."""

    def __init__(self) -> None:
        self.progress = create_download_progress()
        self._tasks: dict[int, int] = {}  # chapter_id -> task_id

    def __enter__(self) -> DownloadProgressTracker:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    def start(self) -> None:
        self.progress.start()

    def stop(self) -> None:
        self.progress.stop()

    def add_chapter(
        self, chapter_id: int, chapter_number: float, total_pages: int
    ) -> None:
        task_id = self.progress.add_task(
            f"Ch.{chapter_number}",
            total=total_pages,
        )
        self._tasks[chapter_id] = task_id

    def update_page(self, chapter_id: int, current_page: int) -> None:
        if chapter_id in self._tasks:
            self.progress.update(self._tasks[chapter_id], completed=current_page)

    def complete_chapter(self, chapter_id: int) -> None:
        if chapter_id in self._tasks:
            self.progress.update(self._tasks[chapter_id], completed=True)

    def fail_chapter(self, chapter_id: int, chapter_number: float = 0) -> None:
        if chapter_id in self._tasks:
            self.progress.update(
                self._tasks[chapter_id],
                description=f"[red]✗ Failed Ch.{chapter_number}",
            )
