import os
import threading
from uuid import uuid4

from engine.config import config
from engine.events import bus
from engine.logger import get_logger
from engine.models import DownloadTask, DownloadStatus

logger = get_logger(__name__)


class QueueManager:
    """
    Manages the download queue: task creation, prioritisation, concurrency
    gating, and lifecycle (pause / resume / cancel).

    Key design decisions:
    - `add()` only CREATE a task, NEVER starts it automatically.
      Callers (UI or IPC listener) are responsible for explicitly calling
      `start()` AFTER user confirmation.
    - `tasks` is a plain dict keyed by task UUID (NOT a list).  Iteration
      order is insertion order on CPython ≥ 3.7, which is good enough for
      a queue that users reorder manually.
    - Concurrency is limited by `max_concurrent_downloads`.  Once the limit
      is reached, extra tasks stay in QUEUED state until a slot opens.
    - Deduplication: URLs are de-duplicated. Calling `add()` for a URL
      that already exists in QUEUED / DOWNLOADING / CONNECTING returns the
      existing task instead of creating a duplicate.
    """

    def __init__(self):
        self.tasks: dict[str, DownloadTask] = {}
        self._lock = threading.Lock()
        self._slots_semaphore = threading.BoundedSemaphore(
            config.get("max_concurrent_downloads", 3)
        )
        self._active_count = 0
        self._downloaders = {}

    # ── task creation (idempotent by URL) ──────────────────────────
    def add(self, url: str, filename: str = "",
            save_path: str | None = None, category: str = "general",
            cookies: str = "", referrer: str = "", mime: str = "",
            total_size: int = 0, expected_checksum: str = "") -> DownloadTask:
        """
        Create a new download task.  If the same URL is already queued /
        downloading / connecting, the existing task is returned instead
        of creating a duplicate.

        The caller MUST call `start(task.id)` to begin downloading after
        the user confirms the download parameters.
        """
        url = url.strip()
        if not url:
            raise ValueError("url is required")

        # --- Deduplication by URL ---
        with self._lock:
            for t in self.tasks.values():
                if t.url == url and t.status in (
                    DownloadStatus.QUEUED,
                    DownloadStatus.CONNECTING,
                    DownloadStatus.DOWNLOADING,
                ):
                    logger.info(
                        "[dedup] URL already queued/active, skipping duplicate: %s (existing task %s)",
                        url, t.id,
                    )
                    return t

            task_id = str(uuid4())
            if not filename:
                filename = url.rsplit("/", 1)[-1].split("?")[0] or "download"
            if save_path is None:
                save_path = str(config.download_dir)

            task = DownloadTask(
                id=task_id,
                url=url,
                filename=filename,
                save_path=save_path,
                category=category,
                cookies=cookies,
                referrer=referrer,
                mime=mime,
                total_size=total_size,
                expected_checksum=expected_checksum.strip().lower(),
            )

            self.tasks[task_id] = task
            logger.info(
                "[queue] task created: id=%s url=%s filename=%s status=QUEUED",
                task_id, url, filename,
            )
            bus.emit("task_added", task)

        return task

    # ── lifecycle ─────────────────────────────────────────────────
    def start(self, task_id: str):
        """
        Move a QUEUED task into DOWNLOADING state (respect the
        concurrent-download limit).
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.warning("[queue] start called for unknown task: %s", task_id)
                return
            if task.status != DownloadStatus.QUEUED:
                logger.debug(
                    "[queue] start skipped — task %s is not QUEUED (%s)",
                    task_id, task.status,
                )
                return

            task.status = DownloadStatus.CONNECTING
            logger.info("[queue] task %s moving to CONNECTING", task_id)
            bus.emit("task_status_changed", task)

        # Dispatch download in a background thread so the UI stays responsive
        threading.Thread(
            target=self._download_runner,
            args=(task_id,),
            daemon=True,
            name=f"dl-{task_id[:8]}",
        ).start()

    def _download_runner(self, task_id: str):
        """Background thread that actually performs the download."""
        task = self.tasks.get(task_id)
        if not task:
            logger.error("[queue] _download_runner: task not found: %s", task_id)
            return

        # Compute the full destination path if not already set
        if not task.dest_path:
            save_folder = task.save_path or str(config.download_dir)
            os.makedirs(save_folder, exist_ok=True)
            candidate = os.path.join(save_folder, task.filename)
            if os.path.exists(candidate):
                base, ext = os.path.splitext(task.filename)
                counter = 1
                while os.path.exists(os.path.join(save_folder, f"{base} ({counter}){ext}")):
                    counter += 1
                task.filename = f"{base} ({counter}){ext}"
                candidate = os.path.join(save_folder, task.filename)
            task.dest_path = candidate
            logger.info("[queue] dest_path resolved: %s", task.dest_path)

        self._slots_semaphore.acquire()
        try:
            from engine.downloader import Downloader

            downloader = Downloader(task, on_progress_saved=self._on_bytes_saved)
            with self._lock:
                if task.status == DownloadStatus.CANCELED:
                    logger.info("[queue] task %s was canceled before starting", task_id)
                    return
                if task.status == DownloadStatus.PAUSED:
                    logger.info("[queue] task %s is paused before starting", task_id)
                    return
                self._downloaders[task_id] = downloader
            logger.info("[queue] Downloader created for task %s, dest=%s", task_id, task.dest_path)
            
            # Set status to CONNECTING (may have been set by start(), but be defensive)
            if task.status == DownloadStatus.QUEUED:
                task.status = DownloadStatus.CONNECTING
                bus.emit("task_status_changed", task)
            
            # Run the download
            try:
                downloader.run()
                
                if task.status == DownloadStatus.CANCELED:
                    logger.info("[queue] task %s was canceled during download", task_id)
                elif task.downloaded_bytes >= task.total_size > 0:
                    task.status = DownloadStatus.COMPLETED
                    logger.info("[queue] download completed: id=%s bytes=%d/%d", 
                                task_id, task.downloaded_bytes, task.total_size)
                    bus.emit("task_completed", task)
                else:
                    task.status = DownloadStatus.FAILED
                    task.error_message = task.error_message or "Download incomplete"
                    logger.warning("[queue] download failed: id=%s bytes=%d/%d error=%s",
                                   task_id, task.downloaded_bytes, task.total_size, task.error_message)
                
                bus.emit("task_status_changed", task)
            except Exception as exc:
                logger.exception("[queue] download worker crashed for %s: %s", task_id, exc)
                if task.status not in (DownloadStatus.CANCELED, DownloadStatus.COMPLETED):
                    task.status = DownloadStatus.FAILED
                    task.error_message = str(exc)[:200]
                bus.emit("task_status_changed", task)
        finally:
            with self._lock:
                self._downloaders.pop(task_id, None)

            self._slots_semaphore.release()

            with self._lock:
                # Promote next queued task if any
                for t in self.tasks.values():
                    if t.status == DownloadStatus.QUEUED:
                        logger.info("[queue] auto-promoting next queued task: %s", t.id)
                        threading.Thread(
                            target=self._download_runner,
                            args=(t.id,),
                            daemon=True,
                            name=f"dl-{t.id[:8]}",
                        ).start()
                        break
                else:
                    self._active_count = max(
                        0,
                        sum(
                            1 for t in self.tasks.values()
                            if t.status in (DownloadStatus.DOWNLOADING, DownloadStatus.CONNECTING)
                        ),
                    )

    def _on_bytes_saved(self, task_id: str):
        """Callback invoked by Downloader after bytes are flushed to disk."""
        task = self.tasks.get(task_id)
        if task:
            bus.emit("task_bytes_flushed", task)

    def pause(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            return
        downloader = self._downloaders.get(task_id)
        if task.status in (DownloadStatus.CONNECTING, DownloadStatus.DOWNLOADING) and downloader:
            downloader.pause()
            task.status = DownloadStatus.PAUSED
            logger.info("[queue] active task paused: %s", task_id)
            bus.emit("task_status_changed", task)
        elif task.status in (DownloadStatus.QUEUED, DownloadStatus.CONNECTING):
            task.status = DownloadStatus.PAUSED
            logger.info("[queue] queued task paused: %s", task_id)
            bus.emit("task_status_changed", task)

    def resume(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task or task.status != DownloadStatus.PAUSED:
            return
        downloader = self._downloaders.get(task_id)
        if downloader:
            downloader.resume()
            task.status = DownloadStatus.DOWNLOADING
            logger.info("[queue] active task resumed: %s", task_id)
            bus.emit("task_status_changed", task)
            return

        task.status = DownloadStatus.QUEUED
        logger.info("[queue] queued task resumed (back to QUEUED): %s", task_id)
        bus.emit("task_status_changed", task)
        self.start(task_id)

    def cancel(self, task_id: str):
        task = self.tasks.get(task_id)
        if task and task.status not in (DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELED):
            downloader = self._downloaders.get(task_id)
            if downloader:
                downloader.cancel()
            task.status = DownloadStatus.CANCELED
            logger.info("[queue] task canceled: %s", task_id)
            bus.emit("task_status_changed", task)
            bus.emit("task_canceled", task)

    def remove(self, task_id: str, delete_file: bool = False):
        """
        Fully remove a task (and its temp file fragments) from the queue.
        Safe to call on any status.
        If delete_file is True, also attempts to delete the downloaded file.
        """
        task = self.tasks.pop(task_id, None)
        if task:
            logger.info("[queue] task removed: %s", task_id)
            
            # Delete the downloaded file if requested
            if delete_file and task.dest_path:
                try:
                    if os.path.exists(task.dest_path):
                        os.remove(task.dest_path)
                        logger.info("[queue] deleted file: %s", task.dest_path)
                    # Also remove any .part fragments
                    part_dir = task.dest_path + ".parts"
                    if os.path.exists(part_dir):
                        import shutil
                        shutil.rmtree(part_dir, ignore_errors=True)
                        logger.info("[queue] cleaned up temp parts: %s", part_dir)
                except OSError as exc:
                    logger.warning("[queue] could not delete file %s: %s", task.dest_path, exc)
            
            bus.emit("task_removed", task_id)

    def progress_callback(self, task_id: str, downloaded: int, total: int,
                          speed: float = 0.0):
        """Called by download threads so the UI can react."""
        task = self.tasks.get(task_id)
        if not task:
            return
        task.downloaded_bytes = downloaded
        if total > 0:
            task.total_size = total
        bus.emit("task_progress", task, speed)


# Singleton instance shared across the whole desktop app
queue_manager = QueueManager()
