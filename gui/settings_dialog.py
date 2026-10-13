"""
DLite Settings Dialog
Production-quality settings UI for configuring download behavior, appearance,
browser integration, and application updates.
"""
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QGroupBox, QSpinBox, QFileDialog, QTabWidget,
    QWidget,
)

from engine.config import config, _config_dir
from engine.logger import get_logger

log = get_logger("gui.settings")

ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "icons")


class SettingsDialog(QDialog):
    """
    Comprehensive settings dialog for DLite.
    Organised into tabs: General, Downloads, Appearance, Browser, Advanced.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — DLite")
        self.setMinimumSize(620, 520)
        self.resize(680, 560)
        self.setModal(True)

        # Keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Return), self, self._on_save)
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self, self._on_save)
        QShortcut(Qt.Key.Key_Escape, self, self.reject)

        self._build_ui()
        self._load_current_settings()
        self._apply_styles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Title bar
        header = QHBoxLayout()
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()

        # Config folder info
        config_path = str(_config_dir())
        config_info = QLabel(f"Config folder: {config_path}")
        config_info.setStyleSheet("color: #8a8b91; font-size: 10px;")
        config_info.setWordWrap(True)
        header.addWidget(config_info)
        root.addLayout(header)

        # Tab widget
        self.tab_widget = QTabWidget()

        # Tab 1: General
        self.tab_widget.addTab(self._build_general_tab(), "  General  ")

        # Tab 2: Downloads
        self.tab_widget.addTab(self._build_downloads_tab(), "  Downloads  ")

        # Tab 3: Appearance
        self.tab_widget.addTab(self._build_appearance_tab(), "  Appearance  ")

        # Tab 4: Browser
        self.tab_widget.addTab(self._build_browser_tab(), "  Browser  ")

        # Tab 5: Advanced
        self.tab_widget.addTab(self._build_advanced_tab(), "  Advanced  ")

        root.addWidget(self.tab_widget)
        root.addStretch()

        # Button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setObjectName("cancelBtn")
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("  Save Settings  ")
        save_btn.clicked.connect(self._on_save)
        save_btn.setObjectName("saveBtn")
        save_btn.setDefault(True)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 16, 12, 16)

        # Startup
        startup_group = QGroupBox("Startup Behavior")
        startup_layout = QVBoxLayout(startup_group)
        self.chk_auto_start = QCheckBox("Start downloads automatically when added")
        startup_layout.addWidget(self.chk_auto_start)

        self.chk_minimize_tray = QCheckBox("Minimize to system tray when closing window")
        startup_layout.addWidget(self.chk_minimize_tray)
        layout.addWidget(startup_group)

        # Interface
        interface_group = QGroupBox("Interface")
        interface_layout = QVBoxLayout(interface_group)

        confirm_row = QHBoxLayout()
        self.chk_confirm_dialog = QCheckBox("Show confirmation dialog before starting download")
        self.chk_confirm_dialog.setChecked(True)
        confirm_row.addWidget(self.chk_confirm_dialog)
        interface_layout.addLayout(confirm_row)

        self.chk_show_splash = QCheckBox("Show splash screen on startup")
        self.chk_show_splash.setChecked(True)
        interface_layout.addWidget(self.chk_show_splash)

        layout.addWidget(interface_group)
        layout.addStretch()
        return tab

    def _build_downloads_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 16, 12, 16)

        # Download folder
        folder_group = QGroupBox("Download Location")
        folder_layout = QHBoxLayout(folder_group)
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("C:\\Users\\You\\Downloads\\DLite")
        folder_layout.addWidget(self.folder_input, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._choose_download_folder)
        folder_layout.addWidget(browse_btn)
        layout.addWidget(folder_group)

        # Concurrency
        perf_group = QGroupBox("Performance")
        perf_grid = QGridLayout(perf_group)
        perf_grid.setSpacing(8)
        perf_grid.setContentsMargins(12, 18, 12, 12)

        perf_grid.addWidget(QLabel("Max simultaneous downloads:"), 0, 0)
        self.spin_concurrent = QSpinBox()
        self.spin_concurrent.setRange(1, 20)
        self.spin_concurrent.setValue(3)
        perf_grid.addWidget(self.spin_concurrent, 0, 1)

        perf_grid.addWidget(QLabel("Segments per download:"), 1, 0)
        self.spin_segments = QSpinBox()
        self.spin_segments.setRange(1, 32)
        self.spin_segments.setValue(8)
        perf_grid.addWidget(self.spin_segments, 1, 1)

        perf_grid.addWidget(QLabel("Speed limit (0 = unlimited):"), 2, 0)
        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(0, 999999)
        self.spin_speed.setSuffix(" KB/s")
        self.spin_speed.setSpecialValueText("Unlimited")
        perf_grid.addWidget(self.spin_speed, 2, 1)

        layout.addWidget(perf_group)

        # Retry
        retry_group = QGroupBox("Error Recovery")
        retry_grid = QGridLayout(retry_group)
        retry_grid.setSpacing(8)
        retry_grid.setContentsMargins(12, 18, 12, 12)

        retry_grid.addWidget(QLabel("Maximum retry attempts:"), 0, 0)
        self.spin_retries = QSpinBox()
        self.spin_retries.setRange(1, 50)
        self.spin_retries.setValue(5)
        retry_grid.addWidget(self.spin_retries, 0, 1)

        retry_grid.addWidget(QLabel("Delay between retries:"), 1, 0)
        self.spin_retry_delay = QSpinBox()
        self.spin_retry_delay.setRange(1, 60)
        self.spin_retry_delay.setSuffix(" sec")
        self.spin_retry_delay.setValue(3)
        retry_grid.addWidget(self.spin_retry_delay, 1, 1)

        layout.addWidget(retry_group)
        layout.addStretch()
        return tab

    def _build_appearance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 16, 12, 16)

        # Theme
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Color theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("🌙  Dark (recommended)", "dark")
        self.theme_combo.addItem("☀️  Light", "light")
        theme_row.addWidget(self.theme_combo, 1)
        theme_layout.addLayout(theme_row)

        # Live preview note
        theme_note = QLabel("Theme changes apply immediately after saving. The dark theme is optimized for long sessions and reduces eye strain.")
        theme_note.setWordWrap(True)
        theme_note.setStyleSheet("color: #8a8b91; font-size: 10px; margin-top: 4px;")
        theme_layout.addWidget(theme_note)

        layout.addWidget(theme_group)

        # Font
        font_group = QGroupBox("Font")
        font_layout = QVBoxLayout(font_group)
        self.chk_system_font = QCheckBox("Use system default font (recommended)")
        self.chk_system_font.setChecked(True)
        font_layout.addWidget(self.chk_system_font)
        layout.addWidget(font_group)

        layout.addStretch()
        return tab

    def _build_browser_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 16, 12, 16)

        # Browser integration info
        info_group = QGroupBox("Browser Integration")
        info_layout = QVBoxLayout(info_group)

        info_text = QLabel(
            "DLite integrates with Chrome, Firefox, Brave, Edge, and any "
            "Chromium-based browser through a companion extension.\n\n"
            "The extension intercepts downloads and forwards them to DLite "
            "when it is running."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("font-size: 12px; line-height: 1.5;")
        info_layout.addWidget(info_text)

        # Native host port
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("TCP listener port:"))
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(config.get("native_host_port", 38271))
        port_row.addWidget(self.spin_port)
        port_row.addStretch()
        info_layout.addLayout(port_row)

        port_note = QLabel(
            "The native messaging host forwards intercepted downloads from your "
            "browser to this port on localhost. Install the companion extension "
            "from the official website."
        )
        port_note.setWordWrap(True)
        port_note.setStyleSheet("color: #8a8b91; font-size: 10px;")
        info_layout.addWidget(port_note)

        self.chk_browser_capture = QCheckBox("Enable browser download interception")
        self.chk_browser_capture.setChecked(True)
        self.chk_browser_capture.setStyleSheet("font-weight: 600; margin-top: 8px;")
        info_layout.addWidget(self.chk_browser_capture)

        layout.addWidget(info_group)
        layout.addStretch()
        return tab

    def _build_advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 16, 12, 16)

        # User agent
        ua_group = QGroupBox("HTTP Headers")
        ua_layout = QVBoxLayout(ua_group)

        ua_layout.addWidget(QLabel("User-Agent string:"))
        self.ua_input = QLineEdit()
        self.ua_input.setPlaceholderText("Mozilla/5.0 (Windows NT 10.0; Win64; x64)...")
        ua_layout.addWidget(self.ua_input)

        ua_note = QLabel(
            "Custom User-Agent sent with download requests. Some servers "
            "require specific user-agents to allow downloads."
        )
        ua_note.setWordWrap(True)
        ua_note.setStyleSheet("color: #8a8b91; font-size: 10px;")
        ua_layout.addWidget(ua_note)

        layout.addWidget(ua_group)

        # Chunk size
        chunk_group = QGroupBox("Download Tuning")
        chunk_grid = QGridLayout(chunk_group)
        chunk_grid.setSpacing(8)
        chunk_grid.setContentsMargins(12, 18, 12, 12)

        chunk_grid.addWidget(QLabel("Chunk size (affects memory/perf):"), 0, 0)
        self.chunk_combo = QComboBox()
        self.chunk_combo.addItem("128 KB (low memory)", 128 * 1024)
        self.chunk_combo.addItem("256 KB (balanced - recommended)", 256 * 1024)
        self.chunk_combo.addItem("512 KB (high throughput)", 512 * 1024)
        self.chunk_combo.addItem("1 MB (aggressive)", 1024 * 1024)
        self.chunk_combo.setCurrentIndex(1)
        chunk_grid.addWidget(self.chunk_combo, 0, 1)

        layout.addWidget(chunk_group)

        # Logging
        log_group = QGroupBox("Logging")
        log_layout = QVBoxLayout(log_group)
        self.chk_debug_log = QCheckBox("Enable debug-level logging (more verbose)")
        self.chk_debug_log.setStyleSheet("font-size: 11px;")
        log_layout.addWidget(self.chk_debug_log)

        log_note = QLabel(
            f"Log files are stored in: {_config_dir() / 'dlite.log'}\n"
            "They rotate automatically when they reach 2 MB."
        )
        log_note.setWordWrap(True)
        log_note.setStyleSheet("color: #8a8b91; font-size: 10px;")
        log_layout.addWidget(log_note)
        layout.addWidget(log_group)

        layout.addStretch()
        return tab

    def _load_current_settings(self):
        """Populate all controls with current config values."""
        self.chk_minimize_tray.setChecked(config.get("minimize_to_tray", True))
        self.chk_auto_start.setChecked(config.get("auto_start_downloads", True))
        self.chk_confirm_dialog.setChecked(True)  # Always enabled by default

        self.folder_input.setText(str(config.download_dir))
        self.spin_concurrent.setValue(config.get("max_concurrent_downloads", 3))
        self.spin_segments.setValue(config.get("max_segments", 8))
        self.spin_speed.setValue(config.get("speed_limit_kbps", 0))
        self.spin_retries.setValue(config.get("retry_attempts", 5))
        self.spin_retry_delay.setValue(config.get("retry_delay_seconds", 3))

        theme = config.get("theme", "dark")
        idx = self.theme_combo.findData(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        self.spin_port.setValue(config.get("native_host_port", 38271))
        self.chk_browser_capture.setChecked(True)

        self.ua_input.setText(config.get("user_agent", ""))

        chunk_value = config.get("chunk_size", 256 * 1024)
        idx = self.chunk_combo.findData(chunk_value)
        if idx >= 0:
            self.chunk_combo.setCurrentIndex(idx)

    def _choose_download_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose default download folder",
            self.folder_input.text().strip() or str(Path.home() / "Downloads"),
        )
        if folder:
            self.folder_input.setText(folder)

    def _on_save(self):
        """Persist all settings to disk and apply to running app."""
        changes = []

        # General
        config.set("minimize_to_tray", self.chk_minimize_tray.isChecked())
        config.set("auto_start_downloads", self.chk_auto_start.isChecked())

        # Downloads
        new_folder = self.folder_input.text().strip()
        if new_folder and new_folder != str(config.download_dir):
            os.makedirs(new_folder, exist_ok=True)
            config.set("download_dir", new_folder)
            changes.append(f"Download folder → {new_folder}")

        config.set("max_concurrent_downloads", self.spin_concurrent.value())
        config.set("max_segments", self.spin_segments.value())
        config.set("speed_limit_kbps", self.spin_speed.value())
        config.set("retry_attempts", self.spin_retries.value())
        config.set("retry_delay_seconds", self.spin_retry_delay.value())

        # Appearance
        new_theme = self.theme_combo.currentData()
        config.set("theme", new_theme)

        # Browser
        config.set("native_host_port", self.spin_port.value())

        # Advanced
        config.set("user_agent", self.ua_input.text().strip())
        config.set("chunk_size", self.chunk_combo.currentData())

        log.info("[settings] saved to %s", config.path)
        self.accept()


    def _apply_styles(self):
        """Apply consistent dark styling matching the main window."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1f24;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-family: "Segoe UI", sans-serif;
                font-size: 12px;
            }
            QTabWidget::pane {
                border: 1px solid #35363e;
                border-radius: 6px;
                background-color: #1a1b1e;
            }
            QTabBar::tab {
                background-color: #26272e;
                border: 1px solid #35363e;
                border-bottom: none;
                border-radius: 5px 5px 0 0;
                padding: 8px 18px;
                margin-right: 3px;
                color: #8a8b91;
                font-size: 11px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #1a1b1e;
                color: #e0e0e0;
                border-bottom: 2px solid #4CAF50;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2d2e36;
            }
            QGroupBox {
                border: 1px solid #35363e;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 16px;
                font-weight: 600;
                color: #cfcfcf;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
            QLineEdit {
                background-color: #2b2c33;
                border: 1px solid #40414a;
                border-radius: 4px;
                padding: 5px 8px;
                color: #e6e6e6;
                font-size: 11px;
                selection-background-color: #2a5e2e;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
            QComboBox {
                background-color: #2b2c33;
                border: 1px solid #40414a;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e6e6e6;
                font-size: 11px;
            }
            QComboBox QAbstractItemView {
                background-color: #26272e;
                border: 1px solid #3a3b44;
                selection-background-color: #2a5e2e;
                outline: none;
            }
            QSpinBox {
                background-color: #2b2c33;
                border: 1px solid #40414a;
                border-radius: 4px;
                padding: 3px 6px;
                color: #e6e6e6;
                font-size: 11px;
            }
            QCheckBox {
                color: #c0c6d0;
                font-size: 11px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #55565f;
                border-radius: 3px;
                background-color: #2b2c33;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QPushButton {
                padding: 6px 16px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: 500;
                font-family: "Segoe UI", sans-serif;
            }
            QPushButton#saveBtn {
                background-color: #4CAF50;
                border: 1px solid #6ABF4B;
                color: #ffffff;
            }
            QPushButton#saveBtn:hover {
                background-color: #5CBF60;
            }
            QPushButton#saveBtn:pressed {
                background-color: #388E3C;
            }
            QPushButton#cancelBtn {
                background-color: #34353d;
                border: 1px solid #45464f;
                color: #c0c4ce;
            }
            QPushButton#cancelBtn:hover {
                background-color: #3d3e47;
            }
        """)