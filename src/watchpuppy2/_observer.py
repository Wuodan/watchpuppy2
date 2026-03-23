import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.api import BaseObserver
from watchdog.observers.inotify import InotifyObserver
from watchdog.observers.polling import PollingObserver

_logger = logging.getLogger(__name__)
_PROBE_FILE_NAME_PREFIX = ".watchpuppy2-probe-"
_PROBE_TIMEOUT_SECONDS = 1.0
_PROBE_WAIT_INTERVAL_SECONDS = 0.01
_POLLING_TIMEOUT_SECONDS = 1.0
_MOUNTINFO_MOUNT_POINT_INDEX = 4
_FORCE_POLLING_FILESYSTEM_TYPES = frozenset(
    {
        "cifs",
        "9p",
        "drvfs",
        "nfs",
        "nfs4",
        "smb3",
    }
)


class _ProbeEventHandler(FileSystemEventHandler):
    def __init__(self, probe_path: Path) -> None:
        self._probe_path = str(probe_path)
        self._seen = threading.Event()

    @property
    def seen(self) -> bool:
        return self._seen.is_set()

    def on_any_event(self, event: FileSystemEvent) -> None:
        _logger.debug(
            "Probe observer received event_type=%s src_path=%r dest_path=%r",
            event.event_type,
            event.src_path,
            event.dest_path,
        )
        if event.src_path in {self._probe_path, event.dest_path}:
            self._seen.set()


def create_observer(path: Path, *, recursive: bool) -> BaseObserver:
    fs_type = _filesystem_type(path)
    if fs_type in _FORCE_POLLING_FILESYSTEM_TYPES:
        _logger.info(
            "Selected PollingObserver for path=%s recursive=%s filesystem_type=%s",
            path,
            recursive,
            fs_type,
        )
        return PollingObserver(timeout=_POLLING_TIMEOUT_SECONDS)
    if _supports_inotify(path, recursive=recursive):
        _logger.info("Selected InotifyObserver for path=%s recursive=%s", path, recursive)
        return InotifyObserver()
    _logger.info("Selected PollingObserver for path=%s recursive=%s", path, recursive)
    return PollingObserver(timeout=_POLLING_TIMEOUT_SECONDS)


def _filesystem_type(path: Path) -> str | None:
    resolved_path = path.resolve()
    best_match = ""
    best_type: str | None = None
    try:
        mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    except OSError:
        _logger.exception("Could not read /proc/self/mountinfo for path=%s", path)
        return None
    for line in mountinfo.splitlines():
        mount_point, fs_type = _parse_mountinfo_line(line)
        if mount_point is None or fs_type is None:
            continue
        if not _path_is_under_mountpoint(resolved_path, mount_point):
            continue
        if len(mount_point) > len(best_match):
            best_match = mount_point
            best_type = fs_type
    _logger.debug("Detected filesystem_type=%s for path=%s", best_type, path)
    return best_type


def _parse_mountinfo_line(line: str) -> tuple[str | None, str | None]:
    if " - " not in line:
        return None, None
    pre_separator, post_separator = line.split(" - ", maxsplit=1)
    pre_fields = pre_separator.split()
    post_fields = post_separator.split()
    if len(pre_fields) <= _MOUNTINFO_MOUNT_POINT_INDEX or not post_fields:
        return None, None
    mount_point = pre_fields[_MOUNTINFO_MOUNT_POINT_INDEX].replace("\\040", " ")
    fs_type = post_fields[0]
    return mount_point, fs_type


def _path_is_under_mountpoint(path: Path, mount_point: str) -> bool:
    mount_path = Path(mount_point)
    if path == mount_path:
        return True
    return mount_path in path.parents


def _supports_inotify(path: Path, *, recursive: bool) -> bool:
    probe_path = path / f"{_PROBE_FILE_NAME_PREFIX}{time.time_ns()}"
    _logger.info("Probing inotify support for path=%s recursive=%s probe_path=%s", path, recursive, probe_path)
    handler = _ProbeEventHandler(probe_path)
    observer = InotifyObserver()
    try:
        observer.schedule(handler, str(path), recursive=recursive)
        observer.start()
        _logger.debug("Writing probe file at %s", probe_path)
        probe_path.write_text("probe", encoding="utf-8")
        _logger.debug("Deleting probe file at %s", probe_path)
        probe_path.unlink()
        supported = _wait_for_probe_event(handler)
        _logger.info("Inotify probe result for path=%s supported=%s", path, supported)
        return supported
    except OSError:
        _logger.exception("Inotify probe failed for path=%s", path)
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
    _logger.debug("Probe timed out after %.2f seconds", _PROBE_TIMEOUT_SECONDS)
    return False


def _unlink_probe_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
