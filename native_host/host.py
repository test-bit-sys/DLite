"""
DLite Native Messaging Host
Bridges browser extensions (Chrome/Firefox/Edge) to the DLite desktop app via TCP.
"""
import json
import logging
import os
import socket
import struct
import sys
from pathlib import Path

DEFAULT_DESKTOP_APP_PORT = 38271
DESKTOP_APP_HOST = "127.0.0.1"

# Set up basic logging to stderr (stdout is used for native protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("native_host")


def _load_desktop_app_port() -> int:
    """Read the TCP port the desktop app listens on.

    The user can change `native_host_port` in the app's Settings dialog,
    so the native messaging host must read the same value from the app's
    settings file instead of assuming the default — otherwise browser
    integration silently breaks after a port change.
    """
    try:
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", str(Path.home())))
        else:
            base = Path.home() / ".config"
        settings_path = base / "DLite" / "settings.json"
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        port = int(data.get("native_host_port", DEFAULT_DESKTOP_APP_PORT))
        if not (1024 <= port <= 65535):
            log.warning("Configured port %s out of range, using default", port)
            return DEFAULT_DESKTOP_APP_PORT
        return port
    except FileNotFoundError:
        # App not configured yet — the default is used on first run.
        return DEFAULT_DESKTOP_APP_PORT
    except Exception as exc:
        log.warning("Could not read settings (%s), using default port", exc)
        return DEFAULT_DESKTOP_APP_PORT


DESKTOP_APP_PORT = _load_desktop_app_port()


def read_message():
    """Read a native-messaging message from stdin (4-byte length + JSON)."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length or len(raw_length) < 4:
        return None
    length = struct.unpack("<I", raw_length)[0]
    if length <= 0 or length > 1024 * 1024:  # 1 MB limit for safety
        log.warning("Invalid message length: %d", length)
        return None
    data = sys.stdin.buffer.read(length)
    if not data:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        log.warning("Failed to parse JSON: %s", e)
        return None


def send_message(message: dict):
    """Send a native-messaging message to stdout (4-byte length + JSON)."""
    encoded = json.dumps(message, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def forward_to_desktop_app(payload: dict) -> dict:
    """
    Forward a message to the desktop app TCP listener.
    Returns the desktop app's JSON response.
    """
    # Handle ping requests locally
    if payload.get("action") == "ping":
        try:
            # Actually try to connect to verify the app is running
            with socket.create_connection(
                (DESKTOP_APP_HOST, DESKTOP_APP_PORT), timeout=2
            ) as sock:
                sock.sendall(json.dumps({"action": "ping"}).encode("utf-8"))
                response = sock.recv(4096)
                resp_data = json.loads(response.decode("utf-8"))
                return {"ok": True, "app_running": True, "response": resp_data}
        except (OSError, json.JSONDecodeError) as e:
            return {"ok": True, "app_running": False, "error": str(e)}
        except Exception as e:
            return {"ok": True, "app_running": False, "error": str(e)}

    # Forward regular download requests
    try:
        with socket.create_connection(
            (DESKTOP_APP_HOST, DESKTOP_APP_PORT), timeout=5
        ) as sock:
            sock.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            # Read response with timeout
            sock.settimeout(5)
            response = sock.recv(4096)
            if not response:
                return {"ok": False, "error": "No response from desktop app", "app_running": True}
            return json.loads(response.decode("utf-8"))
    except socket.timeout:
        return {"ok": False, "error": "Connection timed out", "app_running": False}
    except ConnectionRefusedError:
        return {"ok": False, "error": "Desktop app not running", "app_running": False}
    except (OSError, json.JSONDecodeError) as e:
        return {"ok": False, "error": str(e), "app_running": False}
    except Exception as e:
        return {"ok": False, "error": str(e), "app_running": False}


def main():
    log.info("DLite native host started")
    send_message({"ok": True, "status": "ready"})

    while True:
        message = read_message()
        if message is None:
            log.info("Stdin closed, exiting")
            break

        log.debug("Received: %s", message)
        result = forward_to_desktop_app(message)
        log.debug("Sending: %s", result)
        send_message(result)


if __name__ == "__main__":
    main()