#!/usr/bin/env bash
# Verifies that the destination is chosen by environment variables alone, and that a bad destination
# does not take the Collector down.
#
#   bash docker/observability/scripts/check_destination.sh
#
# Runs the standalone stack (it recreates the Collector a few times and stops the Loki for a while) and leaves it
# running with the local destination. It does not touch the main dev compose, but it cannot run next to the
# combined mode: bring that down first. Never uses `down -v`.
#
# Proves: OBS-33 (empty variables mean local), OBS-34 (path and header per signal), OBS-35 (same config file),
# OBS-36 (unreachable destination: still running, retrying) and OBS-57 (one backend down, the others keep working).

set -u -o pipefail
cd "$(dirname "$0")/../../.." || exit 2

unset OBS_DIR OBS_TRACES_ENDPOINT OBS_METRICS_ENDPOINT OBS_LOGS_ENDPOINT OBS_OTLP_AUTH_HEADER

OBS="docker compose -f docker/observability/docker-compose.observability.yml"
SCRIPTS="docker/observability/scripts"
CONFIG="docker/observability/otel/config.yaml"
COLLECTOR=hairmatch_obs_otel_collector
CAPTURE=hairmatch_obs_otlp_capture
AUTH='Basic dGVzdDp0ZXN0'   # base64("test:test"), a dummy: the capture server accepts anything

PASSES=0
FAILS=0
pass() { PASSES=$((PASSES + 1)); echo "PASS $1: $2"; }
fail() { FAILS=$((FAILS + 1)); echo "FAIL $1: $2"; }
q() { "$@" >/tmp/check_destination.out 2>&1 || { tail -5 /tmp/check_destination.out | sed 's/^/    | /'; return 1; }; }

py() { PYTHONPATH="$SCRIPTS" python3 "$@"; }

# Everything below leaves the stack on the local destination, with the capture server gone and the Loki up.
restore() {
  echo "== restoring the local destination"
  q $OBS --profile verify rm -sf otlp-capture
  q $OBS start loki
  q $OBS up -d
  if py "$SCRIPTS/smoke.py" --mode standalone >/tmp/check_destination_smoke.out 2>&1; then
    pass restore "smoke.py --mode standalone passes again after the restore ($(grep -c '^PASS' /tmp/check_destination_smoke.out) checks)"
  else
    fail restore "smoke.py --mode standalone fails after the restore"; grep '^FAIL' /tmp/check_destination_smoke.out | head -5 | sed 's/^/    | /'
  fi
  echo "check_destination: $PASSES PASS, $FAILS FAIL"
}
trap 'rc=$?; restore; exit $(( rc != 0 || FAILS != 0 ))' EXIT

wait_running() { # <container> <seconds>
  local deadline=$((SECONDS + $2))
  while [ $SECONDS -lt $deadline ]; do
    [ "$(docker inspect -f '{{.State.Status}}' "$1" 2>/dev/null)" = running ] && return 0
    sleep 2
  done
  return 1
}

send_all() { # send a span, a log and a metric straight to the Collector on 127.0.0.1:4318
  py - "$1" <<'PY'
import sys, uuid
import smoke
service = sys.argv[1]
trace = uuid.uuid4().hex
statuses = [smoke.send_traces(service=service, trace_id=trace)[0],
            smoke.send_logs([{"body": "destination check", "trace_id": trace}], service=service)[0],
            smoke.send_histogram(service=service, trace_id=trace)[0]]
sys.exit(0 if statuses == [200, 200, 200] else 1)
PY
}

# sha256 of the config file the running Collector uses (the image has no shell: copy it out).
container_config_sha() {
  local tmp; tmp=$(mktemp)
  docker cp "$COLLECTOR":/etc/otelcol/config.yaml "$tmp" >/dev/null 2>&1 && sha256sum "$tmp" | cut -d' ' -f1
  rm -f "$tmp"
}
config_before=$(sha256sum "$CONFIG" | cut -d' ' -f1)
SHAS_SEEN=""

echo "== 0. standalone with the local destination"
if ! q $OBS up -d; then fail setup "the standalone stack did not come up (is the combined mode still running?)"; exit 1; fi
wait_running "$COLLECTOR" 60 || { fail setup "the Collector is not running"; exit 1; }

echo "== 1. variables defined and empty mean the local destination (OBS-33)"
if OBS_TRACES_ENDPOINT= OBS_METRICS_ENDPOINT= OBS_LOGS_ENDPOINT= OBS_OTLP_AUTH_HEADER= q $OBS up -d \
  && wait_running "$COLLECTOR" 60 && sleep 3 \
  && py "$SCRIPTS/smoke.py" --mode standalone --only signals >/tmp/check_destination_empty.out 2>&1; then
  pass OBS-33 "with the four OBS_* variables set and empty, the signals still reach Tempo, Loki and Prometheus"
else
  fail OBS-33 "empty OBS_* variables did not fall back to the local destination"; grep '^FAIL' /tmp/check_destination_empty.out | head -5 | sed 's/^/    | /'
fi

echo "== 2. switch the destination to the capture server (OBS-34)"
if OBS_TRACES_ENDPOINT=http://otlp-capture:8080/t/v1/traces \
   OBS_METRICS_ENDPOINT=http://otlp-capture:8080/m/v1/metrics \
   OBS_LOGS_ENDPOINT=http://otlp-capture:8080/l/v1/logs \
   OBS_OTLP_AUTH_HEADER="$AUTH" q $OBS --profile verify up -d otlp-capture otel-collector \
   && wait_running "$COLLECTOR" 60 && wait_running "$CAPTURE" 60; then
  sleep 3
  SHAS_SEEN="$SHAS_SEEN $(container_config_sha)"
  send_all "obs-dest-$RANDOM" || fail OBS-34 "the Collector refused the test signals"
  sleep 12   # the batch processor flushes within seconds
  captured=$(docker logs "$CAPTURE" 2>&1)
  for entry in "t/v1/traces" "m/v1/metrics" "l/v1/logs"; do
    if echo "$captured" | grep -qF "POST /$entry auth=$AUTH"; then
      pass OBS-34 "the capture server got POST /$entry with Authorization: $AUTH"
    else
      fail OBS-34 "no POST /$entry with the expected Authorization"; echo "$captured" | tail -5 | sed 's/^/    | /'
    fi
  done
  # Each signal only reaches its own endpoint.
  if echo "$captured" | grep -E 'POST /(t|m|l)/' | awk '{print $2}' | sort -u | grep -qvE '^/(t/v1/traces|m/v1/metrics|l/v1/logs)$'; then
    fail OBS-34 "a signal reached an endpoint that is not its own"
  else
    pass OBS-34 "no signal reached the endpoint of another signal"
  fi
else
  fail OBS-34 "could not start the Collector pointing at the capture server"
fi

echo "== 3. destination that does not exist (OBS-36)"
if OBS_TRACES_ENDPOINT=http://nao-existe.invalid/v1/traces \
   OBS_METRICS_ENDPOINT=http://nao-existe.invalid/v1/metrics \
   OBS_LOGS_ENDPOINT=http://nao-existe.invalid/v1/logs \
   OBS_OTLP_AUTH_HEADER="$AUTH" q $OBS up -d otel-collector && wait_running "$COLLECTOR" 60; then
  sleep 3
  SHAS_SEEN="$SHAS_SEEN $(container_config_sha)"
  send_all "obs-dest-bad-$RANDOM" || fail OBS-36 "the Collector refused signals while the destination is down"
  start=$SECONDS
  alive=1
  while [ $((SECONDS - start)) -lt 60 ]; do
    [ "$(docker inspect -f '{{.State.Status}}' "$COLLECTOR")" = running ] || { alive=0; break; }
    sleep 5
  done
  restarts=$(docker inspect -f '{{.RestartCount}}' "$COLLECTOR")
  if [ $alive = 1 ] && [ "$restarts" = 0 ]; then
    pass OBS-36 "the Collector stays running for 60 s with an unreachable destination, with no restarts"
  else
    fail OBS-36 "the Collector did not survive an unreachable destination (running=$alive, restarts=$restarts)"
  fi
  # The unsent data is held in the persistent queue (file_storage), one queue file per signal.
  qdir=$(mktemp -d)
  docker cp "$COLLECTOR":/var/lib/otelcol/queue "$qdir/" >/dev/null 2>&1
  queued=$(find "$qdir" -type f -size +0 | wc -l)
  rm -rf "$qdir"
  if [ "$queued" -ge 3 ]; then
    pass OBS-36 "the unsent data sits in the on-disk queue ($queued queue files, one per signal)"
  else
    fail OBS-36 "the on-disk queue has $queued non-empty files, expected at least 3"
  fi
  collector_log=$(docker logs "$COLLECTOR" 2>&1)   # a variable, not a pipe: grep -q would SIGPIPE docker under pipefail
  if grep -qi 'will retry' <<<"$collector_log"; then
    pass OBS-36 "the Collector logs that it will retry the failed export"
  else
    fail OBS-36 "no retry in the Collector log"
  fi
else
  fail OBS-36 "could not start the Collector pointing at a missing host"
fi

echo "== 4. one backend down, the others keep working (OBS-57)"
q $OBS --profile verify rm -sf otlp-capture
q $OBS up -d otel-collector && wait_running "$COLLECTOR" 60
SHAS_SEEN="$SHAS_SEEN $(container_config_sha)"

# backend_down <loki|tempo|prometheus>: stop it, send all three signals, check the two other backends receive theirs,
# then start it again and check what was sent while it was down is delivered (retry).
backend_down() {
  local backend="$1" svc="obs-dest-$1-down-$RANDOM" trace log_trace
  trace=$(python3 -c 'import uuid; print(uuid.uuid4().hex)'); log_trace=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
  if ! q $OBS stop "$backend"; then fail OBS-57 "could not stop $backend"; return; fi
  sleep 3
  py - "$svc" "$trace" "$log_trace" "$backend" send <<'PY'
import sys
import smoke
service, trace, log_trace, backend, phase = sys.argv[1:6]
ok = smoke.send_traces(service=service, trace_id=trace)[0] == 200
ok &= smoke.send_logs([{"body": f"sent while {backend} is down {service}", "trace_id": log_trace}], service=service)[0] == 200
ok &= smoke.send_histogram(service=service)[0] == 200
seen = {
    "tempo": lambda: smoke.tempo_trace(trace),
    "loki": lambda: smoke.loki_lines(f'{{service_name="{service}"}}'),
    "prometheus": lambda: smoke.prom_query(f'http_server_request_duration_seconds_count{{job="{service}"}}'),
}
others = {k: bool(smoke.wait_for(fn, 30)) for k, fn in seen.items() if k != backend}
print(f"accepted={ok} others={others}")
sys.exit(0 if ok and all(others.values()) else 1)
PY
  if [ $? -eq 0 ]; then
    pass OBS-57 "with $backend stopped, the other two backends still receive their new signals"
  else
    fail OBS-57 "signals for the other backends stopped arriving while $backend was down"
  fi
  if [ "$(docker inspect -f '{{.State.Status}} {{.RestartCount}}' "$COLLECTOR")" = "running 0" ]; then
    pass OBS-57 "the Collector kept running, with no restarts, while $backend was down"
  else
    fail OBS-57 "the Collector restarted or stopped while $backend was down"
  fi
  q $OBS start "$backend"
  py - "$svc" "$trace" "$backend" <<'PY'
import sys
import smoke
service, trace, backend = sys.argv[1:4]
seen = {
    "tempo": lambda: smoke.tempo_trace(trace),
    "loki": lambda: [x for x in smoke.loki_lines(f'{{service_name="{service}"}}') if x[0].startswith("sent while")],
    "prometheus": lambda: smoke.prom_query(f'http_server_request_duration_seconds_count{{job="{service}"}}'),
}
sys.exit(0 if smoke.wait_for(seen[backend], 150, 3) else 1)
PY
  if [ $? -eq 0 ]; then
    pass OBS-57 "what was sent while $backend was down is delivered after it is back (retry)"
  else
    fail OBS-57 "what was sent while $backend was down never arrived"
  fi
}
for backend in loki tempo prometheus; do backend_down "$backend"; done

config_after=$(sha256sum "$CONFIG" | cut -d' ' -f1)
distinct=$(printf '%s\n' $SHAS_SEEN | sort -u | tr '\n' ' ')
if [ "$config_before" = "$config_after" ] && [ "$distinct" = "$config_before " ] && [ "$(printf '%s\n' $SHAS_SEEN | wc -l)" -ge 3 ]; then
  pass OBS-35 "the Collector ran the same config.yaml ($config_before) in the capture, bad-destination and backend-down scenarios"
else
  fail OBS-35 "the Collector config differed between scenarios (repo $config_before, containers: $distinct)"
fi
