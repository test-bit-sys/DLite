# ──────────────────────────────────────────────────
# DLite Theme System
# Modern, polished dark & light themes inspired by
# professional download managers.
#
# Brand Palette (from official logo):
#   Primary Green:  #4CAF50 / #6ABF4B
#   Accent Blue:    #1E88D0
#   Dark Navy:      #1A2A3A
# ──────────────────────────────────────────────────

DARK = """
/* === Global === */
QMainWindow {
    background-color: #1a1b1e;
}
QWidget {
    background-color: #1a1b1e;
    color: #e0e0e0;
    font-family: "Segoe UI", "SF Pro Display", system-ui, sans-serif;
    font-size: 13px;
}

/* === Menu Bar === */
QMenuBar {
    background-color: #202124;
    border-bottom: 1px solid #2d2e33;
    padding: 2px 0;
    color: #e0e0e0;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
    margin: 2px 2px;
}
QMenuBar::item:selected {
    background-color: #353740;
}
QMenu {
    background-color: #26272e;
    border: 1px solid #3a3b44;
    border-radius: 6px;
    padding: 4px 0;
}
QMenu::item {
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
    margin: 1px 4px;
}
QMenu::item:selected {
    background-color: #2a5e2e;
}
QMenu::separator {
    height: 1px;
    background-color: #35363e;
    margin: 4px 8px;
}

/* === Toolbar === */
QToolBar {
    background-color: #202124;
    border: none;
    border-bottom: 1px solid #2d2e33;
    spacing: 4px;
    padding: 4px 8px;
}
QToolBar QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 10px;
    color: #e0e0e0;
}
QToolBar QToolButton:hover {
    background-color: #353740;
    border-color: #45464f;
}
QToolBar QToolButton:pressed {
    background-color: #2a2b31;
}

/* === Tree Widget (Category Sidebar) === */
QTreeWidget {
    background-color: #1e1f24;
    border: none;
    border-right: 1px solid #2d2e33;
    color: #cfcfcf;
    outline: none;
}
QTreeWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 4px;
}
QTreeWidget::item:selected {
    background-color: #2e6b32;
    color: #ffffff;
}
QTreeWidget::item:hover:!selected {
    background-color: #2a2b31;
}
QHeaderView::section {
    background-color: #1e1f24;
    color: #8a8b91;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #2d2e33;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}

/* === Table (Downloads) === */
QTableWidget {
    background-color: #1e1f24;
    alternate-background-color: #212228;
    gridline-color: transparent;
    border: none;
    outline: none;
    selection-background-color: #2a5e2e;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #282930;
}
QTableWidget::item:selected {
    background-color: #2e6b32;
    color: #ffffff;
}

/* === Progress Bar === */
QProgressBar {
    border: 1px solid #35363e;
    border-radius: 4px;
    background-color: #2b2c33;
    text-align: center;
    color: #e0e0e0;
    font-size: 11px;
    height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #4CAF50,
        stop: 0.5 #6ABF4B,
        stop: 1 #4CAF50
    );
    border-radius: 4px;
}

/* === Buttons === */
QPushButton {
    background-color: #34353d;
    border: 1px solid #45464f;
    border-radius: 5px;
    padding: 7px 16px;
    color: #e0e0e0;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #3d3e47;
    border-color: #55565f;
}
QPushButton:pressed {
    background-color: #2a2b31;
}
QPushButton:default {
    background-color: #4CAF50;
    border-color: #6ABF4B;
    color: #ffffff;
}
QPushButton:default:hover {
    background-color: #5CBF60;
}

/* === Input Fields === */
QLineEdit, QTextEdit {
    background-color: #2b2c33;
    border: 1px solid #40414a;
    border-radius: 5px;
    padding: 7px 10px;
    color: #e6e6e6;
    selection-background-color: #2a5e2e;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #4CAF50;
}

/* === Spin Box & Combo Box === */
QSpinBox, QComboBox {
    background-color: #2b2c33;
    border: 1px solid #40414a;
    border-radius: 5px;
    padding: 5px 8px;
    color: #e6e6e6;
}
QSpinBox::up-button, QSpinBox::down-button,
QComboBox::drop-down {
    background-color: #35363e;
    border: none;
    border-radius: 3px;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #26272e;
    border: 1px solid #3a3b44;
    selection-background-color: #2a5e2e;
    outline: none;
}

/* === Scrollbar === */
QScrollBar:vertical {
    background: #1e1f24;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #45464f;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #55565f;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #1e1f24;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #45464f;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* === Tab Widget === */
QTabWidget::pane {
    border: 1px solid #35363e;
    border-radius: 6px;
    background-color: #1e1f24;
}
QTabBar::tab {
    background-color: #26272e;
    border: 1px solid #35363e;
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    padding: 8px 20px;
    margin-right: 3px;
    color: #8a8b91;
}
QTabBar::tab:selected {
    background-color: #1e1f24;
    color: #e0e0e0;
    border-bottom: 2px solid #4CAF50;
}
QTabBar::tab:hover:!selected {
    background-color: #2d2e36;
}

/* === Check Box === */
QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #55565f;
    border-radius: 3px;
    background-color: #2b2c33;
}
QCheckBox::indicator:checked {
    background-color: #4CAF50;
    border-color: #4CAF50;
}

/* === Status Bar === */
QStatusBar {
    background-color: #202124;
    border-top: 1px solid #2d2e33;
    color: #8a8b91;
    padding: 4px 8px;
    font-size: 12px;
}

/* === Splitter === */
QSplitter::handle {
    background-color: #2d2e33;
    width: 1px;
}

/* === Group Box === */
QGroupBox {
    border: 1px solid #35363e;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 18px;
    font-weight: 600;
    color: #cfcfcf;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* === Dialog === */
QDialog {
    background-color: #1e1f24;
    color: #e0e0e0;
}

/* === ToolTip === */
QToolTip {
    background-color: #353740;
    border: 1px solid #45464f;
    border-radius: 4px;
    padding: 4px 8px;
    color: #e0e0e0;
}

/* === Label === */
QLabel {
    color: #e0e0e0;
}
"""

LIGHT = """
/* === Global === */
QMainWindow {
    background-color: #f0f2f5;
}
QWidget {
    background-color: #f0f2f5;
    color: #1a1a1a;
    font-family: "Segoe UI", "SF Pro Display", system-ui, sans-serif;
    font-size: 13px;
}

/* === Menu Bar === */
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    padding: 2px 0;
    color: #333333;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
    margin: 2px 2px;
}
QMenuBar::item:selected {
    background-color: #e8e8e8;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #d8d8d8;
    border-radius: 6px;
    padding: 4px 0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
QMenu::item {
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
    margin: 1px 4px;
}
QMenu::item:selected {
    background-color: #e0f5e1;
    color: #2e7d32;
}
QMenu::separator {
    height: 1px;
    background-color: #e0e0e0;
    margin: 4px 8px;
}

/* === Toolbar === */
QToolBar {
    background-color: #ffffff;
    border: none;
    border-bottom: 1px solid #dcdcdc;
    spacing: 4px;
    padding: 4px 8px;
}
QToolBar QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 10px;
    color: #333333;
}
QToolBar QToolButton:hover {
    background-color: #f0f0f0;
    border-color: #d0d0d0;
}
QToolBar QToolButton:pressed {
    background-color: #e0e0e0;
}

/* === Tree Widget (Category Sidebar) === */
QTreeWidget {
    background-color: #ffffff;
    border: none;
    border-right: 1px solid #e0e0e0;
    color: #333333;
    outline: none;
}
QTreeWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 4px;
}
QTreeWidget::item:selected {
    background-color: #e0f5e1;
    color: #2e7d32;
}
QTreeWidget::item:hover:!selected {
    background-color: #f5f5f5;
}
QHeaderView::section {
    background-color: #ffffff;
    color: #777777;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #e0e0e0;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}

/* === Table (Downloads) === */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #fafafa;
    gridline-color: transparent;
    border: none;
    outline: none;
    selection-background-color: #e0f5e1;
    selection-color: #1a1a1a;
}
QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #eeeeee;
}
QTableWidget::item:selected {
    background-color: #c8e6c9;
    color: #1a1a1a;
}

/* === Progress Bar === */
QProgressBar {
    border: 1px solid #dcdcdc;
    border-radius: 4px;
    background-color: #f5f5f5;
    text-align: center;
    color: #333333;
    font-size: 11px;
    height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #4CAF50,
        stop: 0.5 #6ABF4B,
        stop: 1 #4CAF50
    );
    border-radius: 4px;
}

/* === Buttons === */
QPushButton {
    background-color: #f5f5f5;
    border: 1px solid #d0d0d0;
    border-radius: 5px;
    padding: 7px 16px;
    color: #333333;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #e8e8e8;
    border-color: #c0c0c0;
}
QPushButton:pressed {
    background-color: #dcdcdc;
}
QPushButton:default {
    background-color: #4CAF50;
    border-color: #388E3C;
    color: #ffffff;
}
QPushButton:default:hover {
    background-color: #5CBF60;
}

/* === Input Fields === */
QLineEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 5px;
    padding: 7px 10px;
    color: #333333;
    selection-background-color: #c8e6c9;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #4CAF50;
}

/* === Spin Box & Combo Box === */
QSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 5px;
    padding: 5px 8px;
    color: #333333;
}
QSpinBox::up-button, QSpinBox::down-button,
QComboBox::drop-down {
    background-color: #f0f0f0;
    border: none;
    border-radius: 3px;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    selection-background-color: #e0f5e1;
    outline: none;
}

/* === Scrollbar === */
QScrollBar:vertical {
    background: #f5f5f5;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #d0d0d0;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #b0b0b0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f5f5f5;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #d0d0d0;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* === Tab Widget === */
QTabWidget::pane {
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #f0f0f0;
    border: 1px solid #dcdcdc;
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    padding: 8px 20px;
    margin-right: 3px;
    color: #777777;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1a1a1a;
    border-bottom: 2px solid #4CAF50;
}
QTabBar::tab:hover:!selected {
    background-color: #e8e8e8;
}

/* === Check Box === */
QCheckBox {
    color: #333333;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #c0c0c0;
    border-radius: 3px;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #4CAF50;
    border-color: #4CAF50;
}

/* === Status Bar === */
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e0e0e0;
    color: #777777;
    padding: 4px 8px;
    font-size: 12px;
}

/* === Splitter === */
QSplitter::handle {
    background-color: #e0e0e0;
    width: 1px;
}

/* === Group Box === */
QGroupBox {
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 18px;
    font-weight: 600;
    color: #444444;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* === Dialog === */
QDialog {
    background-color: #f5f6f8;
    color: #333333;
}

/* === ToolTip === */
QToolTip {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px 8px;
    color: #333333;
}

/* === Label === */
QLabel {
    color: #333333;
}
"""


def stylesheet_for(theme_name: str) -> str:
    return DARK if theme_name == "dark" else LIGHT