#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

scenario="${1:?scenario is required}"
artifacts_dir="${2:?artifacts dir is required}"

mkdir -p "$artifacts_dir"

compose_file=""
expected_watchdog_observer=""
expected_watchpuppy2_observer=""
expected_watchdog_event="false"
expected_watchpuppy2_event="false"
expected_watchpuppy2_log=""

case "$scenario" in
  linux-bind-mount)
    compose_file="demo/linux_bind_mount/docker-compose.yml"
    expected_watchdog_observer="InotifyObserver"
    expected_watchpuppy2_observer="InotifyObserver"
    expected_watchdog_event="true"
    expected_watchpuppy2_event="true"
    expected_watchpuppy2_log="Selected InotifyObserver"
    ;;
  linux-cifs-share)
    compose_file="demo/cifs_share/docker-compose.yml"
    expected_watchdog_observer="InotifyObserver"
    expected_watchpuppy2_observer="PollingObserver"
    expected_watchdog_event="false"
    expected_watchpuppy2_event="true"
    expected_watchpuppy2_log="Selected PollingObserver"
    ;;
  *)
    echo "Unsupported scenario: $scenario" >&2
    exit 1
    ;;
esac

project_name="proof_${scenario//-/_}"
log_file="$artifacts_dir/${scenario}.log"
summary_file="$artifacts_dir/${scenario}.json"
report_file="$artifacts_dir/${scenario}.md"

cleanup() {
  docker compose -p "$project_name" -f "$compose_file" down --volumes --remove-orphans >/dev/null 2>&1 || true
}

trap cleanup EXIT

docker compose -p "$project_name" -f "$compose_file" up --build -d
sleep 20
docker compose -p "$project_name" -f "$compose_file" logs --no-color >"$log_file"

watchdog_observer=$(grep -o "watchdog observer_class=[^ ]*" "$log_file" | tail -n1 | cut -d= -f2 || true)
watchpuppy2_observer=$(grep -o "watchpuppy2 observer_class=[^ ]*" "$log_file" | tail -n1 | cut -d= -f2 || true)

watchdog_event_seen="false"
watchpuppy2_event_seen="false"

if grep -q "^watchdog-.*watchdog event_type=" "$log_file"; then
  watchdog_event_seen="true"
fi

if grep -q "^watchpuppy2-.*watchpuppy2 event_type=" "$log_file"; then
  watchpuppy2_event_seen="true"
fi

if [[ "$watchdog_observer" != "$expected_watchdog_observer" ]]; then
  echo "Unexpected watchdog observer for $scenario: $watchdog_observer" >&2
  exit 1
fi

if [[ "$watchpuppy2_observer" != "$expected_watchpuppy2_observer" ]]; then
  echo "Unexpected watchpuppy2 observer for $scenario: $watchpuppy2_observer" >&2
  exit 1
fi

if [[ "$watchdog_event_seen" != "$expected_watchdog_event" ]]; then
  echo "Unexpected watchdog event visibility for $scenario: $watchdog_event_seen" >&2
  exit 1
fi

if [[ "$watchpuppy2_event_seen" != "$expected_watchpuppy2_event" ]]; then
  echo "Unexpected watchpuppy2 event visibility for $scenario: $watchpuppy2_event_seen" >&2
  exit 1
fi

if ! grep -q "$expected_watchpuppy2_log" "$log_file"; then
  echo "Missing watchpuppy2 selection log for $scenario: $expected_watchpuppy2_log" >&2
  exit 1
fi

cat >"$summary_file" <<EOF
{
  "scenario": "$scenario",
  "watchdog_observer": "$watchdog_observer",
  "watchpuppy2_observer": "$watchpuppy2_observer",
  "watchdog_event_seen": $watchdog_event_seen,
  "watchpuppy2_event_seen": $watchpuppy2_event_seen
}
EOF

cat >"$report_file" <<EOF
# Filesystem Proof Result

| Scenario | Watchdog observer | Watchpuppy2 observer | Watchdog saw events | Watchpuppy2 saw events | Result |
| --- | --- | --- | --- | --- | --- |
| $scenario | $watchdog_observer | $watchpuppy2_observer | $watchdog_event_seen | $watchpuppy2_event_seen | pass |
EOF
