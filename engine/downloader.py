import os
import time
import threading
import re
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from engine.config import config
from engine.events import bus
from engine.logger import get_logger
from engine.models import DownloadTask, Segment, DownloadStatus

log = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

# Common file type signatures for smart content-type detection
CONTENT_TYPE_MAP = {
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/x-7z-compressed": ".7z",
    "application/x-tar": ".tar",
    "application/x-msdownload": ".exe",
    "application/x-msi": ".msi",
    "application/pdf": ".pdf",
    "video/mp4": ".mp4",
    "video/x-matroska": ".mkv",
    "video/webm": ".webm",
    "video/x-msvideo": ".avi",
    "audio/mpeg": ".mp3",
    "audio/flac": ".flac",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def sanitize_filename(name: str) -> str:
    """Remove forbidden characters from a filename and strip spacing."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip(" .")
    return name or "download.bin"


def _extract_filename(headers, fallback_name: str) -> str:
    """Extract filename from Content-Disposition header, falling back to URL base."""
    content_disp = headers.get("Content-Disposition", "")
    if content_disp:
        # Try RFC 5987 UTF-8 encoding first
        match = re.search(r"filename\*=UTF-8''([^;\r\n]+)", content_disp, re.IGNORECASE)
        if match:
            try:
                return sanitize_filename(unquote(match.group(1)))
            except Exception:
                pass
        # Try standard filename param
        match = re.search(r'filename=["\']?([^"\';\r\n]+)["\']?', content_disp, re.IGNORECASE)
        if match:
            try:
                return sanitize_filename(unquote(match.group(1)))
            except Exception:
                pass
    return sanitize_filename(fallback_name)


def _make_unique_path(dest_path: str) -> str:
    """Get a unique path if file already exists by appending (1), (2), etc."""
    if not os.path.exists(dest_path):
        return dest_path
    directory = os.path.dirname(dest_path)
    filename = os.path.basename(dest_path)
    stem, ext = os.path.splitext(filename)
    counter = 1
    while True:
        candidate = os.path.join(directory, f"{stem} ({counter}){ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


class SpeedLimiter:
    """Token bucket rate limiter shared across all segments of a single task."""

    def __init__(self, kbps: int):
        self.rate = kbps * 1024 if kbps else 0
        self.max_tokens = max(self.rate, 1024 * 1024)  # burst allowance
        self.tokens = self.max_tokens
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def throttle(self, n_bytes: int):
        if not self.rate:
            return
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens < n_bytes:
                wait_time = (n_bytes - self.tokens) / self.rate
                time.sleep(min(wait_time, 5.0))  # cap sleep to 5s
                self.tokens = 0
            else:
                self.tokens -= n_bytes


class Downloader:
    """Handles a single download: probes server, segments file, downloads concurrently."""

    def __init__(self, task: DownloadTask, on_progress_saved=None):
        self.task = task
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        self.on_progress_saved = on_progress_saved
        self._file_lock = threading.Lock()
        self._session = requests.Session()
        
        # Load user agent from config settings
        ua = config.get("user_agent", DEFAULT_HEADERS["User-Agent"])
        self._session.headers.update({
            "User-Agent": ua
        })

        if task.referrer:
            self._session.headers["Referer"] = task.referrer
            
        if task.cookies:
            # Parse cookie header and scope correctly in Session
            for cookie in task.cookies.split(";"):
                if "=" in cookie:
                    name, val = cookie.strip().split("=", 1)
                    self._session.cookies.set(name, val)

    def pause(self):
        self.pause_event.set()
        self.task.status = DownloadStatus.PAUSED
        bus.emit("task_updated", self.task)

    def resume(self):
        self.pause_event.clear()

    def cancel(self):
        self.cancel_event.set()
        self.pause_event.clear()  # wake up from pause

    def _probe(self):
        """Probe server to get file size and range support with GET fallback."""
        resp = None
        try:
            # Attempt HEAD request first for efficiency
            resp = self._session.head(
                self.task.url,
                allow_redirects=True,
                timeout=(10, 15),
                headers={"Accept-Encoding": "identity"},
            )
            resp.raise_for_status()
        except Exception as exc:
            log.warning("HEAD probe failed for %s, falling back to GET: %s", self.task.url, exc)
            try:
                # Fallback to GET with stream=True so we only download headers
                resp = self._session.get(
                    self.task.url,
                    allow_redirects=True,
                    timeout=(10, 15),
                    headers={"Accept-Encoding": "identity"},
                    stream=True,
                )
                resp.raise_for_status()
            except Exception as get_exc:
                log.error("GET probe fallback also failed for %s: %s", self.task.url, get_exc)
                raise get_exc

        # Follow final redirected URL
        if resp.url and resp.url != self.task.url:
            log.info("Redirect detected: %s -> %s", self.task.url, resp.url)
            self.task.url = resp.url

        size = int(resp.headers.get("Content-Length", -1))
        accepts_ranges = resp.headers.get("Accept-Ranges", "").lower() == "bytes"

        # Correct filename if provided in Content-Disposition
        old_filename = os.path.basename(self.task.dest_path)
        new_filename = _extract_filename(resp.headers, old_filename)
        
        # Extract content-type for smart extension detection
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type and content_type in CONTENT_TYPE_MAP:
            self.task.detected_ext = CONTENT_TYPE_MAP[content_type]

        # Apply smart extension correction if no extension or generic (.bin) is used
        _, ext = os.path.splitext(new_filename)
        if (not ext or ext.lower() in (".bin", ".tmp")) and self.task.detected_ext:
            new_filename = new_filename + self.task.detected_ext

        if new_filename != old_filename:
            old_dir = os.path.dirname(self.task.dest_path)
            new_dest = _make_unique_path(os.path.join(old_dir, new_filename))
            self.task.dest_path = new_dest
            self.task.filename = os.path.basename(new_dest)
            log.info("Filename corrected to: %s", self.task.filename)

        # Close GET stream if we used the fallback GET request
        resp.close()

        # Double-check range support with a GET range request
        if size > 0 and not accepts_ranges:
            try:
                probe = self._session.get(
                    self.task.url,
                    headers={"Range": "bytes=0-0", "Accept-Encoding": "identity"},
                    timeout=(10, 15),
                    stream=True,
                )
                accepts_ranges = probe.status_code == 206
                if not accepts_ranges and probe.status_code == 200:
                    actual_size = int(probe.headers.get("Content-Length", -1))
                    if actual_size > size:
                        size = actual_size
                probe.close()
            except Exception:
                pass

        self.task.total_size = size
        self.task.supports_range = accepts_ranges and size > 0

        log.info(
            "Probe complete: %s | size=%s | ranges=%s | type=%s",
            self.task.id,
            size,
            accepts_ranges,
            content_type,
        )

    def _build_segments(self):
        """Split file into segments for parallel download."""
        segment_count = config.get("max_segments", 8)
        size = self.task.total_size

        # Non-segmentable download: single segment
        if not self.task.supports_range or size <= 0:
            self.task.segments = [Segment(0, 0, max(size, 0) - 1 if size > 0 else 0)]
            return

        # Smart segment sizing: minimum 256 KB per segment
        min_segment_size = 256 * 1024
        optimal_count = max(1, size // min_segment_size)
        segment_count = min(segment_count, optimal_count)
        segment_count = max(1, segment_count)

        chunk = size // segment_count
        segments = []
        start = 0
        for i in range(segment_count):
            end = start + chunk - 1 if i < segment_count - 1 else size - 1
            segments.append(Segment(i, start, end))
            start = end + 1

        self.task.segments = segments
        log.info("Split %s into %d segments (~%s each)", self.task.id, segment_count,
                 self._human(chunk))

    @staticmethod
    def _human(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        n /= 1024
        if n < 1024:
            return f"{n:.0f} KB"
        n /= 1024
        return f"{n:.1f} MB"

    def _download_segment(self, segment: Segment, limiter: SpeedLimiter):
        """Download a single segment with retry logic."""
        chunk_size = config.get("chunk_size", 256 * 1024)
        attempts = 0
        max_attempts = config.get("retry_attempts", 5)
        is_unknown_size = self.task.total_size <= 0
        # Throttle progress emissions to avoid flooding the UI thread with signals.
        # Emitting at every chunk (dozens of times per second per segment) can
        # cause recursive repaint and UI thread starvation. We limit to ~4 emits/sec.
        _last_emit = 0.0
        _emit_min_interval = 0.25  # seconds between progress signal emissions

        while is_unknown_size or segment.downloaded < segment.size:
            if self.cancel_event.is_set():
                return

            # Handle pause
            while self.pause_event.is_set():
                time.sleep(0.3)
                if self.cancel_event.is_set():
                    return

            # Setup range parameters and write mode
            if not self.task.supports_range:
                # If range is not supported, any start or retry must download from the beginning
                segment.downloaded = 0
                range_start = 0
                write_mode = "wb"
            else:
                range_start = segment.start + segment.downloaded
                write_mode = "r+b"

            range_end = segment.end

            headers = {"Accept-Encoding": "identity"}
            if self.task.supports_range:
                headers["Range"] = f"bytes={range_start}-{range_end}"

            try:
                resp = self._session.get(
                    self.task.url,
                    headers=headers,
                    stream=True,
                    timeout=(15, 60),
                )

                if self.task.supports_range and resp.status_code not in (206, 200):
                    resp.raise_for_status()

                with open(self.task.dest_path, write_mode) as f:
                    if self.task.supports_range:
                        f.seek(range_start)

                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if self.cancel_event.is_set():
                            resp.close()
                            return

                        while self.pause_event.is_set():
                            time.sleep(0.3)
                            if self.cancel_event.is_set():
                                resp.close()
                                return

                        if not chunk:
                            continue

                        limiter.throttle(len(chunk))

                        with self._file_lock:
                            f.write(chunk)

                        segment.downloaded += len(chunk)
                        # Throttled progress emission: only emit if enough time
                        # has elapsed since the last emission. This prevents
                        # overwhelming the GUI thread with rapid-fire signals
                        # that cause recursive repaint and QBackingStore errors.
                        now = time.monotonic()
                        if now - _last_emit >= _emit_min_interval:
                            bus.emit("task_progress", self.task)
                            _last_emit = now

                resp.close()

                # If size was unknown, successful completion of stream means EOF
                if is_unknown_size:
                    segment.end = segment.downloaded - 1 if segment.downloaded > 0 else 0
                    self.task.total_size = segment.downloaded
                    return

                if segment.downloaded >= segment.size:
                    return

            except (requests.RequestException, OSError) as exc:
                attempts += 1
                delay = config.get("retry_delay_seconds", 3)

                if attempts >= max_attempts:
                    log.error(
                        "Segment %s of %s failed permanently (%s/%s): %s",
                        segment.index, self.task.id, attempts, max_attempts, exc,
                    )
                    raise RuntimeError(
                        f"Segment {segment.index} failed after {max_attempts} attempts: {exc}"
                    ) from exc

                log.warning(
                    "Segment %s of %s failed (%s/%s), retrying in %ss: %s",
                    segment.index, self.task.id, attempts, max_attempts, delay, exc,
                )

                # Exponential backoff
                time.sleep(delay * (1.5 ** (attempts - 1)))

    def run(self):
        """Execute the download workflow."""
        task = self.task
        try:
            task.status = DownloadStatus.CONNECTING
            bus.emit("task_updated", task)

            # Probe server if first time
            if not task.segments:
                self._probe()
                self._build_segments()
                self._preallocate_file()

            task.status = DownloadStatus.DOWNLOADING
            bus.emit("task_updated", task)

            limiter = SpeedLimiter(config.get("speed_limit_kbps", 0))
            remaining = [s for s in task.segments if not s.done]

            if not remaining:
                task.status = DownloadStatus.COMPLETED
                bus.emit("task_completed", task)
                bus.emit("task_updated", task)
                return

            # Download with thread pool
            workers = min(len(remaining), config.get("max_segments", 8))
            failed = False
            error_msg = ""
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(self._download_segment, seg, limiter)
                    for seg in remaining
                ]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        failed = True
                        error_msg = str(exc)
                        if self.cancel_event.is_set():
                            break
                        log.error("Segment worker crashed: %s", exc)

            if self.cancel_event.is_set():
                task.status = DownloadStatus.CANCELED
                bus.emit("task_updated", task)
                return

            if failed:
                task.status = DownloadStatus.FAILED
                task.error_message = error_msg[:256]
                bus.emit("task_updated", task)
                return

            # Verify completeness
            if all(s.done for s in task.segments):
                # Trim file to actual size (remove preallocation padding)
                self._trim_file()
                task.status = DownloadStatus.COMPLETED

                # Checksum verification & calculation
                if os.path.isfile(task.dest_path):
                    try:
                        from engine.checksum import calculate_file_hashes, verify_checksum
                        if task.expected_checksum:
                            matched = verify_checksum(task.dest_path, task.expected_checksum)
                            task.checksum_verified = matched
                            hashes = calculate_file_hashes(task.dest_path)
                            task.actual_checksum = hashes.get("sha256", "")
                            if not matched:
                                log.warning(
                                    "Checksum mismatch for %s: expected %s, got %s",
                                    task.id,
                                    task.expected_checksum,
                                    task.actual_checksum,
                                )
                        elif config.get("auto_calc_checksum", False):
                            hashes = calculate_file_hashes(task.dest_path)
                            task.actual_checksum = hashes.get("sha256", "")
                    except Exception as ce:
                        log.warning("Checksum calculation failed for %s: %s", task.id, ce)

                bus.emit("task_completed", task)
            else:
                task.status = DownloadStatus.PAUSED
                log.warning("Download %s incomplete: %s/%s segments done",
                             task.id, sum(1 for s in task.segments if s.done),
                             len(task.segments))

            bus.emit("task_updated", task)

        except Exception as exc:
            task.status = DownloadStatus.FAILED
            task.error_message = str(exc)[:256]
            log.error("Download %s failed: %s", task.id, exc)
            bus.emit("task_updated", task)

    def _preallocate_file(self):
        """Create and preallocate the target file."""
        path = self.task.dest_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        size = self.task.total_size
        if size <= 0 or not self.task.supports_range:
            # Unknown size or range not supported: start empty, will grow as segments download
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    pass
            return

        # Preallocate by seeking and writing a null byte
        with open(path, "wb") as f:
            f.seek(size - 1)
            f.write(b"\0")

    def _trim_file(self):
        """Trim the destination file to the exact downloaded size."""
        actual_size = self.task.downloaded_bytes
        total_size = self.task.total_size

        if total_size > 0 and actual_size < total_size:
            try:
                with open(self.task.dest_path, "ab") as f:
                    f.truncate(actual_size)
            except OSError:
                pass