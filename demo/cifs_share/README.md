# CIFS Share Demo

This demo is a Linux-host proxy for the "shared filesystem into a Linux
container" problem.

It uses a Samba server container and three Linux client containers:

- `watchdog`: plain `watchdog.Observer()`
- `watchpuppy2`: `watchpuppy2.watch(...)`
- `writer`: modifies the same share through a separate CIFS client mount

The point is to show this pattern:

- plain `watchdog.Observer()` resolves to Linux inotify inside the container
- the watched path is actually a shared filesystem mount
- changes coming through another client can be missed
- `watchpuppy2` falls back to polling and still reacts

## Prerequisites

- Linux host
- Docker Engine
- kernel support for CIFS mounts on the host running Docker
- containers allowed to mount CIFS shares

This demo uses `cap_add: SYS_ADMIN` and mounts the share inside each client
container. It is intentionally a demo, not a production container setup.

## Run

From this directory:

```bash
docker compose up --build
```

## Expected Result

- `watchdog` prints `observer_class=InotifyObserver`
- `writer` creates, modifies, renames, and deletes files on the CIFS share
- `watchdog` may stay silent for those changes
- `watchpuppy2` should print file events because it switches to polling

## Why This Demo Exists

It avoids requiring a Windows host just to demonstrate the failure mode.
It is still a proxy, not a literal reproduction of Docker Desktop on Windows.
