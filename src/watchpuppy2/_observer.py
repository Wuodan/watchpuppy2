import logging
import threading
import time
from pathlib import Path

import psutil
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.api import BaseObserver
from watchdog.observers.inotify import InotifyObserver
from watchdog.observers.polling import PollingObserver

_logger = logging.getLogger(__name__)
_PROBE_FILE_NAME_PREFIX = ".watchpuppy2-probe-"
_PROBE_TIMEOUT_SECONDS = 1.0
_PROBE_WAIT_INTERVAL_SECONDS = 0.01
_POLLING_TIMEOUT_SECONDS = 1.0
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
    try:
        partitions = psutil.disk_partitions(all=True)
    except OSError:
        _logger.exception("Could not inspect disk partitions for path=%s", path)
        return None
    partitions_by_depth = sorted(
        partitions,
        key=lambda partition: len(Path(partition.mountpoint).parts),
        reverse=True,
    )
    for partition in partitions_by_depth:
        partition_mountpoint = Path(partition.mountpoint)
        if not _path_is_under_mountpoint(resolved_path, partition_mountpoint):
            continue
        _logger.debug("Detected filesystem_type=%s for path=%s", partition.fstype, path)
        return partition.fstype
    _logger.debug("Detected filesystem_type=None for path=%s", path)
    return None


def _path_is_under_mountpoint(path: Path, mount_path: Path) -> bool:
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
