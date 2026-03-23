import subprocess
import time
from pathlib import Path

_MOUNT_POINT = Path("/mnt/share")
_REMOTE = "//samba/share"
_MOUNT_OPTIONS = "username=demo,password=demo,vers=3.0"
_READY_TIMEOUT_SECONDS = 30


def mount_share() -> Path:
    _MOUNT_POINT.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + _READY_TIMEOUT_SECONDS
    last_mount_error = ""
    while time.monotonic() < deadline:
        mounted, last_mount_error = _try_mount()
        if mounted:
            return _MOUNT_POINT
        time.sleep(1)
    raise RuntimeError(f"Could not mount CIFS demo share: {last_mount_error}")


def _try_mount() -> tuple[bool, str]:
    result = subprocess.run(
        [
            "mount",
            "-t",
            "cifs",
            "-o",
            _MOUNT_OPTIONS,
            _REMOTE,
            str(_MOUNT_POINT),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, ""
    stderr = result.stderr.strip()
    stdout = result.stdout.strip()
    error = stderr or stdout or f"mount exited with status {result.returncode}"
    return _already_mounted(), error


def _already_mounted() -> bool:
    mounts = Path("/proc/mounts").read_text(encoding="utf-8")
    return str(_MOUNT_POINT) in mounts
