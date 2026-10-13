import subprocess
import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QApplication,
)


class ShutdownCountdownDialog(QDialog):
    """
    Countdown dialog triggered when all downloads complete if an auto-action
    (shutdown, sleep, exit) was configured by the user.
    """

    def __init__(self, parent, action: str = "shutdown", timeout_seconds: int = 30):
        super().__init__(parent)
        self.action = action  # "shutdown", "sleep", "exit"
        self.remaining = timeout_seconds
        self.timeout_total = timeout_seconds

        self.setWindowTitle("DLite — Action on Completion")
        self.setFixedSize(420, 240)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        self._build_ui()
        self._apply_style()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        action_names = {
            "shutdown": "shut down",
            "sleep": "go to sleep",
            "exit": "close DLite",
        }
        action_text = action_names.get(self.action, "shut down")

        # Title
        title_lbl = QLabel("All downloads completed!")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981;")
        layout.addWidget(title_lbl)

        # Message with countdown
        self.msg_lbl = QLabel(
            f"Your computer will {action_text} in {self.remaining} seconds."
        )
        self.msg_lbl.setStyleSheet("font-size: 13px; color: #e2e8f0;")
        self.msg_lbl.setWordWrap(True)
        layout.addWidget(self.msg_lbl)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, self.timeout_total)
        self.progress.setValue(self.remaining)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.now_btn = QPushButton("Execute Now")
        self.now_btn.clicked.connect(self._execute_action)
        btn_layout.addWidget(self.now_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #ef4444; color: white;")
        self.cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _tick(self):
        self.remaining -= 1
        self.progress.setValue(self.remaining)

        action_names = {
            "shutdown": "shut down",
            "sleep": "go to sleep",
            "exit": "close DLite",
        }
        action_text = action_names.get(self.action, "shut down")
        self.msg_lbl.setText(
            f"Your computer will {action_text} in {self.remaining} seconds."
        )

        if self.remaining <= 0:
            self.timer.stop()
            self._execute_action()

    def _cancel(self):
        self.timer.stop()
        self.reject()

    def _execute_action(self):
        self.timer.stop()
        self.accept()

        if self.action == "shutdown":
            if sys.platform == "win32":
                subprocess.Popen(["shutdown", "/s", "/t", "0"])
            elif sys.platform == "darwin":
                subprocess.Popen(["osascript", "-e", 'tell app "System Events" to shut down'])
            else:
                subprocess.Popen(["shutdown", "-h", "now"])
        elif self.action == "sleep":
            if sys.platform == "win32":
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            elif sys.platform == "darwin":
                subprocess.Popen(["pmset", "sleepnow"])
            else:
                subprocess.Popen(["systemctl", "suspend"])
        elif self.action == "exit":
            QApplication.quit()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QLabel {
                color: #f8fafc;
            }
            QProgressBar {
                background-color: #1e293b;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #00e5ff;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
