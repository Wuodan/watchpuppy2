import time

from _mount_share import mount_share
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class _LoggingEventHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        print(
            f"watchdog event_type={event.event_type} "
            f"src_path={event.src_path!r} dest_path={event.dest_path!r}"
        )


def main() -> int:
    watch_path = mount_share()
    observer = Observer()
    handler = _LoggingEventHandler()
    observer.schedule(handler, str(watch_path), recursive=True)
    print(f"watchdog observer_class={type(observer).__name__} path={watch_path}")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
