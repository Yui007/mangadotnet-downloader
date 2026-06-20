"""Settings page — full settings UI with form groups and save/reset."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..themes import Colors

if TYPE_CHECKING:
    from manga_dotnet.core.config import Config


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_SETTINGS_QSS = f"""
QGroupBox {{
    font-size: 13px;
    color: {Colors.PRIMARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}
QLabel#formLabel {{
    color: {Colors.TEXT};
    font-size: 12px;
    min-width: 180px;
}}
QPushButton#saveBtn {{
    background-color: {Colors.PRIMARY};
    border: none;
    color: white;
    font-weight: bold;
    padding: 8px 24px;
    border-radius: 6px;
    font-size: 13px;
}}
QPushButton#saveBtn:hover {{
    background-color: {Colors.PRIMARY}CC;
}}
QPushButton#resetBtn {{
    background-color: transparent;
    border: 1px solid {Colors.BORDER};
    color: {Colors.MUTED};
    padding: 8px 24px;
    border-radius: 6px;
    font-size: 13px;
}}
QPushButton#resetBtn:hover {{
    border-color: {Colors.ERROR};
    color: {Colors.ERROR};
}}
"""


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------

class SettingsPage(QWidget):
    """Full settings page displayed as a sidebar tab.

    Loads values from Config on init, saves back on "Save" click.
    Emits ``settings_changed(dict)`` after a successful save.
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, config: Config | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_SETTINGS_QSS)
        self._config = config
        self._build_ui()
        if config:
            self._load_values()

    def set_config(self, config: Config) -> None:
        """Set the config object and reload values."""
        self._config = config
        self._load_values()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        container = QWidget()
        form = QVBoxLayout(container)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(16)

        # Header
        header = QLabel("⚙️ Settings")
        header.setObjectName("headingLabel")
        header.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {Colors.TEXT}; padding-bottom: 8px;")
        form.addWidget(header)

        # ── General ──
        general = QGroupBox("General")
        general_form = QFormLayout()
        general_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("~/manga")
        general_form.addRow(self._label("Output Directory:"), self.output_dir)

        self.default_format = QComboBox()
        self.default_format.addItems(["cbz", "zip", "pdf", "images", "folder"])
        general_form.addRow(self._label("Default Format:"), self.default_format)

        self.default_language = QComboBox()
        self.default_language.addItems(["en", "ko", "zh", "ja", "es", "fr", "pt", "de", "it"])
        general_form.addRow(self._label("Default Language:"), self.default_language)

        self.check_updates = QCheckBox()
        general_form.addRow(self._label("Check for Updates:"), self.check_updates)

        general.setLayout(general_form)
        form.addWidget(general)

        # ── Downloads ──
        downloads = QGroupBox("Downloads")
        dl_form = QFormLayout()
        dl_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.concurrent_chapters = QSpinBox()
        self.concurrent_chapters.setRange(1, 16)
        dl_form.addRow(self._label("Concurrent Chapters:"), self.concurrent_chapters)

        self.concurrent_images = QSpinBox()
        self.concurrent_images.setRange(1, 32)
        dl_form.addRow(self._label("Concurrent Images:"), self.concurrent_images)

        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 10)
        dl_form.addRow(self._label("Max Retries:"), self.max_retries)

        self.retry_delay = QDoubleSpinBox()
        self.retry_delay.setRange(0.5, 30.0)
        self.retry_delay.setSingleStep(0.5)
        self.retry_delay.setSuffix(" sec")
        dl_form.addRow(self._label("Retry Delay:"), self.retry_delay)

        self.timeout = QSpinBox()
        self.timeout.setRange(5, 120)
        self.timeout.setSuffix(" sec")
        dl_form.addRow(self._label("Timeout:"), self.timeout)

        downloads.setLayout(dl_form)
        form.addWidget(downloads)

        # ── Quality & Export ──
        quality = QGroupBox("Quality & Export")
        q_form = QFormLayout()
        q_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.quality = QComboBox()
        self.quality.addItems(["original", "high", "medium", "low"])
        q_form.addRow(self._label("Default Quality:"), self.quality)

        self.convert_webp = QCheckBox()
        q_form.addRow(self._label("Convert WebP → JPG:"), self.convert_webp)

        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(1, 100)
        self.jpeg_quality.setSuffix("%")
        q_form.addRow(self._label("JPEG Quality:"), self.jpeg_quality)

        self.delete_images = QCheckBox()
        q_form.addRow(self._label("Delete Images After Export:"), self.delete_images)

        quality.setLayout(q_form)
        form.addWidget(quality)

        # ── Network ──
        network = QGroupBox("Network")
        n_form = QFormLayout()
        n_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.rate_limit = QSpinBox()
        self.rate_limit.setRange(1, 50)
        self.rate_limit.setSuffix(" req/s")
        n_form.addRow(self._label("Rate Limit:"), self.rate_limit)

        self.proxy = QLineEdit()
        self.proxy.setPlaceholderText("socks5://localhost:1080")
        n_form.addRow(self._label("Proxy:"), self.proxy)

        self.dns_https = QCheckBox()
        n_form.addRow(self._label("DNS over HTTPS:"), self.dns_https)

        network.setLayout(n_form)
        form.addWidget(network)

        # ── Appearance ──
        appearance = QGroupBox("Appearance")
        a_form = QFormLayout()
        a_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.theme = QComboBox()
        self.theme.addItems(["dark", "light", "midnight"])
        a_form.addRow(self._label("Theme:"), self.theme)

        self.sidebar_collapsed = QCheckBox()
        a_form.addRow(self._label("Sidebar Collapsed:"), self.sidebar_collapsed)

        self.show_thumbnails = QCheckBox()
        a_form.addRow(self._label("Show Thumbnails:"), self.show_thumbnails)

        appearance.setLayout(a_form)
        form.addWidget(appearance)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.setObjectName("resetBtn")
        self.reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(self.reset_btn)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.save_btn)

        form.addLayout(btn_row)
        form.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("formLabel")
        return lbl

    # ------------------------------------------------------------------
    # Load / Save / Reset
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        """Load current config values into widgets."""
        if not self._config:
            return
        c = self._config

        self.output_dir.setText(str(c.output_dir))
        self._set_combo(self.default_format, c.default_format)
        self._set_combo(self.default_language, c.default_language)
        self.check_updates.setChecked(c.check_updates)

        self.concurrent_chapters.setValue(c.download.max_concurrent_chapters)
        self.concurrent_images.setValue(c.download.max_concurrent_images)
        self.max_retries.setValue(c.download.max_retries)
        self.retry_delay.setValue(c.download.retry_delay)
        self.timeout.setValue(c.download.timeout)

        self._set_combo(self.quality, c.quality.default)
        self.convert_webp.setChecked(c.quality.convert_webp)
        self.jpeg_quality.setValue(c.quality.jpeg_quality)
        self.delete_images.setChecked(c.quality.delete_images_after_export)

        self.rate_limit.setValue(c.network.rate_limit_rps)
        self.proxy.setText(c.network.proxy or "")
        self.dns_https.setChecked(c.network.dns_over_https)

        self._set_combo(self.theme, c.gui.theme)
        self.sidebar_collapsed.setChecked(c.gui.sidebar_collapsed)
        self.show_thumbnails.setChecked(c.gui.show_thumbnails)

    def _save(self) -> None:
        """Save settings to JSON file."""
        if not self._config:
            return
        c = self._config

        c.output_dir = Path(self.output_dir.text()) if self.output_dir.text() else Path.home() / "manga"
        c.default_format = self.default_format.currentText()
        c.default_language = self.default_language.currentText()
        c.check_updates = self.check_updates.isChecked()

        c.download.max_concurrent_chapters = self.concurrent_chapters.value()
        c.download.max_concurrent_images = self.concurrent_images.value()
        c.download.max_retries = self.max_retries.value()
        c.download.retry_delay = self.retry_delay.value()
        c.download.timeout = self.timeout.value()

        c.quality.default = self.quality.currentText()
        c.quality.convert_webp = self.convert_webp.isChecked()
        c.quality.jpeg_quality = self.jpeg_quality.value()
        c.quality.delete_images_after_export = self.delete_images.isChecked()

        c.network.rate_limit_rps = self.rate_limit.value()
        c.network.proxy = self.proxy.text() or None
        c.network.dns_over_https = self.dns_https.isChecked()

        c.gui.theme = self.theme.currentText()
        c.gui.sidebar_collapsed = self.sidebar_collapsed.isChecked()
        c.gui.show_thumbnails = self.show_thumbnails.isChecked()

        c.save()
        self.settings_changed.emit(c.to_dict())

        # Visual feedback
        self.save_btn.setText("✅ Saved!")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.save_btn.setText("Save Settings"))

    def _reset(self) -> None:
        """Reset to default settings."""
        from manga_dotnet.core.config import Config

        self._config = Config()
        self._load_values()

        # Visual feedback
        self.reset_btn.setText("✅ Reset!")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.reset_btn.setText("Reset to Default"))

    @staticmethod
    def _set_combo(combo: QComboBox, value: str) -> None:
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
