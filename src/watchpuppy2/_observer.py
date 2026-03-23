import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.api import BaseObserver
from watchdog.observers.inotify import InotifyObserver
from watchdog.observers.polling import PollingObserver

_PROBE_FILE_NAME_PREFIX = ".watchpuppy2-probe-"
_PROBE_TIMEOUT_SECONDS = 1.0
_PROBE_WAIT_INTERVAL_SECONDS = 0.01
_POLLING_TIMEOUT_SECONDS = 1.0


class _ProbeEventHandler(FileSystemEventHandler):
    def __init__(self, probe_path: Path) -> None:
        self._probe_path = str(probe_path)
        self._seen = threading.Event()

    @property
    def seen(self) -> bool:
        return self._seen.is_set()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.src_path in {self._probe_path, event.dest_path}:
            self._seen.set()


def create_observer(path: Path, *, recursive: bool) -> BaseObserver:
    if _supports_inotify(path, recursive=recursive):
        return InotifyObserver()
    return PollingObserver(timeout=_POLLING_TIMEOUT_SECONDS)


def _supports_inotify(path: Path, *, recursive: bool) -> bool:
    probe_path = path / f"{_PROBE_FILE_NAME_PREFIX}{time.time_ns()}"
    handler = _ProbeEventHandler(probe_path)
    observer = InotifyObserver()
    try:
        observer.schedule(handler, str(path), recursive=recursive)
        observer.start()
        probe_path.write_text("probe", encoding="utf-8")
        probe_path.unlink()
        return _wait_for_probe_event(handler)
    except OSError:
        return False
    finally:
        _unlink_probe_file(probe_path)
        observer.stop()
        observer.join()


def _wait_for_probe_event(handler: _ProbeEventHandler) -> bool:
    deadline = time.monotonic() + _PROBE_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if handler.seen:
            return True
        time.sleep(_PROBE_WAIT_INTERVAL_SECONDS)
    return False


def _unlink_probe_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
