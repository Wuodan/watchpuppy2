from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers.api import BaseObserver

from watchpuppy2._observer import create_observer


def watch(
    path: str | Path,
    handler: FileSystemEventHandler,
    *,
    recursive: bool = True,
) -> BaseObserver:
    watch_path = Path(path)
    observer = create_observer(watch_path, recursive=recursive)
    observer.schedule(handler, str(watch_path), recursive=recursive)
    observer.start()
    return observer
