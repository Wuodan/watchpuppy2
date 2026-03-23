import logging
import time

from _mount_share import mount_share
from watchdog.events import FileSystemEvent, FileSystemEventHandler

from watchpuppy2 import watch


class _LoggingEventHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        print(
            f"watchpuppy2 event_type={event.event_type} "
            f"src_path={event.src_path!r} dest_path={event.dest_path!r}"
        )


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(name)s %(levelname)s %(message)s",
    )
    watch_path = mount_share()
    handler = _LoggingEventHandler()
    observer = watch(watch_path, handler, recursive=True)
    print(f"watchpuppy2 observer_class={type(observer).__name__} path={watch_path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
