# Linux Bind Mount Demo

This is the control case for the CIFS share demo.

It uses the same three roles:

- `watchdog`: plain `watchdog.Observer()`
- `watchpuppy2`: `watchpuppy2.watch(...)`
- `writer`: creates, modifies, renames, and deletes files

But here the shared path is a normal Linux bind mount, not a CIFS client mount.

## Run

From this directory:

```bash
docker compose up --build
```

## Expected Result

- `watchdog` prints `observer_class=InotifyObserver`
- `watchpuppy2` probe logs show local inotify events
- `watchpuppy2` selects `InotifyObserver`
- both `watchdog` and `watchpuppy2` print events from the separate writer

This is the reverse test for the CIFS demo. It shows the same watcher pattern on
a normal Linux-backed shared directory where inotify should work as expected.
