import json
import socket
import sys
import threading
import os

from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor
from PyQt6.QtWidgets import QApplication, QSplashScreen

from engine.config import config
from engine.logger import get_logger
from engine.version import APP_VERSION
from gui.main_window import MainWindow

log = get_logger("main")

# ─── Paths ──────────────────────────────────────────
def _resource_dir() -> str:
    """Return the directory containing bundled resources.
    Handles both dev mode and PyInstaller frozen mode (onedir/onefile)."""
    if getattr(sys, "frozen", False):
        # PyInstaller: bundled data lives in _MEIPASS (temp for onefile,
        # or <app>/_internal for onedir in PyInstaller 6+).
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(__file__)


ICONS_DIR = os.path.join(_resource_dir(), "icons")
ICON_ICO = os.path.join(ICONS_DIR, "icon.ico")
ICON_PNG = os.path.join(ICONS_DIR, "icon.png")
ICON_256 = os.path.join(ICONS_DIR, "icon256.png")
LOGO_DARK = os.path.join(ICONS_DIR, "logo_dark_full.png")


class InterceptSignalBridge(QObject):
    """Thread-safe bridge: receives interception data from any thread
    and forwards it to the main/GUI thread via a Qt signal.
    
    This avoids the 'setParent: new parent is in a different thread'
    bug and all related QWidget/QTimer threading errors."""
    intercept_requested = pyqtSignal(dict)

    def __init__(self, window: MainWindow):
        super().__init__()
        self.window = window
        # Connect the signal to the window's handler — this ensures
        # the handler always runs in the main/GUI thread.
        self.intercept_requested.connect(self._on_intercept)

    def _on_intercept(self, payload: dict):
        """Runs in the main thread — safe to create/modify QWidgets."""
        self.window.intercept_download_from_extension(
            url=payload["url"],
            filename=payload.get("filename", ""),
            referrer=payload.get("referrer", ""),
            cookies=payload.get("cookies", ""),
            file_size=payload.get("fileSize", 0),
            mime=payload.get("mime", ""),
        )


class ExtensionListener:
    """Tiny loopback TCP server the native messaging host talks to.
    Keeps the browser extension decoupled from the desktop app's process.

    All UI interactions are routed through InterceptSignalBridge's
    pyqtSignal so QWidget creation/modification always happens in
    the main/GUI thread, preventing the dreaded:
      - QObject::setParent: Cannot set parent, new parent is in a different thread
      - QBasicTimer::start: Timers cannot be started from another thread
      - QWidget::repaint: Recursive repaint detected
    """

    def __init__(self, window: MainWindow, port: int):
        self.window = window
        self.port = port
        self._sock = None
        # Signal bridge owned by the main thread (created before any threads start)
        self._bridge = InterceptSignalBridge(window)

    def start(self):
        thread = threading.Thread(target=self._serve, daemon=True)
        thread.start()

    def _serve(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind(("127.0.0.1", self.port))
        except OSError as exc:
            log.error("could not bind extension listener on port %s: %s", self.port, exc)
            return

        self._sock.listen(5)
        log.info("extension listener ready on port %s", self.port)

        while True:
            conn, _ = self._sock.accept()
            threading.Thread(target=self._handle_connection, args=(conn,), daemon=True).start()

    def _handle_connection(self, conn: socket.socket):
        with conn:
            try:
                raw = conn.recv(65536)
                if not raw:
                    return
                payload = json.loads(raw.decode("utf-8"))

                # Handle ping action for connection check
                if payload.get("action") == "ping":
                    conn.sendall(b'{"ok": true, "status": "running"}')
                    return

                # Emit signal to route the interception to the main thread.
                # The bridge's pyqtSignal is thread-safe and Qt will
                # invoke the connected slot in the GUI thread automatically.
                self._bridge.intercept_requested.emit(payload)
                conn.sendall(b'{"ok": true}')
            except (json.JSONDecodeError, KeyError, OSError) as exc:
                log.warning("bad request from extension: %s", exc)
                try:
                    conn.sendall(b'{"ok": false}')
                except OSError:
                    pass


def _create_splash(app: QApplication) -> QSplashScreen:
    """Build a branded splash screen with the official logo."""
    # Use the 256px icon for the splash
    logo_path = ICON_256 if os.path.exists(ICON_256) else ICON_PNG
    if not os.path.exists(logo_path):
        return None

    # Create splash pixmap — 420x320 with dark background
    from PyQt6.QtGui import QPainter, QLinearGradient
    from PyQt6.QtCore import QRectF

    splash_w, splash_h = 420, 340
    pixmap = QPixmap(splash_w, splash_h)
    pixmap.fill(QColor(16, 20, 28))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Subtle gradient overlay
    gradient = QLinearGradient(0, 0, 0, splash_h)
    gradient.setColorAt(0.0, QColor(20, 26, 36))
    gradient.setColorAt(1.0, QColor(10, 14, 22))
    painter.fillRect(QRectF(0, 0, splash_w, splash_h), gradient)

    # Draw logo centered
    logo_pixmap = QPixmap(logo_path)
    logo_size = 120
    scaled_logo = logo_pixmap.scaled(
        logo_size, logo_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    logo_x = (splash_w - scaled_logo.width()) // 2
    logo_y = 40
    painter.drawPixmap(logo_x, logo_y, scaled_logo)

    # Title text
    painter.setPen(QColor(240, 242, 245))
    title_font = QFont("Segoe UI", 22, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.drawText(QRectF(0, logo_y + logo_size + 16, splash_w, 40),
                     Qt.AlignmentFlag.AlignCenter, "DLite")

    # Subtitle
    painter.setPen(QColor(140, 150, 165))
    sub_font = QFont("Segoe UI", 10)
    painter.setFont(sub_font)
    painter.drawText(QRectF(0, logo_y + logo_size + 58, splash_w, 24),
                     Qt.AlignmentFlag.AlignCenter,
                     "Fast, Free & Open-Source Download Manager")

    # Version
    painter.setPen(QColor(80, 90, 100))
    ver_font = QFont("Segoe UI", 8)
    painter.setFont(ver_font)
    painter.drawText(QRectF(0, splash_h - 30, splash_w, 20),
                     Qt.AlignmentFlag.AlignCenter, f"Version {APP_VERSION}")

    # Green accent line
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(76, 175, 80))
    painter.drawRoundedRect(QRectF(splash_w // 2 - 40, splash_h - 46, 80, 3), 1.5, 1.5)

    painter.end()

    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.setFont(QFont("Segoe UI", 9))
    return splash


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("DLite")
    app.setApplicationVersion(APP_VERSION)

    # Set application-wide icon (prefer .ico for multi-resolution on Windows)
    icon_path = ICON_ICO if os.path.exists(ICON_ICO) else ICON_PNG
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Show splash screen
    splash = _create_splash(app)
    if splash:
        splash.show()
        splash.showMessage(
            "  Loading engine...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            QColor(100, 110, 125),
        )
        app.processEvents()

    # Create main window
    window = MainWindow()

    if splash:
        splash.showMessage(
            "  Starting listener...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            QColor(100, 110, 125),
        )
        app.processEvents()

    listener = ExtensionListener(window, config.get("native_host_port", 38271))
    listener.start()

    if splash:
        splash.showMessage(
            "  Ready!",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            QColor(76, 175, 80),
        )
        app.processEvents()
        # Close splash after a short delay
        QTimer.singleShot(800, lambda: (splash.finish(window), window.show()))
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
