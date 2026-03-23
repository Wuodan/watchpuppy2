from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from watchdog.events import DirCreatedEvent

from watchpuppy2._observer import _ProbeEventHandler, _supports_inotify, create_observer


class TestCreateObserver(TestCase):
    @patch("watchpuppy2._observer.InotifyObserver")
    def test_create_observer_inotify(self, inotify_observer: Mock) -> None:
        observer = Mock()
        inotify_observer.return_value = observer

        result = create_observer(Path("/tmp/example"), recursive=True, mode="inotify")

        self.assertIs(observer, result)
        inotify_observer.assert_called_once_with()

    @patch("watchpuppy2._observer.PollingObserver")
    def test_create_observer_polling(self, polling_observer: Mock) -> None:
        observer = Mock()
        polling_observer.return_value = observer

        result = create_observer(Path("/tmp/example"), recursive=True, mode="polling")

        self.assertIs(observer, result)
        polling_observer.assert_called_once_with(timeout=1.0)

    def test_create_observer_unsupported_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported mode: invalid"):
            create_observer(Path("/tmp/example"), recursive=True, mode="invalid")

    @patch("watchpuppy2._observer._supports_inotify")
    @patch("watchpuppy2._observer.InotifyObserver")
    def test_create_observer_auto_uses_inotify_when_probe_succeeds(
        self,
        inotify_observer: Mock,
        supports_inotify: Mock,
    ) -> None:
        supports_inotify.return_value = True
        observer = Mock()
        inotify_observer.return_value = observer

        result = create_observer(Path("/tmp/example"), recursive=False, mode="auto")

        self.assertIs(observer, result)
        supports_inotify.assert_called_once_with(Path("/tmp/example"), recursive=False)
        inotify_observer.assert_called_once_with()

    @patch("watchpuppy2._observer._supports_inotify")
    @patch("watchpuppy2._observer.PollingObserver")
    def test_create_observer_auto_uses_polling_when_probe_fails(
        self,
        polling_observer: Mock,
        supports_inotify: Mock,
    ) -> None:
        supports_inotify.return_value = False
        observer = Mock()
        polling_observer.return_value = observer

        result = create_observer(Path("/tmp/example"), recursive=False, mode="auto")

        self.assertIs(observer, result)
        supports_inotify.assert_called_once_with(Path("/tmp/example"), recursive=False)
        polling_observer.assert_called_once_with(timeout=1.0)


class TestProbeEventHandler(TestCase):
    def test_seen(self) -> None:
        handler = _ProbeEventHandler(Path("/tmp/probe"))

        self.assertFalse(handler.seen)

    def test_on_any_event(self) -> None:
        handler = _ProbeEventHandler(Path("/tmp/probe"))

        handler.on_any_event(DirCreatedEvent("/tmp/probe"))

        self.assertTrue(handler.seen)

    def test_on_any_event_ignores_other_paths(self) -> None:
        handler = _ProbeEventHandler(Path("/tmp/probe"))

        handler.on_any_event(DirCreatedEvent("/tmp/other"))

        self.assertFalse(handler.seen)


class TestSupportsInotify(TestCase):
    @patch("watchpuppy2._observer._wait_for_probe_event")
    @patch("watchpuppy2._observer.InotifyObserver")
    def test_supports_inotify(self, inotify_observer: Mock, wait_for_probe_event: Mock) -> None:
        wait_for_probe_event.return_value = True
        observer = Mock()
        inotify_observer.return_value = observer

        with TemporaryDirectory() as tmp_dir:
            result = _supports_inotify(Path(tmp_dir), recursive=True)

        self.assertTrue(result)
        observer.schedule.assert_called_once()
        observer.start.assert_called_once_with()
        observer.stop.assert_called_once_with()
        observer.join.assert_called_once_with()

    @patch("watchpuppy2._observer.InotifyObserver")
    def test_supports_inotify_handles_os_error(self, inotify_observer: Mock) -> None:
        observer = Mock()
        observer.schedule.side_effect = OSError("not supported")
        inotify_observer.return_value = observer

        with TemporaryDirectory() as tmp_dir:
            result = _supports_inotify(Path(tmp_dir), recursive=False)

        self.assertFalse(result)
        observer.stop.assert_called_once_with()
        observer.join.assert_called_once_with()
