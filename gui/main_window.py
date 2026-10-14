import os
import time
import subprocess
import sys
import json
import logging
from datetime import datetime

try:
    import winreg
except ImportError:
    winreg = None  # Non-Windows platform

from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QSize, QPointF, QRectF
from PyQt6.QtGui import QAction, QIcon, QFont, QColor, QPainter, QPen, QBrush, QPainterPath, QActionGroup
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QLineEdit,
    QTableWidget, QTableWidgetItem, QProgressBar, QSystemTrayIcon, QMenu,
    QMessageBox, QHeaderView, QStyle, QLabel, QSplitter, QTreeWidget,
    QTreeWidgetItem, QStatusBar, QPushButton, QDialog, QFormLayout,
    QSpinBox, QComboBox, QCheckBox, QDialogButtonBox, QGroupBox, QFileDialog,
    QTabWidget, QTextEdit, QFrame, QScrollArea, QApplication, QAbstractItemView,
)

from engine.config import config
from engine.events import bus
from engine.models import DownloadStatus
from engine.queue_manager import queue_manager
from engine.clipboard import is_downloadable_url
from engine.scheduler import scheduler
from gui.add_download_dialog import AddDownloadDialog, DownloadConfirmationDialog
from gui.scheduler_dialog import SchedulerDialog
from gui.batch_pattern_dialog import BatchPatternDialog
from gui.i18n import t
from gui.theme import stylesheet_for

COLUMNS = ["File Name", "Size", "Progress", "Speed", "Time Left", "Status", "Added"]

# Category icons
CATEGORY_ICONS = {
    "general": "📁",
    "video": "🎬",
    "audio": "🎵",
    "document": "📄",
    "archive": "📦",
    "image": "🖼️",
    "program": "⚙️",
}

# Map extensions to categories
EXT_CATEGORY_MAP = {
    # Video
    "mp4": "video", "mkv": "video", "avi": "video", "mov": "video",
    "wmv": "video", "flv": "video", "webm": "video", "m4v": "video",
    "mpg": "video", "mpeg": "video", "3gp": "video", "ogv": "video", "ts": "video",
    # Audio
    "mp3": "audio", "wav": "audio", "flac": "audio", "aac": "audio",
    "ogg": "audio", "wma": "audio", "m4a": "audio", "opus": "audio",
    # Documents
    "pdf": "document", "doc": "document", "docx": "document",
    "xls": "document", "xlsx": "document", "ppt": "document", "pptx": "document",
    "odt": "document", "ods": "document", "odp": "document",
    "txt": "document", "csv": "document", "rtf": "document",
    "epub": "document", "mobi": "document",
    # Archives
    "zip": "archive", "rar": "archive", "7z": "archive", "tar": "archive",
    "gz": "archive", "bz2": "archive", "xz": "archive", "iso": "archive",
    "cab": "archive", "arj": "archive", "lzh": "archive",
    # Images
    "jpg": "image", "jpeg": "image", "png": "image", "gif": "image",
    "bmp": "image", "svg": "image", "webp": "image", "ico": "image",
    "tiff": "image", "psd": "image",
    # Programs
    "exe": "program", "msi": "program", "dmg": "program", "apk": "program",
    "deb": "program", "rpm": "program", "appimage": "program",
}


def human_size(n) -> str:
    if n is None or n < 0:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"


def human_time(seconds) -> str:
    if seconds is None or seconds <= 0 or seconds == float("inf"):
        return "-"
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def guess_category(filename: str) -> str:
    """Detect category from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return EXT_CATEGORY_MAP.get(ext, "general")


class SpeedGraphWidget(QWidget):
    """Real-time running chart of active download speeds."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples = [0.0] * 60
        self.setMinimumHeight(100)

    def add_sample(self, val):
        self.samples.append(val)
        if len(self.samples) > 60:
            self.samples.pop(0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Grid lines
        is_dark = config.get("theme", "dark") == "dark"
        grid_color = QColor("#2d2e33") if is_dark else QColor("#e0e0e0")
        painter.setPen(QPen(grid_color, 1, Qt.PenStyle.DashLine))
        
        for i in range(1, 4):
            y = int(h * i / 4)
            painter.drawLine(0, y, w, y)
        for i in range(1, 10):
            x = int(w * i / 10)
            painter.drawLine(x, 0, x, h)

        max_val = max(self.samples)
        if max_val <= 0:
            max_val = 1024 * 1024  # default scale 1 MB/s
        max_val *= 1.15  # headroom

        path = QPainterPath()
        n = len(self.samples)
        points = []
        for idx, s in enumerate(self.samples):
            x = w * idx / (n - 1)
            y = h - (s / max_val) * h
            y = max(min(y, h - 2), 2)
            points.append(QPointF(x, y))

        if points:
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)

            # Draw filled area
            area_path = QPainterPath(path)
            area_path.lineTo(w, h)
            area_path.lineTo(0, h)
            area_path.closeSubpath()
            
            fill_color = QColor(76, 175, 80, 40)
            painter.fillPath(area_path, QBrush(fill_color))

            # Draw line
            painter.setPen(QPen(QColor("#4CAF50"), 2, Qt.PenStyle.SolidLine))
            painter.drawPath(path)

        # Draw legend
        painter.setPen(QColor("#8a8b91") if is_dark else QColor("#555555"))
        painter.drawText(10, 20, f"Max: {human_size(max_val)}/s")
        painter.drawText(10, h - 10, "Real-time Downloading Speed (Last 60 seconds)")


class SegmentsProgressWidget(QWidget):
    """Draws concurrent segment blocks and overall thread download progress."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.task = None
        self.setMinimumHeight(60)

    def set_task(self, task):
        self.task = task
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        is_dark = config.get("theme", "dark") == "dark"

        # Background
        bg_color = QColor("#1e1f24") if is_dark else QColor("#ffffff")
        painter.fillRect(0, 0, w, h, QBrush(bg_color))

        if not self.task or not self.task.segments or self.task.total_size <= 0:
            painter.setPen(QColor("#8a8b91"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No active download selected or size is unknown")
            return

        total_size = self.task.total_size

        for seg in self.task.segments:
            seg_size = seg.size
            if seg_size <= 0:
                continue

            x_start = w * seg.start / total_size
            x_end = w * (seg.end + 1) / total_size
            seg_width = x_end - x_start

            seg_rect = QRectF(x_start, 10, seg_width, h - 35)

            # Segment base
            base_color = QColor("#2d2e33") if is_dark else QColor("#e8e8e8")
            painter.fillRect(seg_rect, QBrush(base_color))
            painter.setPen(QPen(QColor("#1a1b1e") if is_dark else QColor("#f0f2f5"), 0.5))
            painter.drawRect(seg_rect)

            # Downloaded part
            ratio = seg.downloaded / seg_size
            dl_width = seg_width * ratio
            if dl_width > 0:
                dl_rect = QRectF(x_start, 10, dl_width, h - 35)
                painter.fillRect(dl_rect, QBrush(QColor("#2979ff")))

        # Segment info
        painter.setPen(QColor("#e0e0e0") if is_dark else QColor("#1a1a1a"))
        font = painter.font()
        # Guard against QFont::setPointSize(-1) when the painter's default
        # font has an uninitialized size
        fontSize = font.pointSize()
        if fontSize > 0:
            font.setPointSize(fontSize)
        else:
            font.setPointSize(9)
        painter.setFont(font)
        
        info = f"Segments: {len(self.task.segments)}  |  Resumable: {'Yes' if self.task.supports_range else 'No'}  |  Downloaded: {human_size(self.task.downloaded_bytes)} of {human_size(total_size)}"
        painter.drawText(10, h - 8, info)


class LogSignalEmitter(QObject):
    log_written = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    def __init__(self, emitter: LogSignalEmitter):
        super().__init__()
        self.emitter = emitter
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] (%(name)s) %(message)s", "%H:%M:%S"))

    def emit(self, record):
        msg = self.format(record)
        self.emitter.log_written.emit(msg)


class EngineBridge(QObject):
    task_added = pyqtSignal(object)
    task_removed = pyqtSignal(str)
    task_updated = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        bus.on("task_added", lambda t: self.task_added.emit(t))
        bus.on("task_removed", lambda tid: self.task_removed.emit(tid))
        bus.on("task_updated", lambda t: self.task_updated.emit(t))


class SettingsDialog(QDialog):
    """Application settings dialog."""

    # ── Known browser → registry path / extension path ───────────
    BROWSERS = [
        {
            "name": "Google Chrome",
            "icon": "🌐",
            "registry_key": r"Software\Google\Chrome\NativeMessagingHosts",
            "exe_name": "chrome.exe",
            "extension_id": "mkkjhabahmcbbnhkpkahleljolldhdgf",
            "ext_folder": "chromium",
            "manifest_filename": "com.dlite.host.chromium.json",
            "ext_path_sub": r"Google\Chrome\User Data\Default\Extensions\mkkjhabahmcbbnhkpkahleljolldhdgf",
        },
        {
            "name": "Microsoft Edge",
            "icon": "🟦",
            "registry_key": r"Software\Microsoft\Edge\NativeMessagingHosts",
            "exe_name": "msedge.exe",
            "extension_id": "mkkjhabahmcbbnhkpkahleljolldhdgf",
            "ext_folder": "chromium",
            "manifest_filename": "com.dlite.host.chromium.json",
            "ext_path_sub": r"Microsoft\Edge\User Data\Default\Extensions\mkkjhabahmcbbnhkpkahleljolldhdgf",
        },
        {
            "name": "Brave Browser",
            "icon": "🦁",
            "registry_key": r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
            "exe_name": "brave.exe",
            "extension_id": "mkkjhabahmcbbnhkpkahleljolldhdgf",
            "ext_folder": "chromium",
            "manifest_filename": "com.dlite.host.chromium.json",
            "ext_path_sub": r"BraveSoftware\Brave-Browser\User Data\Default\Extensions\mkkjhabahmcbbnhkpkahleljolldhdgf",
        },
        {
            "name": "Opera Browser",
            "icon": "🔴",
            "registry_key": r"Software\Opera Software\NativeMessagingHosts",
            "exe_name": "launcher.exe",
            "extension_id": "mkkjhabahmcbbnhkpkahleljolldhdgf",
            "ext_folder": "chromium",
            "manifest_filename": "com.dlite.host.chromium.json",
            "ext_path_sub": r"Opera Software\Opera Stable\Extensions\mkkjhabahmcbbnhkpkahleljolldhdgf",
        },
        {
            "name": "Mozilla Firefox",
            "icon": "🦊",
            "registry_key": r"Software\Mozilla\NativeMessagingHosts",
            "exe_name": "firefox.exe",
            "extension_id": "dlite@safouane02",
            "ext_folder": "firefox",
            "manifest_filename": "com.dlite.host.firefox.json",
            "ext_path_sub": None,  # Firefox uses a different extension installation mechanism
        },
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DLite Settings")
        self.setMinimumSize(500, 400)

        # Resolve paths
        self._project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._ext_dir = os.path.join(self._project_root, "browser-extension")
        self._native_host_dir = os.path.join(self._project_root, "native_host")
        self._python_exe = sys.executable

        tabs = QTabWidget()

        # --- General Tab ---
        general_tab = QWidget()
        gen_layout = QFormLayout(general_tab)

        self.download_dir_input = QLineEdit(str(config.download_dir))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.download_dir_input)
        dir_row.addWidget(browse_btn)
        gen_layout.addRow("Download folder:", dir_row)

        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 10)
        self.max_concurrent_spin.setValue(config.get("max_concurrent_downloads", 3))
        gen_layout.addRow("Max concurrent downloads:", self.max_concurrent_spin)

        self.max_segments_spin = QSpinBox()
        self.max_segments_spin.setRange(1, 32)
        self.max_segments_spin.setValue(config.get("max_segments", 8))
        gen_layout.addRow("Max segments per file:", self.max_segments_spin)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(config.get("theme", "dark"))
        gen_layout.addRow("Theme:", self.theme_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("العربية (Arabic)", "ar")
        current_lang = config.get("language", "en")
        idx = 1 if current_lang == "ar" else 0
        self.language_combo.setCurrentIndex(idx)
        gen_layout.addRow("Language / اللغة:", self.language_combo)

        self.minimize_tray_check = QCheckBox("Minimize to system tray")
        self.minimize_tray_check.setChecked(config.get("minimize_to_tray", True))
        gen_layout.addRow("", self.minimize_tray_check)

        self.auto_start_check = QCheckBox("Start downloads automatically")
        self.auto_start_check.setChecked(config.get("auto_start_downloads", True))
        gen_layout.addRow("", self.auto_start_check)

        self.clipboard_monitor_check = QCheckBox("Monitor clipboard for downloadable URLs")
        self.clipboard_monitor_check.setChecked(config.get("monitor_clipboard", True))
        gen_layout.addRow("", self.clipboard_monitor_check)

        self.notify_complete_check = QCheckBox("Show desktop notification on download completion")
        self.notify_complete_check.setChecked(config.get("notify_on_complete", True))
        gen_layout.addRow("", self.notify_complete_check)

        self.user_agent_input = QLineEdit(config.get("user_agent", ""))
        self.user_agent_input.setPlaceholderText("Mozilla/5.0 ...")
        gen_layout.addRow("Custom User-Agent:", self.user_agent_input)

        tabs.addTab(general_tab, "General")

        # --- Speed Tab ---
        speed_tab = QWidget()
        speed_layout = QFormLayout(speed_tab)

        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(0, 100000)
        self.speed_limit_spin.setValue(config.get("speed_limit_kbps", 0))
        self.speed_limit_spin.setSuffix(" KB/s")
        self.speed_limit_spin.setSpecialValueText("Unlimited")
        self.speed_limit_spin.setToolTip("0 = unlimited")
        speed_layout.addRow("Global speed limit:", self.speed_limit_spin)

        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(64, 4096)
        self.chunk_size_spin.setValue(config.get("chunk_size", 256 * 1024) // 1024)
        self.chunk_size_spin.setSuffix(" KB")
        speed_layout.addRow("Buffer chunk size:", self.chunk_size_spin)

        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 20)
        self.retry_spin.setValue(config.get("retry_attempts", 5))
        speed_layout.addRow("Retry attempts:", self.retry_spin)

        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(1, 60)
        self.retry_delay_spin.setValue(config.get("retry_delay_seconds", 3))
        self.retry_delay_spin.setSuffix(" sec")
        speed_layout.addRow("Retry delay:", self.retry_delay_spin)

        tabs.addTab(speed_tab, "Connection")

        # --- Browser Extensions Tab (NEW) ---
        ext_tab = self._build_browser_extensions_tab()
        tabs.addTab(ext_tab, "Browser Extensions")

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tabs)
        main_layout.addWidget(buttons)

    # ──────────────────────────────────────────────────────────────
    # Browser Extensions Tab — auto-detect + install + status
    # ──────────────────────────────────────────────────────────────
    def _build_browser_extensions_tab(self):
        """
        Detect installed browsers and display their extension status.
        For each browser the user can:
          - Install the Native Messaging Host (register manifest in registry)
          - Get instructions to load the extension in developer mode
        Status indicators show whether the host is registered and extension is detected.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("<b>Browser Extension Installation</b>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        info = QLabel(
            "DLite uses a browser extension to intercept downloads. "
            "For each browser below, install the Native Messaging Host "
            "(auto-registers in registry), then load the extension manually."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 11px; color: #8a93a5;")
        layout.addWidget(info)

        # Scroll area for browser cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(8)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Detect & render each browser
        for browser_info in self.BROWSERS:
            detected, exe_path = self._detect_browser(browser_info["exe_name"])
            if not detected:
                continue  # Only show installed browsers

            host_installed = self._check_host_registered(browser_info["registry_key"])
            ext_installed = self._check_extension_present(browser_info)

            # ── Card ──
            card = QFrame()
            card.setObjectName("browserCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card.setStyleSheet("QFrame#browserCard { background: #20242e; border-radius: 8px; padding: 10px; margin: 2px; }")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)

            # Browser name + icon + status
            header_row = QHBoxLayout()
            header_row.setSpacing(8)

            icon_lbl = QLabel(browser_info["icon"])
            icon_lbl.setStyleSheet("font-size: 20px;")
            header_row.addWidget(icon_lbl)

            name_lbl = QLabel(f"<b>{browser_info['name']}</b>")
            name_lbl.setStyleSheet("font-size: 13px; color: #f0f2f5;")
            header_row.addWidget(name_lbl)
            header_row.addStretch()

            # Status badges
            host_status = "✅ Host registered" if host_installed else "⚠ Host not registered"
            ext_status = "✅ Extension detected" if ext_installed else "⚠ Extension not detected"
            status_lbl = QLabel(f"{host_status}  |  {ext_status}")
            status_lbl.setStyleSheet(
                f"font-size: 10px; color: {'#4caf50' if host_installed and ext_installed else '#ff9800'};"
            )
            header_row.addWidget(status_lbl)

            card_layout.addLayout(header_row)

            # Description
            desc_lbl = QLabel(
                f"Detected at: {exe_path}\n"
                f"Extension folder: {browser_info['ext_folder']} (ID: {browser_info['extension_id']})"
            )
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("font-size: 10px; color: #8890a0;")
            card_layout.addWidget(desc_lbl)

            # Buttons row
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)

            install_host_btn = QPushButton("🔧 Install Native Host")
            install_host_btn.setStyleSheet("padding: 4px 10px; font-size: 10px; background: #2a3040;")
            install_host_btn.clicked.connect(
                lambda checked, bi=browser_info: self._install_native_host(bi)
            )
            btn_row.addWidget(install_host_btn)

            load_ext_btn = QPushButton("📂 Load Extension Instructions")
            load_ext_btn.setStyleSheet("padding: 4px 10px; font-size: 10px; background: #2a3040;")
            load_ext_btn.clicked.connect(
                lambda checked, bi=browser_info: self._show_extension_instructions(bi)
            )
            btn_row.addWidget(load_ext_btn)

            btn_row.addStretch()
            card_layout.addLayout(btn_row)

            scroll_layout.addWidget(card)

        # If no browsers detected
        if scroll_layout.count() == 0:
            no_browsers_lbl = QLabel(
                "No supported browsers detected on this system.\n"
                "Supported browsers: Chrome, Edge, Brave, Opera, Firefox."
            )
            no_browsers_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_browsers_lbl.setWordWrap(True)
            no_browsers_lbl.setStyleSheet("color: #8890a0; font-size: 12px; padding: 20px;")
            scroll_layout.addWidget(no_browsers_lbl)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Port & TCP settings
        port_group = QGroupBox("TCP Communication Port")
        port_layout = QHBoxLayout(port_group)
        port_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(config.get("native_host_port", 38271))
        port_layout.addWidget(self.port_spin)
        port_layout.addStretch()
        layout.addWidget(port_group)

        return widget

    def _detect_browser(self, exe_name: str):
        """
        Auto-detect a browser by searching common installation paths
        using the Windows registry ProgramFilesDir and Local AppData.
        Returns (detected: bool, path: str).
        """
        # Common install roots
        roots = [
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")), ""),
        ]

        # Known install sub-folders per browser
        known_dirs = {
            "chrome.exe": ["Google\\Chrome\\Application"],
            "msedge.exe": ["Microsoft\\Edge\\Application"],
            "brave.exe": ["BraveSoftware\\Brave-Browser\\Application"],
            "launcher.exe": ["Opera Software\\Opera Stable", "Opera Software\\Opera GX Stable"],
            "firefox.exe": ["Mozilla Firefox"],
        }

        subdirs = known_dirs.get(exe_name, [exe_name.replace(".exe", "")])

        for root in roots:
            for sub in subdirs:
                candidate = os.path.join(root, sub, exe_name)
                if os.path.isfile(candidate):
                    return True, candidate

        # Fallback: try via where.exe
        try:
            import shutil
            found = shutil.which(exe_name)
            if found:
                return True, found
        except Exception:
            pass

        return False, ""

    def _check_host_registered(self, registry_path: str) -> bool:
        """
        Check if the Native Messaging Host is registered in the Windows registry
        for the given browser registry path. Returns True if registered.
        """
        try:
            key_path = f"{registry_path}\\com.dlite.host"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except OSError:
            return False
        except Exception:
            return False

    def _check_extension_present(self, browser_info: dict) -> bool:
        r"""
        Check if the extension folder exists in the browser's profile directory.
        For Chromium browsers, extensions live under %LOCALAPPDATA%\<browser>\User Data\Default\Extensions\<id>.
        For Firefox, check the profiles directory for the extension ID.
        Returns True if detected.
        """
        ext_path = browser_info.get("ext_path_sub")
        if not ext_path:
            # Firefox — check profiles
            local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            profiles_base = os.path.join(local_app_data, "Mozilla", "Firefox", "Profiles")
            if os.path.isdir(profiles_base):
                for profile_dir in os.listdir(profiles_base):
                    ext_dir = os.path.join(profiles_base, profile_dir, "extensions")
                    if os.path.isdir(ext_dir):
                        for item in os.listdir(ext_dir):
                            if browser_info["extension_id"] in item:
                                return True
            return False
        else:
            local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            full_path = os.path.join(local_app_data, ext_path)
            return os.path.isdir(full_path)

    def _install_native_host(self, browser_info: dict):
        """
        Install/Reregister the Native Messaging Host for the selected browser.
        Steps:
          1. Write the host manifest JSON to native_host/ folder
          2. Register the manifest path in HKCU registry under the browser's key
          3. Show success/failure messagebox
        """
        host_dir = self._native_host_dir
        host_name = "com.dlite.host"
        ext_folder = browser_info["ext_folder"]
        registry_path = browser_info["registry_key"]
        extension_id = browser_info["extension_id"]

        # Build manifest
        manifest = {
            "name": host_name,
            "description": "DLite native messaging host",
            "type": "stdio",
            "path": os.path.join(host_dir, "host.bat"),
        }
        if ext_folder == "firefox":
            manifest["allowed_extensions"] = [extension_id]
        else:
            manifest["allowed_origins"] = [f"chrome-extension://{extension_id}/"]

        # Ensure host.bat exists
        bat_path = os.path.join(host_dir, "host.bat")
        if not os.path.isfile(bat_path):
            bat_content = f'@echo off\n"{self._python_exe}" -u "{os.path.join(host_dir, "host.py")}" %*\n'
            try:
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(bat_content)
            except OSError as e:
                QMessageBox.warning(self, "Error", f"Could not create host.bat: {e}")
                return

        # Write manifest JSON
        manifest_fn = browser_info.get("manifest_filename", f"{host_name}.{ext_folder}.json")
        manifest_path = os.path.join(host_dir, manifest_fn)
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except OSError as e:
            QMessageBox.warning(self, "Error", f"Could not write manifest: {e}")
            return

        # Register in registry
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{registry_path}\\{host_name}")
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
            winreg.CloseKey(key)
            QMessageBox.information(
                self,
                "Success",
                f"Native Messaging Host installed for {browser_info['name']}!\n\n"
                f"Next step: Load the extension in {browser_info['name']}'s developer mode.\n"
                f"Click 'Load Extension Instructions' for details."
            )
        except OSError as e:
            QMessageBox.warning(
                self,
                "Registration Failed",
                f"Could not register native host for {browser_info['name']}:\n{e}\n\n"
                f"Try running DLite as administrator."
            )

    def _show_extension_instructions(self, browser_info: dict):
        """
        Show step-by-step instructions on how to load the unpacked extension
        in the selected browser's developer mode.
        """
        ext_folder = browser_info["ext_folder"]
        ext_path = os.path.join(self._ext_dir, ext_folder)
        browser_name = browser_info["name"]

        if ext_folder == "chromium":
            load_text = (
                f"1. Open {browser_name} and go to: chrome://extensions\n"
                f"2. Enable <b>Developer mode</b> (toggle top-right)\n"
                f"3. Click <b>Load unpacked</b>\n"
                f"4. Navigate to this folder and select it:\n"
                f"   <code>{ext_path}</code>\n"
                f"5. The extension should appear named <b>DLite</b>\n"
                f"6. Make sure it's <b>enabled</b> (toggle on)"
            )
        else:  # Firefox
            load_text = (
                f"1. Open {browser_name} and go to: about:debugging#/runtime/this-firefox\n"
                f"2. Click <b>Load Temporary Add-on</b>\n"
                f"3. Navigate to this folder and select <b>manifest.json</b>:\n"
                f"   <code>{ext_path}</code>\n"
                f"4. The extension should appear named <b>DLite</b>\n"
                f"5. Note: Temporary add-ons are removed when Firefox restarts.\n"
                f"   For permanent install, the extension must be signed by Mozilla."
            )

        msg = QMessageBox(self)
        msg.setWindowTitle(f"Install Extension — {browser_name}")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(load_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def _browse_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", str(config.download_dir)
        )
        if dir_path:
            self.download_dir_input.setText(dir_path)

    def _save_and_accept(self):
        config.set("download_dir", self.download_dir_input.text())
        config.set("max_concurrent_downloads", self.max_concurrent_spin.value())
        config.set("max_segments", self.max_segments_spin.value())
        config.set("theme", self.theme_combo.currentText())
        config.set("language", self.language_combo.currentData())
        config.set("minimize_to_tray", self.minimize_tray_check.isChecked())
        config.set("auto_start_downloads", self.auto_start_check.isChecked())
        config.set("monitor_clipboard", self.clipboard_monitor_check.isChecked())
        config.set("notify_on_complete", self.notify_complete_check.isChecked())
        config.set("speed_limit_kbps", self.speed_limit_spin.value())
        config.set("chunk_size", self.chunk_size_spin.value() * 1024)
        config.set("retry_attempts", self.retry_spin.value())
        config.set("retry_delay_seconds", self.retry_delay_spin.value())
        config.set("native_host_port", self.port_spin.value())
        if self.user_agent_input.text().strip():
            config.set("user_agent", self.user_agent_input.text().strip())
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DLite - Download Manager")
        self.resize(1100, 750)
        self.setMinimumSize(800, 500)

        # Set app icon from official logo
        import os as _os
        self._icon_path = _os.path.join(_os.path.dirname(__file__), "..", "icons", "icon.png")
        if _os.path.exists(self._icon_path):
            self.setWindowIcon(QIcon(self._icon_path))

        self._row_of_task: dict[str, int] = {}
        self._last_sample: dict[str, tuple] = {}  # task_id -> (bytes, timestamp)
        self._auto_action = config.get("action_on_complete", "none")
        self._shutdown_dialog_active = False

        self._build_menu_bar()
        self._build_toolbar()
        self._build_central_widget()
        self._build_status_bar()
        self._build_tray()

        # Connect logging stdout thread-safely to GUI console log tab
        self.log_emitter = LogSignalEmitter()
        self.log_emitter.log_written.connect(self._append_log)
        self.log_handler = QtLogHandler(self.log_emitter)
        logging.getLogger().addHandler(self.log_handler)

        self.bridge = EngineBridge()
        self.bridge.task_added.connect(self._on_task_added)
        self.bridge.task_removed.connect(self._on_task_removed)
        self.bridge.task_updated.connect(self._on_task_updated)

        # Apply theme
        theme_name = config.get("theme", "dark")
        self.setStyleSheet(stylesheet_for(theme_name))
        self._current_theme = theme_name

        # Load existing tasks
        for task in queue_manager.tasks.values():
            self._add_row(task)
        self._update_categories()

        # Accept Drag and Drop (links, .txt batch files)
        self.setAcceptDrops(True)

        # Clipboard auto-capture monitoring
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_changed)
        self._last_clipboard_text = ""

        # Refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_rows)
        self.refresh_timer.start(500)

    # ─── Menu Bar ────────────────────────────────────
    def _build_menu_bar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        add_action = QAction("&Add URL...", self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self._add_download_dialog)
        file_menu.addAction(add_action)

        batch_pattern_action = QAction("&Batch Download (Pattern)...", self)
        batch_pattern_action.setShortcut("Ctrl+B")
        batch_pattern_action.triggered.connect(self._open_batch_pattern_dialog)
        file_menu.addAction(batch_pattern_action)

        file_menu.addSeparator()

        import_action = QAction("&Import URLs from file...", self)
        import_action.triggered.connect(self._import_urls)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self._quit_app)
        file_menu.addAction(quit_action)

        # Downloads menu
        dl_menu = menubar.addMenu("&Downloads")
        pause_all = QAction("Pause &All", self)
        pause_all.setShortcut("Ctrl+Shift+P")
        pause_all.triggered.connect(lambda: self._batch_action("pause"))
        dl_menu.addAction(pause_all)

        resume_all = QAction("Resume &All", self)
        resume_all.setShortcut("Ctrl+Shift+R")
        resume_all.triggered.connect(lambda: self._batch_action("resume"))
        dl_menu.addAction(resume_all)

        dl_menu.addSeparator()

        clear_completed = QAction("Clear &Completed", self)
        clear_completed.setShortcut("Ctrl+Shift+D")
        clear_completed.triggered.connect(self._clear_completed)
        dl_menu.addAction(clear_completed)

        dl_menu.addSeparator()

        scheduler_action = QAction("⏰ &Download Scheduler...", self)
        scheduler_action.triggered.connect(self._open_scheduler_dialog)
        dl_menu.addAction(scheduler_action)

        self.clipboard_menu_action = QAction("📋 Monitor &Clipboard for URLs", self)
        self.clipboard_menu_action.setCheckable(True)
        self.clipboard_menu_action.setChecked(config.get("monitor_clipboard", True))
        self.clipboard_menu_action.triggered.connect(self._toggle_clipboard_monitoring)
        dl_menu.addAction(self.clipboard_menu_action)

        dl_menu.addSeparator()

        auto_menu = dl_menu.addMenu("⚡ When All Downloads Finish")
        self._action_group = QActionGroup(self)
        self._action_group.setExclusive(True)

        actions_def = [
            ("none", "Do Nothing"),
            ("exit", "Exit DLite"),
            ("sleep", "Sleep Computer"),
            ("shutdown", "Shut Down Computer"),
        ]
        for act_key, act_label in actions_def:
            act = QAction(act_label, self)
            act.setCheckable(True)
            act.setChecked(self._auto_action == act_key)
            act.triggered.connect(lambda checked, k=act_key: self._set_auto_action(k))
            self._action_group.addAction(act)
            auto_menu.addAction(act)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About DLite", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ─── Toolbar ─────────────────────────────────────
    def _build_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        style = self.style()

        add_btn = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Add URL", self)
        add_btn.triggered.connect(self._add_download_dialog)
        toolbar.addAction(add_btn)

        batch_btn = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView), "Batch Pattern", self)
        batch_btn.setToolTip("Add Batch Download by Pattern (Ctrl+B)")
        batch_btn.triggered.connect(self._open_batch_pattern_dialog)
        toolbar.addAction(batch_btn)

        sched_btn = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), "Scheduler", self)
        sched_btn.setToolTip("Open Download Scheduler")
        sched_btn.triggered.connect(self._open_scheduler_dialog)
        toolbar.addAction(sched_btn)

        toolbar.addSeparator()

        pause_btn = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPause), "Pause", self)
        pause_btn.triggered.connect(self._pause_selected)
        toolbar.addAction(pause_btn)

        resume_btn = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "Resume", self)
        resume_btn.triggered.connect(self._resume_selected)
        toolbar.addAction(resume_btn)

        cancel_btn = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), "Cancel", self)
        cancel_btn.triggered.connect(self._cancel_selected)
        toolbar.addAction(cancel_btn)

        remove_btn = QAction(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Remove", self)
        remove_btn.triggered.connect(self._remove_selected)
        toolbar.addAction(remove_btn)

        toolbar.addSeparator()

        settings_btn = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Settings", self)
        settings_btn.triggered.connect(self._open_settings)
        toolbar.addAction(settings_btn)

        toolbar.addSeparator()

        # Search
        search_label = QLabel("Search:")
        toolbar.addWidget(search_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter downloads...")
        self.search_box.setFixedWidth(200)
        self.search_box.textChanged.connect(self._apply_search_filter)
        toolbar.addWidget(self.search_box)

    # ─── Central Widget ─────────────────────────────
    def _build_central_widget(self):
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Category sidebar
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(["Categories"])
        self.category_tree.setMaximumWidth(200)
        self.category_tree.setMinimumWidth(140)
        self.category_tree.setRootIsDecorated(True)

        # Right side layout: Splitted vertically between Table (top) and Info Tabs (bottom)
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Table widget container
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 180)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        table_layout.addWidget(self.table)

        # Bottom info panel
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setMinimumHeight(150)

        self.speed_graph = SpeedGraphWidget()
        self.bottom_tabs.addTab(self.speed_graph, "📊 Speed Graph")

        self.segments_progress = SegmentsProgressWidget()
        self.bottom_tabs.addTab(self.segments_progress, "⚡ Segment Connections")

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFont(QFont("Consolas", 9))
        self.bottom_tabs.addTab(self.log_text_edit, "💬 System Logs")

        right_splitter.addWidget(table_widget)
        right_splitter.addWidget(self.bottom_tabs)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)

        main_splitter.addWidget(self.category_tree)
        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

        self.setCentralWidget(main_splitter)

        # Populate category tree
        all_item = QTreeWidgetItem(["📂 All Downloads"])
        all_item.setData(0, Qt.ItemDataRole.UserRole, "all")
        self.category_tree.addTopLevelItem(all_item)

        cats = [
            ("📦 Archives", "archive"),
            ("🎵 Audio", "audio"),
            ("📄 Documents", "document"),
            ("📁 General", "general"),
            ("🖼️ Images", "image"),
            ("⚙️ Programs", "program"),
            ("🎬 Videos", "video"),
        ]
        for cat_name, cat_key in cats:
            item = QTreeWidgetItem([cat_name])
            item.setData(0, Qt.ItemDataRole.UserRole, cat_key)
            self.category_tree.addTopLevelItem(item)

        # Connect signals
        self.category_tree.currentItemChanged.connect(self._on_category_changed)
        self.category_tree.setCurrentItem(all_item)

    # ─── Status Bar ─────────────────────────────────
    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_dl_count = QLabel("Downloads: 0")
        self.status_speed = QLabel("Total Speed: 0 B/s")
        self.status_active = QLabel("Active: 0")

        self.status_bar.addWidget(self.status_dl_count)
        self.status_bar.addWidget(self.status_speed)
        self.status_scheduler = QLabel("")
        self.status_bar.addWidget(self.status_scheduler)
        self.status_bar.addPermanentWidget(self.status_active)

    # ─── System Tray ────────────────────────────────
    def _build_tray(self):
        tray_icon = QIcon(self._icon_path) if os.path.exists(self._icon_path) else self.style().standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon)
        self.tray = QSystemTrayIcon(tray_icon, self)
        menu = QMenu()
        show_action = menu.addAction("Show / Hide")
        show_action.triggered.connect(self._toggle_visible)

        menu.addSeparator()

        pause_all_tray = menu.addAction("Pause All")
        pause_all_tray.triggered.connect(lambda: self._batch_action("pause"))

        resume_all_tray = menu.addAction("Resume All")
        resume_all_tray.triggered.connect(lambda: self._batch_action("resume"))

        menu.addSeparator()
        self.tray_clipboard_action = menu.addAction("Monitor Clipboard")
        self.tray_clipboard_action.setCheckable(True)
        self.tray_clipboard_action.setChecked(config.get("monitor_clipboard", True))
        self.tray_clipboard_action.triggered.connect(self._toggle_clipboard_monitoring)

        sched_tray = menu.addAction("Download Scheduler...")
        sched_tray.triggered.connect(self._open_scheduler_dialog)

        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._quit_app)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.showNormal()
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick
            else None
        )
        self.tray.show()

    # ─── Log Handler Append ─────────────────────────
    def _append_log(self, msg):
        self.log_text_edit.append(msg)
        # Limit log display lines to prevent memory build-up
        doc = self.log_text_edit.document()
        if doc.blockCount() > 500:
            cursor = self.log_text_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 50)
            cursor.removeSelectedText()

    # ─── Actions / Dialogs ──────────────────────────
    def _quit_app(self):
        QApplication.instance().quit()

    def _toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def _add_download_dialog(self):
        """
        Open the simple "Add URL" dialog first to get URL/filename,
        then open the full DownloadConfirmationDialog so the user can
        review and configure the download before it starts.
        """
        dialog = AddDownloadDialog(self)
        if dialog.exec():
            url, filename = dialog.values()
            if url:
                # Open the full download confirmation dialog
                confirm = DownloadConfirmationDialog(
                    parent=self,
                    url=url,
                    filename=filename,
                    file_size=0,
                    mime="",
                    referrer="",
                    cookies="",
                )

                def on_confirmed(result_dict: dict):
                    task = queue_manager.add(
                        url=result_dict["url"],
                        filename=result_dict["filename"],
                        save_path=result_dict["save_path"],
                        category=result_dict["category"],
                        cookies=result_dict["cookies"],
                        referrer=result_dict["referrer"],
                        mime=result_dict["mime"],
                        total_size=result_dict["total_size"],
                        expected_checksum=result_dict.get("expected_checksum", ""),
                    )
                    # Apply user preferences
                    config.set("download_dir", result_dict["save_path"])
                    config.set("max_segments", result_dict["segments"])
                    config.set("speed_limit_kbps", result_dict["speed_limit_kbps"])
                    queue_manager.start(task.id)

                confirm.download_confirmed.connect(on_confirmed)
                result = confirm.exec()
                if result != QDialog.DialogCode.Accepted:
                    logging.getLogger("gui").info("[add-url] user canceled confirmation dialog")

    def _open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            new_theme = config.get("theme", "dark")
            if new_theme != self._current_theme:
                self._current_theme = new_theme
                self.setStyleSheet(stylesheet_for(new_theme))

    def _show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About DLite")
        dialog.setFixedSize(460, 520)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 24, 30, 24)

        # Logo
        import os as _os
        logo_path = _os.path.join(_os.path.dirname(__file__), "..", "icons", "icon256.png")
        if _os.path.exists(logo_path):
            from PyQt6.QtGui import QPixmap
            logo_label = QLabel()
            pixmap = QPixmap(logo_path).scaled(
                120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

        # Title
        title = QLabel("DLite")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        layout.addWidget(title)

        # Version
        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setFont(QFont("Segoe UI", 11))
        version.setStyleSheet("color: #8a8b91;")
        layout.addWidget(version)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #35363e;")
        layout.addWidget(sep)

        # Description
        desc = QLabel(
            "A modern, lightweight, open-source download manager.\n\n"
            "Features:\n"
            "  - Multi-segment parallel downloading\n"
            "  - Real-time speed graph & statistics\n"
            "  - Browser integration (Chrome/Firefox/Edge)\n"
            "  - Pause, resume & error recovery\n"
            "  - Dark and light themes"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignLeft)
        desc.setFont(QFont("Segoe UI", 10))
        layout.addWidget(desc)

        layout.addStretch()

        # Footer
        footer = QLabel("Built with Python & PyQt6\nMIT License")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #8a8b91; font-size: 10px;")
        layout.addWidget(footer)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    def _import_urls(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import URLs", "", "Text files (*.txt);;All files (*.*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        url = line.strip()
                        if url and not url.startswith("#"):
                            queue_manager.add(url)
            except OSError as e:
                QMessageBox.warning(self, "Error", f"Could not read file: {e}")

    # ─── Context Menu ───────────────────────────────
    def _show_context_menu(self, pos):
        menu = QMenu(self)

        ids = self._selected_task_ids()
        if not ids:
            return

        pause_action = menu.addAction("⏸ Pause")
        pause_action.triggered.connect(self._pause_selected)

        resume_action = menu.addAction("▶ Resume")
        resume_action.triggered.connect(self._resume_selected)

        cancel_action = menu.addAction("✕ Cancel")
        cancel_action.triggered.connect(self._cancel_selected)

        menu.addSeparator()

        open_folder = menu.addAction("📂 Open containing folder")
        open_folder.triggered.connect(lambda: self._open_file_location(ids[0]))

        open_file = menu.addAction("📄 Open file")
        open_file.triggered.connect(lambda: self._open_downloaded_file(ids[0]))

        if len(ids) == 1:
            task = queue_manager.tasks.get(ids[0])
            if task and task.status == DownloadStatus.COMPLETED and os.path.exists(task.dest_path):
                menu.addSeparator()
                checksum_action = menu.addAction("🛡️ Checksum & File Integrity...")
                checksum_action.triggered.connect(lambda: self._show_checksum_dialog(ids[0]))

        menu.addSeparator()

        remove_action = menu.addAction("🗑 Remove from list")
        remove_action.triggered.connect(self._remove_selected)

        delete_file = menu.addAction("⛔ Remove and delete file")
        delete_file.triggered.connect(lambda: self._remove_with_file(ids))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _show_checksum_dialog(self, task_id: str):
        task = queue_manager.tasks.get(task_id)
        if not task or not os.path.exists(task.dest_path):
            QMessageBox.warning(self, "Checksum", "Downloaded file not found on disk.")
            return
        from gui.checksum_dialog import ChecksumDialog
        dlg = ChecksumDialog(
            parent=self,
            filepath=task.dest_path,
            filename=task.filename,
            expected_hash=getattr(task, "expected_checksum", "") or "",
        )
        dlg.exec()

    def _on_cell_double_clicked(self, row, _col):
        for task_id, r in self._row_of_task.items():
            if r == row:
                task = queue_manager.tasks.get(task_id)
                if task and task.status == DownloadStatus.COMPLETED and os.path.exists(task.dest_path):
                    self._open_downloaded_file(task_id)
                elif task:
                    self._open_file_location(task_id)
                break

    def _open_file_location(self, task_id):
        task = queue_manager.tasks.get(task_id)
        if task:
            target = task.dest_path if os.path.exists(task.dest_path) else (task.save_path or str(config.download_dir))
            if os.path.exists(target):
                folder = target if os.path.isdir(target) else os.path.dirname(target)
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder])
                else:
                    subprocess.Popen(["xdg-open", folder])

    def _open_downloaded_file(self, task_id):
        task = queue_manager.tasks.get(task_id)
        if task and task.status == DownloadStatus.COMPLETED and os.path.exists(task.dest_path):
            if sys.platform == "win32":
                os.startfile(task.dest_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", task.dest_path])
            else:
                subprocess.Popen(["xdg-open", task.dest_path])

    def _set_auto_action(self, action: str):
        self._auto_action = action
        config.set("action_on_complete", action)

    def _check_auto_finish_action(self):
        if self._auto_action == "none" or self._shutdown_dialog_active:
            return
        has_active = any(
            t.status in (DownloadStatus.DOWNLOADING, DownloadStatus.CONNECTING, DownloadStatus.QUEUED)
            for t in queue_manager.tasks.values()
        )
        if not has_active and len(queue_manager.tasks) > 0:
            self._shutdown_dialog_active = True
            from gui.shutdown_dialog import ShutdownCountdownDialog
            dlg = ShutdownCountdownDialog(parent=self, action=self._auto_action, timeout_seconds=30)
            dlg.exec()
            self._shutdown_dialog_active = False
            self._set_auto_action("none")
            if hasattr(self, "_action_group"):
                for act in self._action_group.actions():
                    if act.text() == "Do Nothing":
                        act.setChecked(True)
                        break

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls_to_add = []
        if event.mimeData().hasUrls():
            for qurl in event.mimeData().urls():
                if qurl.isLocalFile():
                    local_path = qurl.toLocalFile()
                    if local_path.lower().endswith(".txt"):
                        try:
                            with open(local_path, "r", encoding="utf-8") as f:
                                for line in f:
                                    line_str = line.strip()
                                    if line_str and not line_str.startswith("#"):
                                        urls_to_add.append(line_str)
                        except Exception as e:
                            logging.getLogger("gui").warning("Failed reading dropped file: %s", e)
                else:
                    url_str = qurl.toString().strip()
                    if url_str.startswith(("http://", "https://", "ftp://")):
                        urls_to_add.append(url_str)
        elif event.mimeData().hasText():
            text = event.mimeData().text().strip()
            for line in text.splitlines():
                line = line.strip()
                if line.startswith(("http://", "https://", "ftp://")):
                    urls_to_add.append(line)

        if urls_to_add:
            if len(urls_to_add) == 1:
                from gui.add_download_dialog import DownloadConfirmationDialog
                url = urls_to_add[0]
                confirm = DownloadConfirmationDialog(parent=self, url=url)
                def on_confirmed(result_dict: dict):
                    task = queue_manager.add(
                        url=result_dict["url"],
                        filename=result_dict["filename"],
                        save_path=result_dict["save_path"],
                        category=result_dict["category"],
                        cookies=result_dict["cookies"],
                        referrer=result_dict["referrer"],
                        mime=result_dict["mime"],
                        total_size=result_dict["total_size"],
                        expected_checksum=result_dict.get("expected_checksum", ""),
                    )
                    config.set("download_dir", result_dict["save_path"])
                    config.set("max_segments", result_dict["segments"])
                    config.set("speed_limit_kbps", result_dict["speed_limit_kbps"])
                    queue_manager.start(task.id)
                confirm.download_confirmed.connect(on_confirmed)
                confirm.exec()
            else:
                count = 0
                for u in urls_to_add:
                    queue_manager.add(u)
                    count += 1
                QMessageBox.information(self, "Downloads Added", f"Added {count} downloads from dropped items.")
            event.acceptProposedAction()

    # ─── Selection Helpers ──────────────────────────
    def _selected_task_ids(self):
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        ids = []
        for task_id, row in self._row_of_task.items():
            if row in rows:
                ids.append(task_id)
        return ids

    def _batch_action(self, action: str):
        for task_id, task in list(queue_manager.tasks.items()):
            if action == "pause" and task.status in (
                DownloadStatus.QUEUED,
                DownloadStatus.CONNECTING,
                DownloadStatus.DOWNLOADING,
            ):
                queue_manager.pause(task_id)
            elif action == "resume" and task.status in (
                DownloadStatus.PAUSED,
                DownloadStatus.FAILED,
            ):
                queue_manager.resume(task_id)

    def _clear_completed(self):
        to_remove = [
            tid for tid, t in queue_manager.tasks.items()
            if t.status in (DownloadStatus.COMPLETED, DownloadStatus.CANCELED, DownloadStatus.FAILED)
        ]
        if to_remove:
            for tid in to_remove:
                queue_manager.remove(tid)

    def add_download_from_extension(self, url, filename="", referrer="", cookies=""):
        """
        Legacy path — kept for backward compatibility with older hosts.
        Creates the task QUEUED only (never auto-starts).
        """
        task = queue_manager.add(
            url, filename=filename, referrer=referrer, cookies=cookies,
        )
        return task

    def intercept_download_from_extension(
        self, url: str, filename: str = "",
        referrer: str = "", cookies: str = "",
        file_size: int = 0, mime: str = "",
    ):
        """
        The new interception pipeline (called from ExtensionListener).
        1. Creates a download task in QUEUED state
        2. Opens the DownloadConfirmationDialog (modal)
        3. If user confirms → saves the configured parameters → starts download
        4. If user cancels → removes the task from queue entirely

        This enforces the confirmation workflow: intercept → confirm → download.
        """
        import logging
        logger = logging.getLogger("main.intercept")
        logger.info(
            "[intercept] received: url=%s filename=%s size=%d mime=%s",
            url, filename, file_size, mime,
        )

        # Step 1: Create task QUEUED only
        task = queue_manager.add(
            url=url,
            filename=filename,
            referrer=referrer,
            cookies=cookies,
            total_size=file_size,
            mime=mime,
        )
        logger.info("[intercept] task created, id=%s status=QUEUED", task.id)

        # Step 2: Open confirmation dialog — transferred to main thread via invokeMethod
        dialog = DownloadConfirmationDialog(
            parent=self,
            url=url,
            filename=filename,
            file_size=file_size,
            mime=mime,
            referrer=referrer,
            cookies=cookies,
        )

        # Track our intent so we know whether to start or remove
        user_approved = [False]

        def on_confirmed(result_dict: dict):
            user_approved[0] = True
            logger.info("[intercept] user CONFIRMED download: %s", result_dict["filename"])

            # Apply user choices to the task
            task.filename = result_dict["filename"]
            task.save_path = result_dict["save_path"]
            task.category = result_dict["category"]
            task.cookies = result_dict["cookies"]
            task.referrer = result_dict["referrer"]
            task.mime = result_dict["mime"]
            task.total_size = result_dict["total_size"]
            task.expected_checksum = result_dict.get("expected_checksum", "")

            # Compute the full destination path
            save_folder = task.save_path or str(config.download_dir)
            os.makedirs(save_folder, exist_ok=True)
            candidate = os.path.join(save_folder, task.filename)
            if os.path.exists(candidate):
                base, ext = os.path.splitext(task.filename)
                counter = 1
                while os.path.exists(os.path.join(save_folder, f"{base} ({counter}){ext}")):
                    counter += 1
                task.filename = f"{base} ({counter}){ext}"
                candidate = os.path.join(save_folder, task.filename)
            task.dest_path = candidate
            logger.info("[intercept] dest_path resolved: %s", task.dest_path)

            # Update config defaults from user preferences
            config.set("download_dir", result_dict["save_path"])
            config.set("max_segments", result_dict["segments"])
            config.set("speed_limit_kbps", result_dict["speed_limit_kbps"])

            # Start the download
            queue_manager.start(task.id)
            logger.info("[intercept] download started: id=%s dest=%s", task.id, task.dest_path)

        dialog.download_confirmed.connect(on_confirmed)

        dialog.exec()

        if not user_approved[0]:
            # User canceled or closed dialog → remove task
            logger.info("[intercept] user CANCELED download, removing task: %s", task.id)
            queue_manager.remove(task.id)

    def _pause_selected(self):
        for task_id in self._selected_task_ids():
            queue_manager.pause(task_id)

    def _resume_selected(self):
        for task_id in self._selected_task_ids():
            queue_manager.resume(task_id)

    def _cancel_selected(self):
        for task_id in self._selected_task_ids():
            queue_manager.cancel(task_id)

    def _remove_selected(self):
        ids = self._selected_task_ids()
        if not ids:
            return
        reply = QMessageBox.question(
            self, "Remove downloads", f"Remove {len(ids)} download(s) from the list?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            for task_id in ids:
                queue_manager.remove(task_id)

    def _remove_with_file(self, ids):
        if not ids:
            return
        reply = QMessageBox.warning(
            self,
            "Delete files",
            f"Remove {len(ids)} download(s) AND delete the downloaded files?\nThis cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for task_id in ids:
                queue_manager.remove(task_id, delete_file=True)

    # ─── Table Management ──────────────────────────
    def _on_task_added(self, task):
        if not task.category or task.category == "general":
            task.category = guess_category(task.filename or task.url)
        self._add_row(task)
        self._update_categories()

    def _on_task_removed(self, task_id):
        row = self._row_of_task.pop(task_id, None)
        if row is not None:
            self.table.removeRow(row)
            self._reindex_rows()
        self._update_categories()
        self._update_status_bar()

    def _on_task_updated(self, task):
        self._update_status_bar()
        if task.status == DownloadStatus.COMPLETED:
            if config.get("notify_on_complete", True):
                self._notify_completed(task)
            if self._auto_action != "none":
                self._check_auto_finish_action()

    def _add_row(self, task):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._row_of_task[task.id] = row

        # File name
        name_item = QTableWidgetItem(task.filename or task.url)
        name_item.setToolTip(f"{task.url}\nSaved to: {task.dest_path}")
        self.table.setItem(row, 0, name_item)

        # Size
        self.table.setItem(row, 1, QTableWidgetItem(human_size(task.total_size)))

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(int(task.progress))
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%p%")
        self.table.setCellWidget(row, 2, progress_bar)

        # Speed placeholder
        self.table.setItem(row, 3, QTableWidgetItem("-"))

        # Time left placeholder
        self.table.setItem(row, 4, QTableWidgetItem("-"))

        # Status
        status_item = QTableWidgetItem(task.status.value.capitalize())
        self.table.setItem(row, 5, status_item)

        # Added date
        added = datetime.fromtimestamp(task.created_at).strftime("%Y-%m-%d %H:%M")
        self.table.setItem(row, 6, QTableWidgetItem(added))

        # Row height
        self.table.setRowHeight(row, 32)

    def _reindex_rows(self):
        self._row_of_task = {}
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            if name_item:
                for task_id, task in queue_manager.tasks.items():
                    if (task.filename or task.url) == name_item.text():
                        self._row_of_task[task_id] = row
                        break

    def _refresh_rows(self):
        scheduler.check()
        now = time.monotonic()
        total_speed = 0.0

        # Retrieve selected download task for segments visualizer tab
        selected_task = None
        selected_ids = self._selected_task_ids()
        if selected_ids:
            selected_task = queue_manager.tasks.get(selected_ids[0])

        if selected_task:
            self.segments_progress.set_task(selected_task)
        else:
            self.segments_progress.set_task(None)

        for task_id, row in list(self._row_of_task.items()):
            task = queue_manager.tasks.get(task_id)
            if task is None:
                continue

            # Update filename column in case it gets corrected by the engine
            self.table.item(row, 0).setText(task.filename or task.url)

            # Update size (may have been discovered after probing)
            self.table.item(row, 1).setText(human_size(task.total_size))

            # Update progress
            progress_bar = self.table.cellWidget(row, 2)
            if isinstance(progress_bar, QProgressBar):
                progress_bar.setValue(int(task.progress))

            # Update status
            status_text = task.status.value.capitalize()
            if task.status == DownloadStatus.FAILED and task.error_message:
                status_text += f" ({task.error_message})"
            self.table.item(row, 5).setText(status_text)

            # Calculate speed and ETA
            prev_bytes, prev_time = self._last_sample.get(task_id, (task.downloaded_bytes, now))
            elapsed = now - prev_time
            if elapsed > 0 and task.status == DownloadStatus.DOWNLOADING:
                speed = (task.downloaded_bytes - prev_bytes) / elapsed
                total_speed += speed
                remaining_bytes = max(task.total_size - task.downloaded_bytes, 0) if task.total_size > 0 else 0
                eta = remaining_bytes / speed if speed > 0 else -1
                self.table.item(row, 3).setText(f"{human_size(speed)}/s")
                self.table.item(row, 4).setText(human_time(eta))
            else:
                self.table.item(row, 3).setText("-")
                self.table.item(row, 4).setText("-")

            # Color the status cell
            status_colors = {
                DownloadStatus.COMPLETED: QColor("#4caf50"),
                DownloadStatus.DOWNLOADING: QColor("#2196f3"),
                DownloadStatus.CONNECTING: QColor("#ff9800"),
                DownloadStatus.PAUSED: QColor("#ff9800"),
                DownloadStatus.FAILED: QColor("#f44336"),
                DownloadStatus.CANCELED: QColor("#9e9e9e"),
                DownloadStatus.QUEUED: QColor("#9c27b0"),
            }
            color = status_colors.get(task.status, QColor("#ffffff"))
            self.table.item(row, 5).setForeground(color)

            self._last_sample[task_id] = (task.downloaded_bytes, now)

        # Update real-time speed graph widget
        self.speed_graph.add_sample(total_speed)

        # Update status bar using the calculated total speed
        self._update_status_bar(total_speed)

    def _update_status_bar(self, total_speed=0.0):
        total = len(queue_manager.tasks)
        active = sum(
            1 for t in queue_manager.tasks.values()
            if t.status in (DownloadStatus.DOWNLOADING, DownloadStatus.CONNECTING)
        )

        self.status_dl_count.setText(f"Downloads: {total}")
        self.status_speed.setText(f"Total Speed: {human_size(total_speed)}/s")
        self.status_active.setText(f"Active: {active}")
        if scheduler.is_enabled:
            summary = scheduler.get_status_summary()
            self.status_scheduler.setText(f" | ⏰ {summary}")
            self.status_scheduler.setStyleSheet("color: #38bdf8; font-weight: 500;")
        else:
            self.status_scheduler.setText("")

    def _apply_search_filter(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().lower()
            self.table.setRowHidden(row, text not in name)

    # ─── Category Filtering ────────────────────────
    def _on_category_changed(self, current, previous):
        if not current:
            return
        category_filter = current.data(0, Qt.ItemDataRole.UserRole)

        for row in range(self.table.rowCount()):
            # Find the task for this row
            task_category = "general"
            for task_id, r in self._row_of_task.items():
                if r == row:
                    task = queue_manager.tasks.get(task_id)
                    if task:
                        task_category = task.category or guess_category(task.filename or task.url)
                    break
            
            if category_filter == "all":
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, task_category != category_filter)

    def _update_categories(self):
        """Update category counts in the sidebar."""
        counts = {}
        for task in queue_manager.tasks.values():
            cat = task.category or guess_category(task.filename or task.url)
            counts[cat] = counts.get(cat, 0) + 1
        counts["all"] = len(queue_manager.tasks)

        for i in range(self.category_tree.topLevelItemCount()):
            item = self.category_tree.topLevelItem(i)
            cat_key = item.data(0, Qt.ItemDataRole.UserRole)
            cnt = counts.get(cat_key, 0)
            base_name = item.text(0).split(" (")[0]
            item.setText(0, f"{base_name} ({cnt})")

    # ─── Window Events ─────────────────────────────
    def closeEvent(self, event):
        if config.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "DLite",
                "Application minimized to tray. Double-click to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            event.accept()

    def _notify_completed(self, task):
        if hasattr(self, "tray") and self.tray.isVisible():
            title = t("notify_dl_completed", "Download Completed")
            desc = t("notify_dl_completed_desc", "has finished downloading.")
            self.tray.showMessage(
                title,
                f"{task.filename} ({human_size(task.total_size)}) {desc}",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )

    def _toggle_clipboard_monitoring(self, checked: bool):
        config.set("monitor_clipboard", checked)
        if hasattr(self, "clipboard_menu_action"):
            self.clipboard_menu_action.setChecked(checked)
        if hasattr(self, "tray_clipboard_action"):
            self.tray_clipboard_action.setChecked(checked)

    def _on_clipboard_changed(self):
        if not config.get("monitor_clipboard", True):
            return
        try:
            text = self.clipboard.text().strip()
            if not text or text == self._last_clipboard_text:
                return
            self._last_clipboard_text = text
            if is_downloadable_url(text):
                if config.get("clipboard_auto_open_dialog", True):
                    QTimer.singleShot(150, lambda: self._prompt_clipboard_download(text))
        except Exception as e:
            logging.getLogger("gui").debug("Clipboard monitoring exception: %s", e)

    def _prompt_clipboard_download(self, url: str):
        confirm = DownloadConfirmationDialog(parent=self, url=url)

        def on_confirmed(result_dict: dict):
            task = queue_manager.add(
                url=result_dict["url"],
                filename=result_dict["filename"],
                save_path=result_dict["save_path"],
                category=result_dict["category"],
                cookies=result_dict["cookies"],
                referrer=result_dict["referrer"],
                mime=result_dict["mime"],
                total_size=result_dict["total_size"],
                expected_checksum=result_dict.get("expected_checksum", ""),
            )
            config.set("download_dir", result_dict["save_path"])
            config.set("max_segments", result_dict["segments"])
            config.set("speed_limit_kbps", result_dict["speed_limit_kbps"])
            queue_manager.start(task.id)

        confirm.download_confirmed.connect(on_confirmed)
        confirm.exec()

    def _open_scheduler_dialog(self):
        dlg = SchedulerDialog(self)
        dlg.exec()
        self._update_status_bar()

    def _open_batch_pattern_dialog(self):
        dlg = BatchPatternDialog(self)
        dlg.exec()
