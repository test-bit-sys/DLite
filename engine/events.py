import logging
import threading
from collections import defaultdict

_log = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)
        self._lock = threading.Lock()

    def on(self, event_name, callback):
        with self._lock:
            self._listeners[event_name].append(callback)

    def off(self, event_name, callback):
        with self._lock:
            if callback in self._listeners[event_name]:
                self._listeners[event_name].remove(callback)

    def emit(self, event_name, *args, **kwargs):
        with self._lock:
            callbacks = list(self._listeners[event_name])
        for cb in callbacks:
            try:
                cb(*args, **kwargs)
            except Exception:
                # A broken listener must never take down a download thread,
                # but failing silently makes bugs impossible to diagnose.
                _log.exception("EventBus listener for %r failed", event_name)


bus = EventBus()
