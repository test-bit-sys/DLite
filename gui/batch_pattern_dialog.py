"""
DLite Batch Pattern Download Dialog
Allows users to generate and queue batches of numbered or lettered URLs using range patterns.
"""
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QGroupBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox,
)

from engine.config import config
from engine.pattern_generator import expand_pattern, extract_filename_from_url
from engine.queue_manager import queue_manager


class BatchPatternDialog(QDialog):
    """
    Dialog for generating sequences of downloads using URL patterns (e.g. part_[01-20].zip).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Download by Pattern — DLite")
        self.setMinimumSize(680, 520)
        self.resize(720, 560)
        self.setModal(True)

        self._generated_urls: list[str] = []

        QShortcut(QKeySequence(Qt.Key.Key_Return), self, self._on_generate)
        QShortcut(Qt.Key.Key_Escape, self, self.reject)

        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("🔢 Batch Pattern Download")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        # Pattern Input Group
        pat_group = QGroupBox("Pattern Definition")
        pat_layout = QVBoxLayout(pat_group)
        pat_layout.setSpacing(8)

        pat_row = QHBoxLayout()
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("https://example.com/files/part_[01-20].zip")
        pat_row.addWidget(self.pattern_input, 1)

        self.btn_preview = QPushButton("Generate Preview")
        self.btn_preview.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold;")
        self.btn_preview.clicked.connect(self._on_generate)
        pat_row.addWidget(self.btn_preview)
        pat_layout.addLayout(pat_row)

        syntax_hint = QLabel(
            "<b>Supported Wildcards:</b> <code>[01-20]</code> (zero-padded numbers), "
            "<code>[1-50:2]</code> (with step), <code>[a-z]</code> or <code>[A-Z]</code> (letters)."
        )
        syntax_hint.setTextFormat(Qt.TextFormat.RichText)
        syntax_hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        pat_layout.addWidget(syntax_hint)

        root.addWidget(pat_group)

        # Preview Table
        preview_group = QGroupBox("Generated Downloads Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setSpacing(6)

        self.preview_count_label = QLabel("No URLs generated yet.")
        self.preview_count_label.setStyleSheet("color: #38bdf8; font-weight: 500;")
        preview_layout.addWidget(self.preview_count_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["#", "File Name", "Generated URL"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        preview_layout.addWidget(self.table)
        root.addWidget(preview_group, 1)

        # Destination & Category Options
        opt_group = QGroupBox("Download Destination & Options")
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setSpacing(8)

        dest_row = QHBoxLayout()
        dest_row.addWidget(QLabel("Save Folder:"))
        self.save_folder_input = QLineEdit(str(config.download_dir))
        dest_row.addWidget(self.save_folder_input, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._on_browse)
        dest_row.addWidget(btn_browse)
        opt_layout.addLayout(dest_row)

        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["general", "video", "audio", "document", "archive", "program", "image"])
        cat_row.addWidget(self.category_combo)

        cat_row.addSpacing(20)
        self.chk_start_now = QCheckBox("Start downloading immediately")
        self.chk_start_now.setChecked(True)
        cat_row.addWidget(self.chk_start_now)
        cat_row.addStretch()

        opt_layout.addLayout(cat_row)
        root.addWidget(opt_group)

        # Bottom Buttons
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(self.cancel_btn)

        self.add_btn = QPushButton("Add All to Queue")
        self.add_btn.setStyleSheet("background-color: #10b981; color: white; font-weight: bold;")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self._on_add_all)
        bottom_row.addWidget(self.add_btn)

        root.addLayout(bottom_row)

    def _on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_folder_input.text())
        if folder:
            self.save_folder_input.setText(folder)

    def _on_generate(self):
        pattern = self.pattern_input.text().strip()
        if not pattern:
            return

        try:
            urls = expand_pattern(pattern)
            if not urls:
                QMessageBox.warning(self, "Invalid Pattern", "Could not expand pattern into any valid URLs.")
                return

            self._generated_urls = urls
            self.table.setRowCount(len(urls))
            for idx, url in enumerate(urls, 1):
                fn = extract_filename_from_url(url)
                self.table.setItem(idx - 1, 0, QTableWidgetItem(str(idx)))
                self.table.setItem(idx - 1, 1, QTableWidgetItem(fn))
                self.table.setItem(idx - 1, 2, QTableWidgetItem(url))

            self.preview_count_label.setText(f"Generated {len(urls)} URLs ready to queue.")
            self.add_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Pattern Error", f"Error generating batch URLs:\n{e}")

    def _on_add_all(self):
        if not self._generated_urls:
            return

        save_path = self.save_folder_input.text().strip() or str(config.download_dir)
        os.makedirs(save_path, exist_ok=True)
        cat = self.category_combo.currentText()
        auto_start = self.chk_start_now.isChecked()

        queued_tasks = []
        for url in self._generated_urls:
            fn = extract_filename_from_url(url)
            task = queue_manager.add(
                url=url,
                filename=fn,
                save_path=save_path,
                category=cat,
            )
            queued_tasks.append(task)
            if auto_start:
                queue_manager.start(task.id)

        QMessageBox.information(
            self,
            "Batch Added",
            f"Successfully added {len(queued_tasks)} downloads to the queue!",
        )
        self.accept()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: 600;
                color: #e2e8f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #38bdf8;
            }
            QLabel {
                color: #cbd5e1;
            }
            QLineEdit, QComboBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px 8px;
                color: #f8fafc;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #38bdf8;
            }
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                gridline-color: #334155;
            }
            QTableWidget::item:selected {
                background-color: #0284c7;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #334155;
                font-weight: bold;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
                border-color: #1e293b;
            }
            QCheckBox {
                color: #f1f5f9;
                spacing: 8px;
            }
        """)
