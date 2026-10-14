import json
import os
from pathlib import Path

APP_NAME = "DLite"

DEFAULT_SETTINGS = {
    "download_dir": str(Path.home() / "Downloads" / "DLite"),
    "max_segments": 8,
    "max_concurrent_downloads": 3,
    "speed_limit_kbps": 0,          # 0 means unlimited
    "retry_attempts": 5,
    "retry_delay_seconds": 3,
    "chunk_size": 1024 * 256,
    "theme": "dark",
    "minimize_to_tray": True,
    "auto_start_downloads": True,
    "native_host_port": 38271,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "monitor_clipboard": True,
    "clipboard_auto_open_dialog": True,
    "notify_on_complete": True,
    "action_on_complete": "none",
    "scheduler_enabled": False,
    "scheduler_start_enabled": False,
    "scheduler_start_time": "02:00",
    "scheduler_stop_enabled": False,
    "scheduler_stop_time": "07:00",
    "scheduler_throttle_enabled": False,
    "scheduler_throttle_start": "09:00",
    "scheduler_throttle_end": "18:00",
    "scheduler_throttle_rate_kbps": 500,
    "scheduler_action_on_complete": "none",
}


def _config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


class Config:
    def __init__(self):
        self.path = _config_dir() / "settings.json"
        self.data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        if not self.path.exists():
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            self.data.update(stored)
        except (json.JSONDecodeError, OSError):
            # corrupted config, fall back to defaults instead of crashing
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    @property
    def download_dir(self) -> Path:
        d = Path(self.data["download_dir"])
        d.mkdir(parents=True, exist_ok=True)
        return d


config = Config()
