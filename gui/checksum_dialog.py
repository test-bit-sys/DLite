import os
try:
    import pyperclip
except ImportError:
    pyperclip = None
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QGroupBox,
)

from engine.checksum import calculate_file_hashes


class HashWorker(QThread):
    finished_hashes = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            hashes = calculate_file_hashes(self.filepath)
            self.finished_hashes.emit(hashes)
        except Exception as e:
            self.error.emit(str(e))


class ChecksumDialog(QDialog):
    """
    Dialog for computing and verifying cryptographic checksums (SHA-256, SHA-1, MD5).
    Features:
      - Asynchronous multi-hash calculation (non-blocking)
      - One-click copy for each hash
      - Real-time comparison input with instant match verification
    """

    def __init__(self, parent, filepath: str, filename: str = "", expected_hash: str = ""):
        super().__init__(parent)
        self.filepath = filepath
        self.filename = filename or os.path.basename(filepath)
        self.expected_hash = expected_hash
        self.calculated_hashes = {}

        self.setWindowTitle(f"File Integrity & Checksum — {self.filename}")
        self.resize(620, 480)
        self.setMinimumSize(540, 420)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowTitleHint
        )

        self._build_ui()
        self._apply_style()
        self._start_hash_calculation()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 16, 18, 16)

        # Header
        header = QHBoxLayout()
        icon_lbl = QLabel("🛡️")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header.addWidget(icon_lbl)

        info_col = QVBoxLayout()
        name_lbl = QLabel(self.filename)
        name_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #f0f2f5;")
        path_lbl = QLabel(self.filepath)
        path_lbl.setStyleSheet("font-size: 11px; color: #8ab4f8;")
        path_lbl.setWordWrap(True)
        info_col.addWidget(name_lbl)
        info_col.addWidget(path_lbl)
        header.addLayout(info_col)
        layout.addLayout(header)

        # Progress / Status
        self.status_lbl = QLabel("Calculating hashes in background...")
        self.status_lbl.setStyleSheet("color: #a0aec0; font-style: italic;")
        layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate pulse
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        # Hash values group
        hash_group = QGroupBox("Calculated Hashes")
        hash_layout = QVBoxLayout(hash_group)
        hash_layout.setSpacing(8)

        # SHA-256
        self.sha256_input = self._create_hash_row("SHA-256:", hash_layout)
        # SHA-1
        self.sha1_input = self._create_hash_row("SHA-1:", hash_layout)
        # MD5
        self.md5_input = self._create_hash_row("MD5:", hash_layout)

        layout.addWidget(hash_group)

        # Verification section
        verify_group = QGroupBox("Verify / Compare Checksum")
        verify_layout = QVBoxLayout(verify_group)

        comp_row = QHBoxLayout()
        comp_row.addWidget(QLabel("Expected Hash:"))
        self.verify_input = QLineEdit()
        self.verify_input.setPlaceholderText("Paste hash here to verify integrity...")
        if self.expected_hash:
            self.verify_input.setText(self.expected_hash)
        self.verify_input.textChanged.connect(self._check_match)
        comp_row.addWidget(self.verify_input)
        verify_layout.addLayout(comp_row)

        self.match_result_lbl = QLabel("")
        self.match_result_lbl.setStyleSheet("font-weight: bold; padding: 4px;")
        verify_layout.addWidget(self.match_result_lbl)

        layout.addWidget(verify_group)

        layout.addStretch()

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _create_hash_row(self, label_text: str, parent_layout: QVBoxLayout) -> QLineEdit:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(75)
        lbl.setStyleSheet("font-weight: bold; color: #cbd5e1;")
        row.addWidget(lbl)

        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setFont(QFont("Consolas", 10))
        edit.setStyleSheet("background-color: #1e2430; color: #00e5ff; border: 1px solid #334155; border-radius: 4px; padding: 4px;")
        row.addWidget(edit, 1)

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedWidth(60)
        copy_btn.clicked.connect(lambda: self._copy_hash(edit.text()))
        row.addWidget(copy_btn)

        parent_layout.addLayout(row)
        return edit

    def _copy_hash(self, text: str):
        if text:
            if pyperclip is not None:
                try:
                    pyperclip.copy(text)
                except Exception:
                    from PyQt6.QtWidgets import QApplication
                    QApplication.clipboard().setText(text)
            else:
                from PyQt6.QtWidgets import QApplication
                QApplication.clipboard().setText(text)
            self.status_lbl.setText("Copied hash to clipboard!")
            self.status_lbl.setStyleSheet("color: #10b981;")

    def _start_hash_calculation(self):
        if not os.path.isfile(self.filepath):
            self.status_lbl.setText("File does not exist or has been moved.")
            self.status_lbl.setStyleSheet("color: #ef4444;")
            self.progress_bar.setVisible(False)
            return

        self.worker = HashWorker(self.filepath)
        self.worker.finished_hashes.connect(self._on_hashes_ready)
        self.worker.error.connect(self._on_hash_error)
        self.worker.start()

    def _on_hashes_ready(self, hashes: dict):
        self.calculated_hashes = hashes
        self.progress_bar.setVisible(False)
        self.status_lbl.setText("Hashes calculated successfully.")
        self.status_lbl.setStyleSheet("color: #10b981;")

        self.sha256_input.setText(hashes.get("sha256", ""))
        self.sha1_input.setText(hashes.get("sha1", ""))
        self.md5_input.setText(hashes.get("md5", ""))

        self._check_match()

    def _on_hash_error(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.status_lbl.setText(f"Error calculating hash: {err_msg}")
        self.status_lbl.setStyleSheet("color: #ef4444;")

    def _check_match(self):
        target = self.verify_input.text().strip().lower()
        if not target:
            self.match_result_lbl.setText("")
            return

        if not self.calculated_hashes:
            self.match_result_lbl.setText("Waiting for hash calculation...")
            self.match_result_lbl.setStyleSheet("color: #94a3b8;")
            return

        sha256 = self.calculated_hashes.get("sha256", "")
        sha1 = self.calculated_hashes.get("sha1", "")
        md5 = self.calculated_hashes.get("md5", "")

        if target == sha256:
            self.match_result_lbl.setText("VERIFIED: Hash matches SHA-256 perfectly!")
            self.match_result_lbl.setStyleSheet("color: #10b981; font-weight: bold; background: #064e3b; border-radius: 4px;")
        elif target == sha1:
            self.match_result_lbl.setText("VERIFIED: Hash matches SHA-1 perfectly!")
            self.match_result_lbl.setStyleSheet("color: #10b981; font-weight: bold; background: #064e3b; border-radius: 4px;")
        elif target == md5:
            self.match_result_lbl.setText("VERIFIED: Hash matches MD5 perfectly!")
            self.match_result_lbl.setStyleSheet("color: #10b981; font-weight: bold; background: #064e3b; border-radius: 4px;")
        else:
            self.match_result_lbl.setText("MISMATCH: Provided hash does NOT match this file!")
            self.match_result_lbl.setStyleSheet("color: #f87171; font-weight: bold; background: #7f1d1d; border-radius: 4px;")

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #141822;
                color: #e2e8f0;
            }
            QGroupBox {
                border: 1px solid #2d3748;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #94a3b8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLineEdit {
                background-color: #1a202c;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
            }
            QLineEdit:focus {
                border-color: #00e5ff;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #00e5ff;
            }
        """)
