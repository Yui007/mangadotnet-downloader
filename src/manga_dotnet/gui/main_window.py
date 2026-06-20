"""Main application window with left sidebar navigation.

Layout:
    ┌──────────┬───────────────────────────────────────────┐
    │ Sidebar  │                                           │
    │          │  Content Stack (swapped by sidebar tabs)  │
    │ 🔍 Search│                                           │
    │ ⬇️ Downl.│  (SearchPage has its own search bar)      │
    │ 📚 Libr. │                                           │
    │ 📋 Hist. │                                           │
    │ ⚙️ Sett. │                                           │
    │          ├───────────────────────────────────────────┤
    │    ◀     │  Download Panel (collapsible, bottom)     │
    └──────────┴───────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .pages import (
    DownloadsPage,
    HistoryPage,
    OpenUrlPage,
    SearchPage,
    SettingsPage,
)
from .sidebar import SidebarNav
from .themes import DARK_THEME_QSS, Colors

if TYPE_CHECKING:
    from manga_dotnet.api.client import MangaDotNetClient
    from manga_dotnet.core.config import Config

logger = logging.getLogger(__name__)

class _ClientInitWorker(QThread):
    """Initialize the API client (solve CF challenge) in a background thread."""

    ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config

    def run(self) -> None:
        try:
            from manga_dotnet.api.client import MangaDotNetClient

            client = MangaDotNetClient(self._config)
            client.initialize()
            self.ready.emit(client)
        except Exception as e:
            logger.error("Client initialization failed: %s", e)
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Background download worker
# ---------------------------------------------------------------------------

class _DownloadWorker(QThread):
    """Download chapters in a background thread.

    Uses the existing ImageAPI + export modules to download and export.
    Respects config settings: concurrent_chapters, concurrent_images,
    max_retries, retry_delay, delete_images_after_export.
    """
    progress = pyqtSignal(int, str, str, str)  # percent, speed, elapsed, pages
    finished_ok = pyqtSignal(object)  # DownloadResult
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        client,
        chapter_ids: list[int],
        export_format: str = "cbz",
        delete_images: bool = False,
        manga_title: str = "",
        chapter_numbers: list[float] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._chapter_ids = chapter_ids
        self._export_format = export_format
        self._delete_images = delete_images
        self._manga_title = manga_title
        self._chapter_numbers = chapter_numbers or [0] * len(chapter_ids)

        # Thread controls
        import threading
        self._is_cancelled = False
        self._is_paused = False
        self._pause_cond = threading.Condition()
        self._lock = threading.Lock()
        
        # Stats counters
        self._downloaded_pages = 0
        self._total_expected_pages = 0
        self._downloaded_bytes = 0
        self._start_time = 0.0

    def cancel(self) -> None:
        with self._pause_cond:
            self._is_cancelled = True
            self._is_paused = False
            self._pause_cond.notify_all()

    def toggle_pause(self) -> bool:
        with self._pause_cond:
            self._is_paused = not self._is_paused
            if not self._is_paused:
                self._pause_cond.notify_all()
            return self._is_paused

    def run(self) -> None:
        try:
            import asyncio
            import time

            from manga_dotnet.api.images import ImageAPI
            from manga_dotnet.export.cleanup import get_exporter
            from manga_dotnet.core.config import Config

            self._start_time = time.time()
            total = len(self._chapter_ids)
            downloaded = 0
            failed = 0

            image_api = ImageAPI(self._client)
            exporter = get_exporter(self._export_format)
            config = Config.load()
            output_dir = config.output_dir

            # Read download settings from config
            max_retries = config.download.max_retries
            retry_delay = config.download.retry_delay
            concurrent_chapters = config.download.max_concurrent_chapters

            # 1. Fetch images lists for all chapters to determine total expected page count
            chapter_image_lists = {}
            for idx, ch_id in enumerate(self._chapter_ids):
                with self._pause_cond:
                    while self._is_paused and not self._is_cancelled:
                        self._pause_cond.wait()
                if self._is_cancelled:
                    return

                try:
                    chapter_images = image_api.get_images(ch_id)
                    if chapter_images and chapter_images.images:
                        chapter_image_lists[idx] = chapter_images
                        with self._lock:
                            self._total_expected_pages += len(chapter_images.images)
                except Exception as e:
                    logger.warning("Failed to get images for chapter %d: %s", ch_id, e)

            if self._total_expected_pages == 0:
                self.error_occurred.emit("No pages found to download.")
                return

            # Use thread pool for concurrent chapter downloads
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def download_one_chapter(idx: int, ch_id: int) -> tuple[int, bool, int]:
                """Download and export a single chapter. Returns (idx, success, page_count)."""
                ch_num = self._chapter_numbers[idx]
                try:
                    chapter_images = chapter_image_lists.get(idx)
                    if not chapter_images or not chapter_images.images:
                        return (idx, False, 0)

                    page_count = len(chapter_images.images)
                    page_data = []

                    for img in chapter_images.images:
                        # Handle pause / cancel
                        with self._pause_cond:
                            while self._is_paused and not self._is_cancelled:
                                self._pause_cond.wait()
                        if self._is_cancelled:
                            return (idx, False, 0)

                        # Download image with retry logic
                        data = None
                        last_error = None
                        for attempt in range(max_retries + 1):
                            if self._is_cancelled:
                                return (idx, False, 0)
                            try:
                                data = image_api.download_image(img.full_url)
                                if data:
                                    last_error = None
                                    break
                            except Exception as e:
                                last_error = e
                                if attempt < max_retries:
                                    time.sleep(retry_delay)

                        if self._is_cancelled:
                            return (idx, False, 0)

                        if last_error:
                            logger.warning(
                                "Failed to download page %s after %d retries: %s",
                                img.full_url, max_retries, last_error,
                            )
                            continue

                        if data:
                            page_data.append((img, data))

                            # Increment downloaded stats under lock and emit progress
                            with self._lock:
                                self._downloaded_pages += 1
                                self._downloaded_bytes += len(data)

                                elapsed_s = time.time() - self._start_time
                                if elapsed_s <= 0:
                                    elapsed_s = 0.1

                                speed_val = (self._downloaded_bytes / (1024 * 1024)) / elapsed_s
                                speed_str = f"{speed_val:.2f} MB/s"

                                elapsed_str = f"{int(elapsed_s // 60)}:{int(elapsed_s % 60):02d}"
                                pages_str = f"{self._downloaded_pages}/{self._total_expected_pages}"
                                pct = int(self._downloaded_pages / self._total_expected_pages * 100)

                                self.progress.emit(pct, speed_str, elapsed_str, pages_str)

                    if not page_data:
                        return (idx, False, 0)

                    if self._is_cancelled:
                        return (idx, False, 0)

                    # Export
                    raw_images = [data for _img, data in page_data]
                    safe_title = self._manga_title or f"manga_{ch_id}"
                    safe_title = "".join(
                        c for c in safe_title if c.isalnum() or c in " -_"
                    ).strip()
                    safe_title = safe_title.replace(" ", "_") or f"manga_{ch_id}"
                    chapter_folder = f"Chapter_{ch_num:g}"
                    chapter_dir = output_dir / safe_title / chapter_folder
                    chapter_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"Chapter_{ch_num:g}"
                    metadata = {
                        "chapter_id": ch_id,
                        "chapter_number": ch_num,
                        "manga_title": self._manga_title,
                    }
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(
                            exporter.export(
                                images=raw_images,
                                output_dir=chapter_dir,
                                filename=filename,
                                metadata=metadata,
                            )
                        )
                    finally:
                        loop.close()

                    # Save loose images if delete_images is False and format is an archive
                    if self._export_format not in ("images", "folder") and not self._delete_images:
                        from manga_dotnet.export.base import detect_extension
                        for p_idx, (_img_info, img_bytes) in enumerate(page_data):
                            ext = detect_extension(img_bytes)
                            img_path = chapter_dir / f"{p_idx + 1:04d}{ext}"
                            try:
                                img_path.write_bytes(img_bytes)
                            except Exception as e:
                                logger.warning("Failed to save loose page image: %s", e)

                    return (idx, True, page_count)

                except Exception as e:
                    logger.warning("Failed to download chapter %d: %s", ch_id, e)
                    return (idx, False, 0)

            # Execute chapter downloads (concurrent up to max_chapters)
            effective_concurrency = min(concurrent_chapters, total)
            with ThreadPoolExecutor(max_workers=effective_concurrency) as pool:
                futures = {
                    pool.submit(download_one_chapter, idx, ch_id): idx
                    for idx, ch_id in enumerate(self._chapter_ids)
                }
                for future in as_completed(futures):
                    idx, success, page_count = future.result()
                    if success:
                        downloaded += 1
                    else:
                        failed += 1

            if self._is_cancelled:
                return

            from manga_dotnet.core.models import DownloadResult
            result = DownloadResult(
                manga_id=0,
                manga_title="",
                chapters_downloaded=downloaded,
                chapters_failed=failed,
                total_pages=self._downloaded_pages,
                export_format=self._export_format,
            )
            self.finished_ok.emit(result)

        except Exception as e:
            logger.error("Download worker failed: %s", e)
            self.error_occurred.emit(str(e))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Main application window.

    Houses the left sidebar, a QStackedWidget for page content, and a
    collapsible download panel at the bottom.  The API client is initialized
    lazily in a background thread on first use (solving the Cloudflare
    challenge takes ~10 seconds).
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MangaDotNet Downloader")
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)

        self._client: MangaDotNetClient | None = None
        self._client_worker: _ClientInitWorker | None = None
        self._config: Config | None = None
        self._active_workers: dict[int, _DownloadWorker] = {}
        self._download_queue: list[dict] = []
        self._next_task_id: int = 1

        self._build_ui()
        self._build_menu_bar()
        self._build_status_bar()

        # Load config FIRST, then apply theme
        self._load_config()
        self._apply_theme()
        self._init_client()

        # Initialize history
        from manga_dotnet.core.history import LibraryManager
        self._library_manager = LibraryManager()
        try:
            for entry in self._library_manager.get_history():
                self.history_page.add_entry(
                    manga_title=entry.manga_title,
                    chapter_range=entry.chapter_range,
                    export_format=entry.export_format,
                    timestamp=entry.timestamp,
                    status=entry.status,
                    manga_id=entry.manga_id,
                    chapters_downloaded=entry.chapters_downloaded,
                    total_pages=entry.total_pages,
                    output_path=entry.output_path,
                    errors=entry.errors,
                    client=self._client,
                )
        except Exception as e:
            logger.warning("Failed to populate history page: %s", e)

        # Apply persisted GUI settings on startup
        if self._config:
            # Sidebar collapsed
            if self._config.gui.sidebar_collapsed:
                self.sidebar._collapse()
            # Default format in detail pages
            self.search_page.set_default_format(self._config.default_format)
            self.open_url_page.set_default_format(self._config.default_format)
            # Default language in detail pages
            self.search_page.set_default_language(self._config.default_language)
            self.open_url_page.set_default_language(self._config.default_language)
            # Default quality in detail pages
            self.search_page.set_default_quality(self._config.quality.default)
            self.open_url_page.set_default_quality(self._config.quality.default)
            # Delete images after export
            self.search_page.set_delete_images(self._config.quality.delete_images_after_export)
            self.open_url_page.set_delete_images(self._config.quality.delete_images_after_export)
            # Show thumbnails in search results
            self.search_page.set_show_thumbnails(self._config.gui.show_thumbnails)
            # Thumbnail size in search results
            self.search_page.set_thumbnail_size(self._config.gui.thumbnail_size)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar
        self.sidebar = SidebarNav()
        main_layout.addWidget(self.sidebar)

        # Right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Content stack
        self.content_stack = QStackedWidget()
        self._build_pages()
        right_layout.addWidget(self.content_stack, stretch=1)

        main_layout.addWidget(right_panel, stretch=1)

        # Connect sidebar → page switching
        self.sidebar.page_changed.connect(self.content_stack.setCurrentIndex)

        # Connect settings changes → re-apply theme
        self.settings_page.settings_changed.connect(self._on_settings_changed)

        # Connect downloads page signals to MainWindow slots
        self.downloads_page.cancel_requested.connect(self._cancel_download)
        self.downloads_page.pause_requested.connect(self._pause_download)

        # Connect history page signals
        self.history_page.delete_entry_requested.connect(self._delete_history_entry)

    def _build_pages(self) -> None:
        """Create and register all content pages in the stack."""
        self.open_url_page = OpenUrlPage()
        self.search_page = SearchPage()
        self.downloads_page = DownloadsPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(self._config)

        self.content_stack.addWidget(self.open_url_page)
        self.content_stack.addWidget(self.search_page)
        self.content_stack.addWidget(self.downloads_page)
        self.content_stack.addWidget(self.history_page)
        self.content_stack.addWidget(self.settings_page)

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load the application configuration."""
        from manga_dotnet.core.config import Config

        self._config = Config.load()
        # Update settings page with loaded config
        if hasattr(self, "settings_page"):
            self.settings_page.set_config(self._config)

    # ------------------------------------------------------------------
    # API client initialization
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        """Initialize the API client in a background thread."""
        if self._config is None:
            return
        self._client_worker = _ClientInitWorker(self._config, parent=self)
        self._client_worker.ready.connect(self._on_client_ready)
        self._client_worker.error.connect(self._on_client_error)
        self.statusBar().showMessage("☁️ Initializing API client (solving Cloudflare)…")
        self._client_worker.start()

    def _on_settings_changed(self, settings: dict) -> None:
        """Re-apply all settings when they change."""
        # Reload config from disk so self._config is up to date
        from manga_dotnet.core.config import Config
        self._config = Config.load()

        # Update settings page with fresh config reference
        if hasattr(self, "settings_page"):
            self.settings_page.set_config(self._config)

        # 1. Theme
        self._apply_theme()

        # 2. Sidebar collapse/expand
        if self._config and hasattr(self, "sidebar"):
            if self._config.gui.sidebar_collapsed:
                self.sidebar._collapse()
            else:
                self.sidebar._expand()

        # 3. Default format in detail pages
        if self._config:
            self.search_page.set_default_format(self._config.default_format)
            self.open_url_page.set_default_format(self._config.default_format)

        # 4. Default language in detail pages
        if self._config:
            self.search_page.set_default_language(self._config.default_language)
            self.open_url_page.set_default_language(self._config.default_language)

        # 5. Default quality in detail pages
        if self._config:
            self.search_page.set_default_quality(self._config.quality.default)
            self.open_url_page.set_default_quality(self._config.quality.default)

        # 6. Delete images after export
        if self._config:
            self.search_page.set_delete_images(self._config.quality.delete_images_after_export)
            self.open_url_page.set_delete_images(self._config.quality.delete_images_after_export)

        # 7. Show thumbnails in search results
        if self._config:
            self.search_page.set_show_thumbnails(self._config.gui.show_thumbnails)

        # 8. Thumbnail size in search results
        if self._config:
            self.search_page.set_thumbnail_size(self._config.gui.thumbnail_size)

        self.statusBar().showMessage("✅ Settings saved", 3000)

    def _on_client_ready(self, client: MangaDotNetClient) -> None:
        """Handle successful client initialization."""
        self._client = client
        self.open_url_page.set_client(client)
        self.search_page.set_client(client)
        self.statusBar().showMessage("✅ Ready", 5000)
        logger.info("API client initialized successfully")

        # Connect download_requested signals from both detail pages
        self.open_url_page._detail.download_requested.connect(
            self._on_download_requested
        )
        self.search_page.detail_page.download_requested.connect(
            self._on_download_requested
        )

    def _on_client_error(self, error: str) -> None:
        """Handle failed client initialization."""
        self.statusBar().showMessage(f"❌ Client init failed: {error}", 10000)
        logger.error("Client initialization failed: %s", error)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menubar: QMenuBar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("📥 &Import Batch…", self._import_batch)
        file_menu.addAction("⚙️ &Settings…", self._open_settings)
        file_menu.addSeparator()
        file_menu.addAction("❌ E&xit", self.close)

        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("🔗 &Open URL", lambda: self._switch_page(0))
        view_menu.addAction("🔍 &Search", lambda: self._switch_page(1))
        view_menu.addAction("⬇️ &Downloads", lambda: self._switch_page(2))
        view_menu.addAction("📋 &History", lambda: self._switch_page(3))

        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self._show_about)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        status: QStatusBar = self.statusBar()
        status.showMessage("Initializing…")

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        """Apply the current theme from config."""
        from .themes import get_theme_qss, clear_theme_cache
        theme_name = "dark"
        if self._config and hasattr(self._config, "gui"):
            theme_name = getattr(self._config.gui, "theme", "dark")
        clear_theme_cache()
        self.setStyleSheet(get_theme_qss(theme_name))

    # ------------------------------------------------------------------
    # Menu actions (stubs — wired to real logic in later phases)
    # ------------------------------------------------------------------

    def _switch_page(self, index: int) -> None:
        self.sidebar.set_current_index(index)

    def _import_batch(self) -> None:
        """Import a batch file of manga URLs and queue downloads."""
        import json

        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        path, _ = QFileDialog.getOpenFileName(
            self, "Import Batch File", "",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)",
        )
        if not path:
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to read file:\n{e}")
            return

        # Support both a list of items and a single object
        items = data if isinstance(data, list) else [data]
        queued = 0
        errors: list[str] = []

        for item in items:
            try:
                manga_id = item.get("manga_id") or item.get("id") or item.get("url", "")
                if not manga_id:
                    errors.append(f"Skipping item with no manga_id/id/url: {item}")
                    continue

                # Resolve manga_id from URL if needed
                if isinstance(manga_id, str) and not manga_id.isdigit():
                    # Try to extract ID from URL like https://mangadot.net/manga/12345/
                    import re
                    m = re.search(r"/manga/(\d+)", manga_id)
                    if m:
                        manga_id = int(m.group(1))
                    else:
                        errors.append(f"Cannot extract manga_id from: {manga_id}")
                        continue
                else:
                    manga_id = int(manga_id)

                manga_title = item.get("manga_title") or item.get("title") or f"Manga #{manga_id}"
                chapter_range = item.get("chapter_range") or item.get("chapters") or ""
                if isinstance(chapter_range, list):
                    chapter_range = ", ".join(str(c) for c in chapter_range)
                export_format = item.get("export_format") or item.get("format") or (
                    self._config.default_format if self._config else "cbz"
                )
                delete_images = item.get("delete_images", False)

                # Build chapter objects from range string or list
                chapters = []
                raw_chapters = item.get("chapter_ids") or item.get("chapter_list")
                if raw_chapters:
                    for i, ch_id in enumerate(raw_chapters):
                        from manga_dotnet.core.models import Chapter
                        chapters.append(Chapter(id=int(ch_id), chapter_number=float(i + 1)))
                elif isinstance(chapter_range, str) and chapter_range:
                    # Parse "1-5" or "1,3,5" into chapter IDs — we'll need to fetch them
                    # For now, store the range string and resolve later
                    pass

                task_id = self._next_task_id
                self._next_task_id += 1

                download_data = {
                    "manga_id": manga_id,
                    "manga_title": manga_title,
                    "chapters": chapters,
                    "volumes": [],
                    "format": export_format,
                    "quality": "original",
                    "delete_images": delete_images,
                    "chapter_range": str(chapter_range) if chapter_range else "",
                    "_task_id": task_id,
                    "_batch_imported": True,
                }

                # Add to queue
                self._download_queue.append(download_data)

                # Add to downloads page UI
                display_range = str(chapter_range) if chapter_range else export_format.upper()
                self.downloads_page.add_active_download(task_id, manga_title, display_range)
                queued += 1

            except Exception as e:
                errors.append(f"Error processing item: {e}")

        # Process queue
        self._process_download_queue()

        # Switch to downloads tab
        if queued > 0:
            self._switch_page(2)

        # Report results
        msg = f"📥 Queued {queued} download(s) from {path}"
        if errors:
            msg += f"\n\n{len(errors)} error(s):\n" + "\n".join(errors[:10])
        self.statusBar().showMessage(msg, 8000)
        if errors:
            QMessageBox.warning(self, "Batch Import", msg)

    def _open_settings(self) -> None:
        """Switch to the settings page."""
        self._switch_page(4)  # Settings is index 4 now

    def _on_download_requested(self, data: dict) -> None:
        """Handle download request from a MangaDetailPage — add to queue."""
        from PyQt6.QtWidgets import QMessageBox

        manga_id = data.get("manga_id", 0)
        chapters = data.get("chapters", [])
        volumes = data.get("volumes", [])
        fmt = data.get("format", "cbz")
        quality = data.get("quality", "original")
        delete_images = data.get("delete_images", False)

        # Build summary
        parts = []
        if chapters:
            ch_nums = ", ".join(
                f"{ch.chapter_number:g}" for ch in chapters[:10]
            )
            if len(chapters) > 10:
                ch_nums += f" (+{len(chapters) - 10} more)"
            parts.append(f"{len(chapters)} chapters ({ch_nums})")
        if volumes:
            vol_nums = ", ".join(
                f"Vol. {v.volume_number:g}" for v in volumes
            )
            parts.append(f"{len(volumes)} volumes ({vol_nums})")

        summary = "\n".join(parts) if parts else "Nothing selected"

        reply = QMessageBox.question(
            self,
            "Confirm Download",
            f"Manga ID: {manga_id}\n"
            f"Format: {fmt}  |  Quality: {quality}\n"
            f"Delete images after export: {'Yes' if delete_images else 'No'}\n\n"
            f"Selected:\n{summary}\n\n"
            f"Add to download queue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            chapter_range = ""
            if chapters:
                nums = [ch.chapter_number for ch in chapters]
                chapter_range = f"Ch. {min(nums):g}-{max(nums):g}" if len(nums) > 1 else f"Ch. {nums[0]:g}"
            if volumes:
                vol_range = " + ".join(f"Vol. {v.volume_number:g}" for v in volumes)
                chapter_range = f"{chapter_range} + {vol_range}" if chapter_range else vol_range

            task_id = self._next_task_id
            self._next_task_id += 1
            manga_title = data.get("manga_title") or f"Manga #{manga_id}"

            download_data = {
                **data,
                "chapter_range": chapter_range,
                "_task_id": task_id,
            }
            self._download_queue.append(download_data)

            self.downloads_page.add_active_download(
                task_id, manga_title, chapter_range or fmt
            )

            self._switch_page(2)
            self._process_download_queue()

    def _process_download_queue(self) -> None:
        """Start queued downloads up to the concurrent limit."""
        if not self._config:
            return
        max_concurrent = getattr(self._config.download, "max_concurrent_downloads", 3)
        while self._download_queue and len(self._active_workers) < max_concurrent:
            data = self._download_queue.pop(0)
            task_id = data["_task_id"]
            self._start_download(data, task_id)

    def _start_download(self, data: dict, task_id: int) -> None:
        """Start a download in a background thread."""
        chapters = data.get("chapters", [])
        volumes = data.get("volumes", [])
        fmt = data.get("format") or (self._config.default_format if self._config else "cbz")
        delete_images = data.get("delete_images") if "delete_images" in data else (
            self._config.quality.delete_images_after_export if self._config else False
        )

        if not self._client:
            self.downloads_page.complete_download(task_id, fmt=fmt)
            return

        chapter_ids = [ch.id for ch in chapters]
        chapter_numbers = [ch.chapter_number for ch in chapters]

        worker = _DownloadWorker(
            self._client, chapter_ids, fmt, delete_images,
            manga_title=data.get("manga_title", "Unknown"),
            chapter_numbers=chapter_numbers,
            parent=self,
        )

        self._active_workers[task_id] = worker

        worker.progress.connect(
            lambda pct, spd, elapsed, pages: self._update_download_progress(
                task_id, pct, spd, elapsed, pages
            )
        )
        worker.finished_ok.connect(
            lambda result: self._complete_download(task_id, data, chapters, fmt)
        )
        worker.error_occurred.connect(
            lambda msg: self._handle_download_error(task_id, msg)
        )

        self._download_workers = getattr(self, "_download_workers", [])
        self._download_workers.append(worker)
        worker.start()

    def _update_download_progress(self, task_id: int, pct: int, spd: str, elapsed: str, pages: str) -> None:
        self.downloads_page.update_download_progress(task_id, pct, spd, elapsed, pages)

    def _complete_download(self, task_id: int, data: dict, chapters: list, fmt: str) -> None:
        manga_title = data.get("manga_title") or f"Manga #{data.get('manga_id', '')}"
        chapter_range = ""
        if chapters:
            nums = [ch.chapter_number for ch in chapters]
            chapter_range = f"Ch. {min(nums):g}-{max(nums):g}" if len(nums) > 1 else f"Ch. {nums[0]:g}"

        self.downloads_page.complete_download(task_id, manga_title, chapter_range, fmt)
        self._active_workers.pop(task_id, None)

        # Compute the output path where files were saved
        manga_id = data.get("manga_id", 0)
        output_path = ""
        try:
            from manga_dotnet.core.config import Config
            config = Config.load()
            safe_title = "".join(
                c for c in manga_title if c.isalnum() or c in " -_"
            ).strip().replace(" ", "_") or f"manga_{manga_id}"
            if chapters:
                first_num = chapters[0].chapter_number
                output_path = str(config.output_dir / safe_title / f"Chapter_{first_num:g}")
            else:
                output_path = str(config.output_dir / safe_title)
        except Exception:
            pass

        # Try to fetch the manga cover URL from the API
        cover_url = ""
        if self._client and manga_id:
            try:
                resp = self._client.get(f"{self._client.API_BASE}/manga/{manga_id}/")
                import json
                info = json.loads(resp)
                manga_data = info.get("manga", info)
                photo = manga_data.get("photo", "")
                if photo:
                    cover_url = photo if photo.startswith("http") else f"https://mangadot.net{photo}"
            except Exception:
                pass

        # Record in history
        try:
            entry = self._library_manager.record_download(
                manga_id=manga_id,
                manga_title=manga_title,
                chapter_range=chapter_range,
                export_format=fmt,
                chapters_downloaded=len(chapters),
                output_path=output_path,
                cover_url=cover_url,
                status="success",
            )
            self.history_page.add_entry(
                manga_title=manga_title,
                chapter_range=chapter_range,
                export_format=fmt,
                timestamp=entry.timestamp,
                status="success",
                manga_id=entry.manga_id,
                chapters_downloaded=entry.chapters_downloaded,
                total_pages=entry.total_pages,
                output_path=entry.output_path,
                cover_url=entry.cover_url,
                errors=entry.errors,
                client=self._client,
            )
        except Exception as e:
            logger.warning("Failed to record download in history: %s", e)

        # Process next item in queue
        self._process_download_queue()

    def _handle_download_error(self, task_id: int, message: str) -> None:
        self.downloads_page.remove_download(task_id)
        self._active_workers.pop(task_id, None)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Download Error", f"Download failed: {message}")
        # Process next item in queue
        self._process_download_queue()

    def _delete_history_entry(self, key: str) -> None:
        """Remove a single history entry identified by composite key."""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Remove History Entry",
            "Remove this entry from download history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # Parse composite key: "manga_id|chapter_range|timestamp"
        try:
            parts = key.split("|", 2)
            target_mid = int(parts[0])
            target_range = parts[1] if len(parts) > 1 else ""
            target_ts = parts[2] if len(parts) > 2 else ""
        except (ValueError, IndexError):
            logger.warning("Invalid history entry key: %s", key)
            return
        # Remove only the single matching entry
        try:
            entries = self._library_manager._entries
            self._library_manager._entries = [
                e for e in entries
                if not (e.manga_id == target_mid
                        and e.chapter_range == target_range
                        and e.timestamp == target_ts)
            ]
            self._library_manager._save_history()
        except Exception as e:
            logger.warning("Failed to remove history entry: %s", e)
        # Rebuild the history page from remaining entries
        self.history_page.clear()
        try:
            for entry in self._library_manager.get_history():
                self.history_page.add_entry(
                    manga_title=entry.manga_title,
                    chapter_range=entry.chapter_range,
                    export_format=entry.export_format,
                    timestamp=entry.timestamp,
                    status=entry.status,
                    manga_id=entry.manga_id,
                    chapters_downloaded=entry.chapters_downloaded,
                    total_pages=entry.total_pages,
                    output_path=entry.output_path,
                    cover_url=entry.cover_url,
                    errors=entry.errors,
                    client=self._client,
                )
        except Exception as e:
            logger.warning("Failed to rebuild history page: %s", e)

    def _cancel_download(self, task_id: int) -> None:
        """Cancel an active download task."""
        logger.info("Cancelling download task %d", task_id)
        worker = self._active_workers.get(task_id)
        if worker:
            worker.cancel()
            self._active_workers.pop(task_id, None)
        
        self.downloads_page.remove_download(task_id)
        self.statusBar().showMessage(f"🗑 Download task {task_id} cancelled", 3000)

    def _pause_download(self, task_id: int) -> None:
        """Toggle pause/resume state for a download task."""
        worker = self._active_workers.get(task_id)
        if worker:
            is_paused = worker.toggle_pause()
            logger.info("Task %d pause status toggled to %s", task_id, is_paused)
            self.downloads_page.set_download_paused(task_id, is_paused)
            
            state_msg = "paused" if is_paused else "resumed"
            self.statusBar().showMessage(f"⏸ Download task {task_id} {state_msg}", 3000)

    def _show_about(self) -> None:
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "About MangaDotNet Downloader",
            "MangaDotNet Downloader v1.0.0\n\n"
            "A modern manga downloader for MangaDotNet\n"
            "with CLI and GUI interfaces.\n\n"
            "License: MIT",
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        """Clean up resources on close."""
        # Cancel all active downloads
        for worker in list(self._active_workers.values()):
            worker.cancel()
        self._download_queue.clear()
        if self._client:
            self._client.close()
        if self._client_worker and self._client_worker.isRunning():
            self._client_worker.quit()
            self._client_worker.wait(3000)
        super().closeEvent(event)
