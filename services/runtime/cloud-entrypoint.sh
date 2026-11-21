#!/bin/sh
set -eu
cd /app
pids=""
cleanup() {
  for pid in $pids; do kill "$pid" 2>/dev/null || true; done
  for pid in $pids; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM
if [ -z "$SAM_WORKER_BIND_HOST" ]; then export SAM_WORKER_BIND_HOST=127.0.0.1; fi
for role in ceo coo research strategy cto design video content marketing platforms finance quality; do
  python service.py "$role" &
  pids="$pids $!"
done
python - <<'PY'
import time, urllib.request
ports = range(8790, 8802)
for attempt in range(60):
    ready = 0
    for port in ports:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                if response.status == 200:
                    ready += 1
        except Exception:
            pass
    if ready == 12:
        break
    time.sleep(1)
else:
    raise SystemExit(f"Only {ready}/12 workers became healthy")
PY
python coordinator.py &
coordinator_pid=$!
wait "$coordinator_pid"