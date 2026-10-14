"""
DLite Download Scheduler Dialog
Provides a modern UI for scheduling download starts, stops, and bandwidth throttling windows.
"""
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QCheckBox,
    QGroupBox, QSpinBox, QTimeEdit,
)

from engine.config import config
from engine.scheduler import scheduler, parse_time_str


class SchedulerDialog(QDialog):
    """
    Dialog for configuring automated download scheduling and time-based bandwidth limits.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Scheduler — DLite")
        self.setMinimumSize(540, 520)
        self.setModal(True)

        QShortcut(QKeySequence(Qt.Key.Key_Return), self, self._on_save)
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self, self._on_save)
        QShortcut(Qt.Key.Key_Escape, self, self.reject)

        self._build_ui()
        self._load_settings()
        self._apply_styles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("⏰ Download Scheduler")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        desc = QLabel(
            "Automate when DLite downloads files, limit bandwidth during peak hours, "
            "and perform system actions upon completion."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 4px;")
        root.addWidget(desc)

        # Master toggle
        self.chk_master = QCheckBox("Enable Download Scheduler")
        self.chk_master.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        self.chk_master.toggled.connect(self._update_enabled_states)
        root.addWidget(self.chk_master)

        # ── 1. Execution Times ───────────────────────────────────────
        times_group = QGroupBox("Queue Timing")
        times_layout = QGridLayout(times_group)
        times_layout.setSpacing(10)
        times_layout.setContentsMargins(14, 16, 14, 14)

        self.chk_start = QCheckBox("Start / Resume queue at:")
        self.time_start = QTimeEdit()
        self.time_start.setDisplayFormat("HH:mm")
        self.time_start.setTime(QTime(2, 0))
        times_layout.addWidget(self.chk_start, 0, 0)
        times_layout.addWidget(self.time_start, 0, 1)

        self.chk_stop = QCheckBox("Pause queue at:")
        self.time_stop = QTimeEdit()
        self.time_stop.setDisplayFormat("HH:mm")
        self.time_stop.setTime(QTime(7, 0))
        times_layout.addWidget(self.chk_stop, 1, 0)
        times_layout.addWidget(self.time_stop, 1, 1)

        root.addWidget(times_group)

        # ── 2. Bandwidth Throttling Window ───────────────────────────
        throttle_group = QGroupBox("Bandwidth Throttling Window")
        throttle_layout = QGridLayout(throttle_group)
        throttle_layout.setSpacing(10)
        throttle_layout.setContentsMargins(14, 16, 14, 14)

        self.chk_throttle = QCheckBox("Throttle download speed during specific hours")
        self.chk_throttle.toggled.connect(self._update_throttle_states)
        throttle_layout.addWidget(self.chk_throttle, 0, 0, 1, 2)

        throttle_layout.addWidget(QLabel("Throttling Start:"), 1, 0)
        self.time_throttle_start = QTimeEdit()
        self.time_throttle_start.setDisplayFormat("HH:mm")
        self.time_throttle_start.setTime(QTime(9, 0))
        throttle_layout.addWidget(self.time_throttle_start, 1, 1)

        throttle_layout.addWidget(QLabel("Throttling End:"), 2, 0)
        self.time_throttle_end = QTimeEdit()
        self.time_throttle_end.setDisplayFormat("HH:mm")
        self.time_throttle_end.setTime(QTime(18, 0))
        throttle_layout.addWidget(self.time_throttle_end, 2, 1)

        throttle_layout.addWidget(QLabel("Speed limit during window:"), 3, 0)
        self.spin_throttle_rate = QSpinBox()
        self.spin_throttle_rate.setRange(10, 100000)
        self.spin_throttle_rate.setValue(500)
        self.spin_throttle_rate.setSuffix(" KB/s")
        throttle_layout.addWidget(self.spin_throttle_rate, 3, 1)

        root.addWidget(throttle_group)

        # ── 3. Post-completion Action ────────────────────────────────
        action_group = QGroupBox("Completion Action")
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(14, 14, 14, 14)

        action_layout.addWidget(QLabel("When all scheduled downloads finish:"))
        self.combo_action = QComboBox()
        self.combo_action.addItem("Do Nothing", "none")
        self.combo_action.addItem("Exit DLite", "exit")
        self.combo_action.addItem("Sleep Computer", "sleep")
        self.combo_action.addItem("Shut Down Computer", "shutdown")
        action_layout.addWidget(self.combo_action, 1)

        root.addWidget(action_group)
        root.addStretch()

        # ── Buttons ──────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)

        root.addLayout(btn_layout)

    def _load_settings(self):
        self.chk_master.setChecked(bool(config.get("scheduler_enabled", False)))

        self.chk_start.setChecked(bool(config.get("scheduler_start_enabled", False)))
        try:
            st = parse_time_str(config.get("scheduler_start_time", "02:00"))
            self.time_start.setTime(QTime(st.hour, st.minute))
        except Exception:
            pass

        self.chk_stop.setChecked(bool(config.get("scheduler_stop_enabled", False)))
        try:
            sp = parse_time_str(config.get("scheduler_stop_time", "07:00"))
            self.time_stop.setTime(QTime(sp.hour, sp.minute))
        except Exception:
            pass

        self.chk_throttle.setChecked(bool(config.get("scheduler_throttle_enabled", False)))
        try:
            ts = parse_time_str(config.get("scheduler_throttle_start", "09:00"))
            self.time_throttle_start.setTime(QTime(ts.hour, ts.minute))
        except Exception:
            pass

        try:
            te = parse_time_str(config.get("scheduler_throttle_end", "18:00"))
            self.time_throttle_end.setTime(QTime(te.hour, te.minute))
        except Exception:
            pass

        self.spin_throttle_rate.setValue(int(config.get("scheduler_throttle_rate_kbps", 500)))

        # Action on complete
        act = config.get("scheduler_action_on_complete", "none")
        idx = self.combo_action.findData(act)
        if idx >= 0:
            self.combo_action.setCurrentIndex(idx)

        self._update_enabled_states(self.chk_master.isChecked())
        self._update_throttle_states(self.chk_throttle.isChecked())

    def _update_enabled_states(self, enabled: bool):
        self.chk_start.setEnabled(enabled)
        self.time_start.setEnabled(enabled and self.chk_start.isChecked())
        self.chk_stop.setEnabled(enabled)
        self.time_stop.setEnabled(enabled and self.chk_stop.isChecked())
        self.chk_throttle.setEnabled(enabled)
        self._update_throttle_states(enabled and self.chk_throttle.isChecked())
        self.combo_action.setEnabled(enabled)

    def _update_throttle_states(self, enabled: bool):
        master = self.chk_master.isChecked()
        active = master and enabled
        self.time_throttle_start.setEnabled(active)
        self.time_throttle_end.setEnabled(active)
        self.spin_throttle_rate.setEnabled(active)

    def _on_save(self):
        config.set("scheduler_enabled", self.chk_master.isChecked())
        config.set("scheduler_start_enabled", self.chk_start.isChecked())
        config.set("scheduler_start_time", self.time_start.time().toString("HH:mm"))
        config.set("scheduler_stop_enabled", self.chk_stop.isChecked())
        config.set("scheduler_stop_time", self.time_stop.time().toString("HH:mm"))
        config.set("scheduler_throttle_enabled", self.chk_throttle.isChecked())
        config.set("scheduler_throttle_start", self.time_throttle_start.time().toString("HH:mm"))
        config.set("scheduler_throttle_end", self.time_throttle_end.time().toString("HH:mm"))
        config.set("scheduler_throttle_rate_kbps", self.spin_throttle_rate.value())
        config.set("scheduler_action_on_complete", self.combo_action.currentData())

        # Trigger scheduler check immediately
        scheduler.check()
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
                margin-top: 12px;
                padding-top: 14px;
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
            QTimeEdit, QSpinBox, QComboBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                color: #f8fafc;
                min-height: 24px;
            }
            QTimeEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #38bdf8;
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
            QCheckBox {
                color: #f1f5f9;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
        """)
