import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

# Map extensions to categories
CATEGORY_EXTENSIONS = {
    "video":    ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg", "mpeg", "3gp", "ogv", "ts"],
    "audio":    ["mp3", "wav", "flac", "aac", "ogg", "wma", "m4a", "opus"],
    "document": ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "txt", "csv", "rtf", "epub", "mobi"],
    "archive":  ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab", "arj", "lzh"],
    "software": ["exe", "msi", "dmg", "apk", "deb", "rpm", "appimage"],
    "image":    ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "ico", "tiff", "psd"],
}


def guess_category(filename: str) -> str:
    """Detect category from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    for cat, exts in CATEGORY_EXTENSIONS.items():
        if ext in exts:
            return cat
    return "general"


class DownloadStatus(str, Enum):
    QUEUED = "queued"
    CONNECTING = "connecting"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class Segment:
    index: int
    start: int
    end: int
    downloaded: int = 0

    @property
    def size(self) -> int:
        return self.end - self.start + 1

    @property
    def done(self) -> bool:
        return self.downloaded >= self.size

    def to_dict(self):
        return {"index": self.index, "start": self.start, "end": self.end, "downloaded": self.downloaded}

    @staticmethod
    def from_dict(d):
        return Segment(d["index"], d["start"], d["end"], d.get("downloaded", 0))


@dataclass
class DownloadTask:
    url: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    filename: str = ""
    save_path: str = ""           # Folder where the file will be saved
    dest_path: str = ""           # Full final path (computed at download start)
    total_size: int = -1
    supports_range: bool = False
    segments: list = field(default_factory=list)
    status: DownloadStatus = DownloadStatus.QUEUED
    error_message: str = ""
    created_at: float = field(default_factory=time.time)
    referrer: str = ""
    cookies: str = ""
    mime: str = ""                # MIME type (e.g., "application/pdf")
    detected_ext: str = ""
    category: str = "general"

    @property
    def downloaded_bytes(self) -> int:
        return sum(s.downloaded for s in self.segments)

    @property
    def progress(self) -> float:
        if self.total_size <= 0:
            return 0.0
        return min(100.0, (self.downloaded_bytes / self.total_size) * 100)

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "dest_path": self.dest_path,
            "save_path": self.save_path,
            "filename": self.filename,
            "total_size": self.total_size,
            "supports_range": self.supports_range,
            "segments": [s.to_dict() for s in self.segments],
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "referrer": self.referrer,
            "cookies": self.cookies,
            "mime": self.mime,
            "category": self.category,
        }

    @staticmethod
    def from_dict(d):
        task = DownloadTask(url=d["url"])
        task.id = d["id"]
        task.filename = d.get("filename", "")
        task.save_path = d.get("save_path", "")
        task.dest_path = d.get("dest_path", "")
        task.total_size = d.get("total_size", -1)
        task.supports_range = d.get("supports_range", False)
        task.segments = [Segment.from_dict(s) for s in d.get("segments", [])]
        task.status = DownloadStatus(d.get("status", "queued"))
        task.error_message = d.get("error_message", "")
        task.created_at = d.get("created_at", time.time())
        task.referrer = d.get("referrer", "")
        task.cookies = d.get("cookies", "")
        task.mime = d.get("mime", "")
        task.category = d.get("category", "general")
        return task
