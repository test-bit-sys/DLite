"""
DLite Download Scheduler Engine
Manages scheduled starts, stops, time-based bandwidth throttling windows,
and post-schedule system actions.
"""
from datetime import datetime, time as dtime
import logging

from engine.config import config
from engine.events import bus
from engine.models import DownloadStatus
from engine.queue_manager import queue_manager

logger = logging.getLogger(__name__)


def parse_time_str(time_str: str) -> dtime:
    """Parse 'HH:MM' or 'HH:MM:SS' string into a datetime.time object."""
    parts = [int(p) for p in time_str.strip().split(":")]
    if len(parts) == 2:
        return dtime(hour=parts[0], minute=parts[1])
    elif len(parts) == 3:
        return dtime(hour=parts[0], minute=parts[1], second=parts[2])
    raise ValueError(f"Invalid time format: {time_str}")


def is_in_time_window(current: dtime, start: dtime, end: dtime) -> bool:
    """
    Check if current time is within [start, end].
    Correctly supports overnight windows (e.g. 22:00 to 06:00).
    """
    if start <= end:
        return start <= current <= end
    else:
        # Overnight range, e.g. 23:00 to 05:00
        return current >= start or current <= end


class DownloadScheduler:
    """
    Engine component responsible for evaluating time-based download schedules.
    Evaluates:
      1. Start queue at scheduled time.
      2. Stop queue at scheduled time.
      3. Dynamic bandwidth throttling window (temporary speed limit).
      4. Auto-actions upon completion of scheduled downloads.
    """

    def __init__(self):
        self._last_start_minute = -1
        self._last_stop_minute = -1
        self._throttled_by_scheduler = False
        self._original_speed_limit = 0

    @property
    def is_enabled(self) -> bool:
        return bool(config.get("scheduler_enabled", False))

    def check(self, now: datetime | None = None):
        """
        Evaluate scheduling rules against the given (or current) timestamp.
        Typically called once per second by the GUI or background runner.
        """
        if now is None:
            now = datetime.now()

        current_time = now.time()
        minute_key = now.hour * 60 + now.minute

        # If scheduler is completely disabled, revert any active throttle and exit
        if not self.is_enabled:
            if self._throttled_by_scheduler:
                self._restore_speed_limit()
            return

        # ── 1. Scheduled Start ───────────────────────────────────────
        if config.get("scheduler_start_enabled", False):
            start_str = config.get("scheduler_start_time", "02:00")
            try:
                start_t = parse_time_str(start_str)
                if current_time.hour == start_t.hour and current_time.minute == start_t.minute:
                    if self._last_start_minute != minute_key:
                        self._last_start_minute = minute_key
                        logger.info("[scheduler] Start time reached (%s) — resuming queue", start_str)
                        self._start_queue()
                        bus.emit("scheduler_event", {"type": "start", "time": start_str})
            except Exception as e:
                logger.error("[scheduler] Failed evaluating start time: %s", e)

        # ── 2. Scheduled Stop ────────────────────────────────────────
        if config.get("scheduler_stop_enabled", False):
            stop_str = config.get("scheduler_stop_time", "07:00")
            try:
                stop_t = parse_time_str(stop_str)
                if current_time.hour == stop_t.hour and current_time.minute == stop_t.minute:
                    if self._last_stop_minute != minute_key:
                        self._last_stop_minute = minute_key
                        logger.info("[scheduler] Stop time reached (%s) — pausing queue", stop_str)
                        self._pause_queue()
                        bus.emit("scheduler_event", {"type": "stop", "time": stop_str})
            except Exception as e:
                logger.error("[scheduler] Failed evaluating stop time: %s", e)

        # ── 3. Bandwidth Throttling Window ───────────────────────────
        if config.get("scheduler_throttle_enabled", False):
            t_start_str = config.get("scheduler_throttle_start", "09:00")
            t_end_str = config.get("scheduler_throttle_end", "18:00")
            throttle_rate = int(config.get("scheduler_throttle_rate_kbps", 500))

            try:
                t_start = parse_time_str(t_start_str)
                t_end = parse_time_str(t_end_str)
                in_window = is_in_time_window(current_time, t_start, t_end)

                if in_window:
                    if not self._throttled_by_scheduler:
                        self._original_speed_limit = int(config.get("speed_limit_kbps", 0))
                        config.set("speed_limit_kbps", throttle_rate)
                        self._throttled_by_scheduler = True
                        logger.info(
                            "[scheduler] Entering throttling window (%s to %s): speed capped to %d KB/s",
                            t_start_str, t_end_str, throttle_rate,
                        )
                        bus.emit("scheduler_event", {
                            "type": "throttle_on",
                            "rate": throttle_rate,
                            "window": f"{t_start_str}-{t_end_str}",
                        })
                else:
                    if self._throttled_by_scheduler:
                        self._restore_speed_limit()
            except Exception as e:
                logger.error("[scheduler] Failed evaluating throttling window: %s", e)
        else:
            if self._throttled_by_scheduler:
                self._restore_speed_limit()

    def _start_queue(self):
        """Resume paused downloads and start queued tasks."""
        for task_id, task in list(queue_manager.tasks.items()):
            if task.status == DownloadStatus.PAUSED:
                queue_manager.resume(task_id)
            elif task.status == DownloadStatus.QUEUED:
                queue_manager.start(task_id)

    def _pause_queue(self):
        """Pause all currently active and queued downloads."""
        for task_id, task in list(queue_manager.tasks.items()):
            if task.status in (
                DownloadStatus.DOWNLOADING,
                DownloadStatus.CONNECTING,
                DownloadStatus.QUEUED,
            ):
                queue_manager.pause(task_id)

    def _restore_speed_limit(self):
        """Restore original speed limit after throttling window ends."""
        config.set("speed_limit_kbps", self._original_speed_limit)
        self._throttled_by_scheduler = False
        logger.info(
            "[scheduler] Exiting throttling window: restored speed limit to %d KB/s",
            self._original_speed_limit,
        )
        bus.emit("scheduler_event", {
            "type": "throttle_off",
            "rate": self._original_speed_limit,
        })

    def get_status_summary(self) -> str:
        """Return a concise description of current scheduler state."""
        if not self.is_enabled:
            return "Disabled"

        parts = []
        if config.get("scheduler_start_enabled", False):
            parts.append(f"Starts: {config.get('scheduler_start_time', '02:00')}")
        if config.get("scheduler_stop_enabled", False):
            parts.append(f"Stops: {config.get('scheduler_stop_time', '07:00')}")
        if config.get("scheduler_throttle_enabled", False):
            rate = config.get("scheduler_throttle_rate_kbps", 500)
            s = config.get("scheduler_throttle_start", "09:00")
            e = config.get("scheduler_throttle_end", "18:00")
            parts.append(f"Throttle: {rate} KB/s ({s}-{e})")

        return " | ".join(parts) if parts else "Armed (Idle)"


scheduler = DownloadScheduler()
