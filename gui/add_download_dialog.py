import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor, QKeySequence, QShortcut,
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QSpinBox, QFrame, QFileDialog, QWidget, QDialogButtonBox,
)

from engine.config import config
from engine.logger import get_logger

log = get_logger("gui")

ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "icons")

# Category → icon / label / extensions mapping
CATEGORY_INFO = {
    "video":      ("🎬", "Video"),
    "audio":      ("🎵", "Audio"),
    "document":   ("📄", "Document"),
    "archive":    ("📦", "Archive"),
    "software":   ("💻", "Software"),
    "image":      ("🖼️", "Image"),
    "general":    ("📁", "General"),
}

CATEGORY_EXTENSIONS = {
    "video":    ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg", "mpeg", "3gp", "ogv", "ts"],
    "audio":    ["mp3", "wav", "flac", "aac", "ogg", "wma", "m4a", "opus"],
    "document": ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "txt", "csv", "rtf", "epub", "mobi"],
    "archive":  ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab", "arj", "lzh"],
    "software": ["exe", "msi", "dmg", "apk", "deb", "rpm", "appimage"],
    "image":    ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "ico", "tiff", "psd"],
}


def _adaptive_text_color(bg: QColor) -> QColor:
    """Return white or near-black depending on background lightness."""
    luma = 0.299 * bg.redF() + 0.587 * bg.greenF() + 0.114 * bg.blueF()
    return QColor("#222") if luma > 0.55 else QColor("#eee")


def _human_readable_size(size_bytes: int) -> str:
    if size_bytes < 0:
        return "Unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:,.1f} {unit}" if unit != "B" else f"{size_bytes:,} B"
        size_bytes /= 1024
    return f"{size_bytes:,.1f} PB"


def _disk_free(path: str) -> int:
    """Free disk space in bytes at the given path."""
    try:
        _, _, free = shutil.disk_usage(Path(path).anchor if os.name == "nt" else path)
        return free
    except Exception:
        return -1


def guess_category_from_filename(filename: str) -> str:
    """Return best-guess category from filename extension."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if not ext:
        return "general"
    for cat, exts in CATEGORY_EXTENSIONS.items():
        if ext in exts:
            return cat
    return "general"


def _get_url_final_filename(url: str, fallback: str = "") -> str:
    """Pull filename from URL path, strip query params."""
    path = urlparse(url).path
    name = Path(path).name.split("?")[0] if path else ""
    return name or fallback or url.rsplit("/", 1)[-1].split("?")[0] or "download"


# ============================================================================
# Download Confirmation Dialog
# ============================================================================

class DownloadConfirmationDialog(QDialog):
    """
    Modern high-speed download confirmation dialog.

    Workflow:
      1. Browser extension intercepts download
      2. Native host relays metadata to desktop app
      3. Desktop app opens THIS dialog
      4. User reviews / adjusts parameters
      5. "Start Download" → task moves to QUEUED → download begins
      6. "Cancel" → task is removed from queue
    """

    # Emitted when the user confirms with the final DownloadTask
    download_confirmed = pyqtSignal(dict)

    def __init__(
        self, parent=None,
        url: str = "",
        filename: str = "",
        file_size: int = 0,
        mime: str = "",
        referrer: str = "",
        cookies: str = "",
    ):
        super().__init__(parent)

        self.url = url.strip()
        self.cookies = cookies
        self.referrer = referrer
        self.mime = mime
        self.file_size = file_size

        # Derive initial filename
        raw_filename = _get_url_final_filename(url, filename)
        self.original_filename = raw_filename

        # Guess category
        self.category = guess_category_from_filename(raw_filename)

        # Default download path
        self._save_root = str(config.download_dir)

        # ── window setup ──────────────────────────────────────────
        self.setWindowTitle("Download File — DLite")
        self.setMinimumSize(580, 440)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setModal(True)

        # Keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Return), self, self._on_start)
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self, self._on_start)
        QShortcut(Qt.Key.Key_Escape, self, self._on_cancel)

        self._build_ui()
        self._apply_styles()

        # Track confirmed state so we don't double-emit
        self._confirmed = False

    # ── Force the dialog to top when shown ─────────────────────────
    def showEvent(self, event):
        """Raise and activate the dialog so it appears on top of all windows."""
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

        # On Windows, Qt's raise/activateWindow may not be enough due to
        # foreground-stealing prevention. Use Win32 SetForegroundWindow as
        # a fallback after a short timer.
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass  # Non-critical; dialog is still usable.

    # ── UI construction ──────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(10)

        # --- Header strip: file icon + name + type badge ---
        header = QHBoxLayout()
        header.setSpacing(10)

        icon_lbl = QLabel("📥")
        icon_lbl.setFixedSize(48, 48)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setObjectName("headerIcon")
        header.addWidget(icon_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        self.lbl_filename = QLabel(self.original_filename)
        self.lbl_filename.setObjectName("headerFilename")
        self.lbl_filename.setWordWrap(True)
        info_col.addWidget(self.lbl_filename)

        type_row = QHBoxLayout()
        type_row.setSpacing(6)
        self.lbl_type = QLabel(self.mime or urlparse(self.url).path.rsplit(".", 1)[-1].upper() or "FILE")
        self.lbl_type.setObjectName("typeBadge")
        type_row.addWidget(self.lbl_type)
        type_row.addStretch()
        info_col.addLayout(type_row)

        header.addLayout(info_col, 1)
        header.addStretch()

        root.addLayout(header)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        # --- Details grid ---
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 4, 0, 4)

        row = 0

        def _add_row(label_text: str, widget: QWidget, ctrl_name: str = ""):
            nonlocal row
            lbl = QLabel(label_text)
            lbl.setObjectName("gridLabel")
            grid.addWidget(lbl, row, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(widget, row, 1, 1, 2)
            if ctrl_name:
                setattr(self, ctrl_name, widget)
            row += 1
            return widget

        # URL
        self.url_input = QLineEdit(self.url)
        self.url_input.setReadOnly(True)
        self.url_input.setObjectName("readOnlyLine")
        _add_row("URL:", self.url_input, "url_input")

        # Estimated size
        lbl_size = QLabel(_human_readable_size(self.file_size) if self.file_size else "Unknown")
        lbl_size.setObjectName("metricValue")
        self.lbl_size = lbl_size
        _add_row("Estimated size:", lbl_size, "lbl_size")

        # File name (editable)
        self.filename_input = QLineEdit(self.original_filename)
        self.filename_input.setObjectName("editLine")
        _add_row("Save as:", self.filename_input, "filename_input")

        # Category picker
        cat_combo = QComboBox()
        cat_combo.setObjectName("catCombo")
        cat_combo.addItem("🎬  Video", "video")
        cat_combo.addItem("🎵  Audio", "audio")
        cat_combo.addItem("📄  Document", "document")
        cat_combo.addItem("📦  Archive", "archive")
        cat_combo.addItem("💻  Software", "software")
        cat_combo.addItem("🖼️  Image", "image")
        cat_combo.addItem("📁  General", "general")
        idx = cat_combo.findData(self.category)
        if idx >= 0:
            cat_combo.setCurrentIndex(idx)
        self.cat_combo = cat_combo
        _add_row("Category:", cat_combo, "cat_combo")

        # Save to folder (line edit + browse button)
        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        self.folder_input = QLineEdit(self._save_root)
        self.folder_input.setObjectName("editLine")
        self.folder_input.setReadOnly(False)
        folder_row.addWidget(self.folder_input, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("browseBtn")
        browse_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(browse_btn)
        folder_widget = QWidget()
        folder_widget.setLayout(folder_row)
        _add_row("Save to:", folder_widget, "folder_row_widget")
        self.browse_btn = browse_btn

        # Disk space
        free = _disk_free(self._save_root)
        self.lbl_disk = QLabel(
            _human_readable_size(free) if free > 0 else "N/A"
        )
        self.lbl_disk.setObjectName("metricValue")
        _add_row("Disk free:", self.lbl_disk, "lbl_disk")

        # Resume support
        self.chk_resume = QCheckBox("Resume support (if server supports)")
        self.chk_resume.setChecked(True)
        self.chk_resume.setObjectName("checkBox")
        _add_row("Resume:", self.chk_resume, "chk_resume")

        # Connections (segments)
        conn_row = QHBoxLayout()
        conn_row.setSpacing(4)
        self.spin_segments = QSpinBox()
        self.spin_segments.setRange(1, 32)
        self.spin_segments.setValue(max(config.get("max_segments", 8), 1))
        self.spin_segments.setObjectName("spinBox")
        conn_lbl = QLabel("connections")
        conn_lbl.setObjectName("gridLabel")
        conn_row.addWidget(self.spin_segments)
        conn_row.addWidget(conn_lbl)
        conn_row.addStretch()
        conn_widget = QWidget()
        conn_widget.setLayout(conn_row)
        _add_row("Segments:", conn_widget)

        # Speed limit (optional)
        speed_row = QHBoxLayout()
        speed_row.setSpacing(4)
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(0, 999999)
        self.speed_spin.setSuffix(" KB/s")
        self.speed_spin.setSpecialValueText("Unlimited")
        self.speed_spin.setValue(config.get("speed_limit_kbps", 0))
        self.speed_spin.setObjectName("spinBox")
        speed_row.addWidget(self.speed_spin)
        speed_row.addStretch()
        speed_widget = QWidget()
        speed_widget.setLayout(speed_row)
        _add_row("Speed limit:", speed_widget)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        root.addLayout(grid)

        root.addStretch()

        # --- Separator ---
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setObjectName("separator")
        root.addWidget(sep2)

        # --- Button row ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(cancel_btn)

        start_btn = QPushButton(" ▶  Start Download")
        start_btn.setObjectName("startBtn")
        start_btn.clicked.connect(self._on_start)
        start_btn.setDefault(True)
        btn_row.addWidget(start_btn)

        root.addLayout(btn_row)

    # ── folder picker ────────────────────────────────────────────
    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choose download folder", self.folder_input.text().strip() or str(config.download_dir),
        )
        if folder:
            self.folder_input.setText(folder)
            self._save_root = folder
            free = _disk_free(folder)
            self.lbl_disk.setText(_human_readable_size(free) if free > 0 else "N/A")
            config.set("download_dir", folder)
            log.info("[dialog] download folder changed to: %s", folder)

    def _on_start(self):
        if self._confirmed:
            return
        self._confirmed = True

        fname = self.filename_input.text().strip() or self.original_filename or "download"
        folder = self.folder_input.text().strip() or str(config.download_dir)
        cat = self.cat_combo.currentData() or "general"
        segments = self.spin_segments.value()
        speed_limit = self.speed_spin.value()
        resume_enabled = self.chk_resume.isChecked()

        log.info(
            "[dialog] user confirmed: url=%s filename=%s folder=%s category=%s segments=%d speed=%d resume=%s",
            self.url, fname, folder, cat, segments, speed_limit, resume_enabled,
        )

        # Prepare result dict
        result = {
            "url": self.url,
            "filename": fname,
            "save_path": folder,
            "category": cat,
            "segments": segments,
            "speed_limit_kbps": speed_limit,
            "resume_enabled": resume_enabled,
            "cookies": self.cookies,
            "referrer": self.referrer,
            "mime": self.mime,
            "total_size": self.file_size,
        }
        self.download_confirmed.emit(result)
        self.accept()

    def _on_cancel(self):
        log.info("[dialog] user canceled download: %s", self.url)
        self.reject()

    # ── styling ──────────────────────────────────────────────────
    def _apply_styles(self):
        """Apply a professional dark-themed stylesheet."""
        self.setStyleSheet("""
            QDialog {
                background-color: #181c24;
                border: 1px solid #2a2e3a;
                border-radius: 10px;
            }
            QLabel {
                color: #d0d4dd;
                font-family: "Segoe UI", sans-serif;
                font-size: 12px;
            }
            QLabel#headerIcon {
                background: #20242e;
                border-radius: 8px;
                font-size: 28px;
                padding: 4px;
            }
            QLabel#headerFilename {
                font-size: 15px;
                font-weight: bold;
                color: #f0f2f5;
            }
            QLabel#typeBadge {
                background: #272c36;
                color: #8ab4f8;
                padding: 2px 10px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
            }
            QLabel#gridLabel {
                color: #8a93a5;
                font-size: 11px;
            }
            QLabel#metricValue {
                color: #b0b8c5;
                font-weight: 600;
            }
            QLabel#comingSoon {
                color: #555;
                font-style: italic;
                font-size: 10px;
            }
            QFrame#separator {
                background: #2a2e3a;
                max-height: 1px;
            }
            QLineEdit {
                background: #20242e;
                border: 1px solid #2f3440;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e0e4ec;
                font-size: 11px;
                selection-background-color: #1a73e8;
            }
            QLineEdit#readOnlyLine {
                background: #1a1d25;
                color: #8890a0;
            }
            QComboBox {
                background: #20242e;
                border: 1px solid #2f3440;
                border-radius: 4px;
                padding: 3px 8px;
                color: #e0e4ec;
                font-size: 11px;
            }
            QComboBox QAbstractItemView {
                background: #222632;
                color: #d0d4dd;
                selection-background-color: #1a73e8;
            }
            QCheckBox {
                color: #c0c6d0;
                font-size: 11px;
                spacing: 6px;
            }
            QSpinBox {
                background: #20242e;
                border: 1px solid #2f3440;
                border-radius: 4px;
                padding: 2px 6px;
                color: #e0e4ec;
                font-size: 11px;
            }
            QPushButton {
                padding: 6px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                font-family: "Segoe UI", sans-serif;
            }
            QPushButton#startBtn {
                background: #2e7d32;
                color: #ffffff;
                border: 1px solid #388e3c;
            }
            QPushButton#startBtn:hover {
                background: #388e3c;
            }
            QPushButton#startBtn:pressed {
                background: #1b5e20;
            }
            QPushButton#cancelBtn {
                background: #343840;
                color: #c0c4ce;
                border: 1px solid #444a55;
            }
            QPushButton#cancelBtn:hover {
                background: #3e444f;
            }
            QPushButton#browseBtn {
                background: #2a3040;
                color: #ccd2dc;
                border: 1px solid #384050;
                padding: 4px 12px;
                font-size: 10px;
            }
            QPushButton#browseBtn:hover {
                background: #323848;
            }
            QPushButton#advancedBtn {
                background: transparent;
                color: #8a93a5;
                border: 1px solid #2a2e3a;
                font-size: 10px;
            }
        """)


# ============================================================================
# Simple manual "Add URL" dialog (retained for toolbar)
# ============================================================================

class AddDownloadDialog(QDialog):
    """Simple fallback used when the user manually adds a URL."""

    def __init__(self, parent=None, prefilled_url=""):
        super().__init__(parent)
        self.setWindowTitle("Add download")
        self.setMinimumWidth(420)

        self.url_input = QLineEdit(prefilled_url)
        self.url_input.setPlaceholderText("https://example.com/file.zip")

        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("leave empty to keep the original name")

        form = QGridLayout()
        form.addWidget(QLabel("URL"), 0, 0)
        form.addWidget(self.url_input, 0, 1)
        form.addWidget(QLabel("Save as"), 1, 0)
        form.addWidget(self.filename_input, 1, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter the direct link to the file you want to download."))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self):
        return self.url_input.text().strip(), self.filename_input.text().strip()
