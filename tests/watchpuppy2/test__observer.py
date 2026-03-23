from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from watchdog.events import DirCreatedEvent

from watchpuppy2._observer import (
    _filesystem_type,
    _parse_mountinfo_line,
    _path_is_under_mountpoint,
    _ProbeEventHandler,
    _supports_inotify,
    create_observer,
)


class TestCreateObserver(TestCase):
    @patch("watchpuppy2._observer._filesystem_type")
    @patch("watchpuppy2._observer.PollingObserver")
    def test_create_observer_uses_polling_for_cifs(
        self,
        polling_observer: Mock,
        filesystem_type: Mock,
    ) -> None:
        filesystem_type.return_value = "cifs"
        observer = Mock()
        polling_observer.return_value = observer

        result = create_observer(Path("/tmp/example"), recursive=False)

        self.assertIs(observer, result)
        filesystem_type.assert_called_once_with(Path("/tmp/example"))
        polling_observer.assert_called_once_with(timeout=1.0)

    @patch("watchpuppy2._observer._filesystem_type")
    @patch("watchpuppy2._observer._supports_inotify")
    @patch("watchpuppy2._observer.InotifyObserver")
    def test_create_observer_uses_inotify_when_probe_succeeds(
        self,
        inotify_observer: Mock,
        supports_inotify: Mock,
        filesystem_type: Mock,
    ) -> None:
        filesystem_type.return_value = "ext4"
        supports_inotify.return_value = True
        observer = Mock()
        inotify_observer.return_value = observer

        result = create_observer(Path("/tmp/example"), recursive=False)

        self.assertIs(observer, result)
        filesystem_type.assert_called_once_with(Path("/tmp/example"))
        supports_inotify.assert_called_once_with(Path("/tmp/example"), recursive=False)
        inotify_observer.assert_called_once_with()

    @patch("watchpuppy2._observer._filesystem_type")
    @patch("watchpuppy2._observer._supports_inotify")
    @patch("watchpuppy2._observer.PollingObserver")
    def test_create_observer_uses_polling_when_probe_fails(
        self,
        polling_observer: Mock,
        supports_inotify: Mock,
        filesystem_type: Mock,
    ) -> None:
        filesystem_type.return_value = "ext4"
        supports_inotify.return_value = False
        observer = Mock()
        polling_observer.return_value = observer

        result = create_observer(Path("/tmp/example"), recursive=False)

        self.assertIs(observer, result)
        filesystem_type.assert_called_once_with(Path("/tmp/example"))
        supports_inotify.assert_called_once_with(Path("/tmp/example"), recursive=False)
        polling_observer.assert_called_once_with(timeout=1.0)


class TestFilesystemType(TestCase):
    @patch("pathlib.Path.read_text")
    def test_filesystem_type(self, read_text: Mock) -> None:
        read_text.return_value = (
            "38 33 0:34 / / rw,relatime - overlay overlay rw\n"
            "60 38 0:50 / /mnt/share rw,relatime - cifs //samba/share rw\n"
        )

        result = _filesystem_type(Path("/mnt/share/example.txt"))

        self.assertEqual("cifs", result)

    @patch("pathlib.Path.read_text")
    def test_filesystem_type_returns_none_on_read_error(self, read_text: Mock) -> None:
        read_text.side_effect = OSError("boom")

        result = _filesystem_type(Path("/mnt/share/example.txt"))

        self.assertIsNone(result)

    def test_parse_mountinfo_line(self) -> None:
        result = _parse_mountinfo_line("60 38 0:50 / /mnt/share rw,relatime - cifs //samba/share rw")

        self.assertEqual(("/mnt/share", "cifs"), result)

    def test_parse_mountinfo_line_returns_none_for_invalid_input(self) -> None:
        result = _parse_mountinfo_line("invalid")

        self.assertEqual((None, None), result)

    def test_path_is_under_mountpoint(self) -> None:
        result = _path_is_under_mountpoint(Path("/mnt/share/example.txt"), "/mnt/share")

        self.assertTrue(result)

    def test_path_is_under_mountpoint_returns_false_for_other_mount(self) -> None:
        result = _path_is_under_mountpoint(Path("/mnt/share/example.txt"), "/other")

        self.assertFalse(result)


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
