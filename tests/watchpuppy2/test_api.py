from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from watchdog.events import FileSystemEventHandler

from watchpuppy2.api import watch


class _Handler(FileSystemEventHandler):
    pass


class TestWatch(TestCase):
    @patch("watchpuppy2.api.create_observer")
    def test_watch(self, create_observer: Mock) -> None:
        observer = Mock()
        create_observer.return_value = observer
        handler = _Handler()

        result = watch("/tmp/example", handler, recursive=False)

        self.assertIs(observer, result)
        create_observer.assert_called_once_with(Path("/tmp/example"), recursive=False)
        observer.schedule.assert_called_once_with(handler, "/tmp/example", recursive=False)
        observer.start.assert_called_once_with()
