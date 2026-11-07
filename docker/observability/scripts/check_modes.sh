#!/usr/bin/env bash
# Verifies the two ways of bringing the stack up (standalone and combined) against the real main compose.
#
#   CONFIRM=1 bash docker/observability/scripts/check_modes.sh
#
# It STOPS AND STARTS the main dev compose (db, localstack, ministack, django, pgadmin) and the observability
# stack. It never uses `down -v`, so no volume is touched. It records the state of the main compose before it
# starts and puts it back at the end (also when a step fails).
#
# Proves: OBS-01, OBS-03, OBS-04, OBS-05, OBS-10, OBS-12 (effective mounts), OBS-43 (via smoke --mode combined), OBS-60.

if [ "${CONFIRM:-}" != "1" ]; then
  echo "This script stops and starts the main dev compose (never with -v) and the observability stack."
  echo "Run it again with CONFIRM=1 to go on."
  exit 2
fi

set -u -o pipefail
cd "$(dirname "$0")/../../.." || exit 2

# The shell must not leak destination overrides into the runs below.
unset OBS_DIR OBS_TRACES_ENDPOINT OBS_METRICS_ENDPOINT OBS_LOGS_ENDPOINT OBS_OTLP_AUTH_HEADER

MAIN="docker compose -f docker/docker-compose.yml"
OBS="docker compose -f docker/observability/docker-compose.observability.yml"
BOTH="docker compose -f docker/docker-compose.yml -f docker/observability/docker-compose.observability.yml"
OBS_SERVICES="otel-collector loki tempo prometheus pyroscope alloy grafana postgres-exporter"
SCRIPTS="docker/observability/scripts"

WORK="$(mktemp -d)"
PASSES=0
FAILS=0

pass() { PASSES=$((PASSES + 1)); echo "PASS $1: $2"; }
fail() { FAILS=$((FAILS + 1)); echo "FAIL $1: $2"; }
# check <req> <message> <command...>: PASS when the command succeeds.
check() { local req="$1" msg="$2"; shift 2; if "$@" >/dev/null 2>&1; then pass "$req" "$msg"; else fail "$req" "$msg"; fi; }

# Quiet compose: its progress goes to stderr and is noise here.
q() { "$@" >"$WORK/last.out" 2>&1; local rc=$?; [ $rc -ne 0 ] && tail -5 "$WORK/last.out" | sed 's/^/    | /'; return $rc; }

# --- state of the main compose -------------------------------------------------------------------------------------

main_states() { $MAIN ps -a --format '{{.Service}} {{.State}}' 2>/dev/null | sort; }

main_states >"$WORK/initial_states.txt"
echo "== main compose state before the run"
sed 's/^/   /' "$WORK/initial_states.txt"

restore_main() {
  echo "== restoring the main compose to the state it had before the run"
  q $BOTH down --remove-orphans
  q $OBS down
  q $MAIN up -d
  # Anything that was not running before is stopped again, so the final state matches the initial one.
  while read -r service state; do
    [ "$state" != "running" ] && q $MAIN stop "$service"
  done <"$WORK/initial_states.txt"
  sleep 5
  main_states >"$WORK/final_states.txt"
  if diff -q "$WORK/initial_states.txt" "$WORK/final_states.txt" >/dev/null; then
    pass restore "the main compose ends in the state it started in"
  else
    fail restore "the main compose state differs from the start"; diff "$WORK/initial_states.txt" "$WORK/final_states.txt" | sed 's/^/    | /'
  fi
}

finish() {
  restore_main
  rm -rf "$WORK"
  echo "check_modes: $PASSES PASS, $FAILS FAIL"
  [ "$FAILS" -eq 0 ]
}
trap 'exit_code=$?; finish; exit $(( exit_code != 0 || FAILS != 0 ))' EXIT

# --- helpers -------------------------------------------------------------------------------------------------------

# wait_obs <compose cmd>: every observability service running, within 60 s.
wait_obs_running() {
  local compose="$1" deadline=$((SECONDS + 60))
  while [ $SECONDS -lt $deadline ]; do
    local running
    running=$($compose ps --format '{{.Service}} {{.State}}' 2>/dev/null | grep -E "^($(echo $OBS_SERVICES | tr ' ' '|')) running$" | wc -l)
    [ "$running" -eq 8 ] && return 0
    sleep 2
  done
  return 1
}

# no_restarts <compose cmd>: no observability container has restarted.
no_restarts() {
  local compose="$1" id
  for service in $OBS_SERVICES; do
    id=$($compose ps -q "$service" 2>/dev/null) || return 1
    [ -n "$id" ] || return 1
    [ "$(docker inspect -f '{{.RestartCount}}' "$id")" = "0" ] || return 1
  done
}

# wait_main_healthy: db, localstack and ministack healthy and django running, within 300 s.
wait_main_ready() {
  local deadline=$((SECONDS + 300))
  while [ $SECONDS -lt $deadline ]; do
    if [ "$(docker inspect -f '{{.State.Health.Status}}' hairmatch_db 2>/dev/null)" = "healthy" ] \
      && [ "$(docker inspect -f '{{.State.Health.Status}}' hairmatch_localstack 2>/dev/null)" = "healthy" ] \
      && [ "$(docker inspect -f '{{.State.Health.Status}}' hairmatch_ministack 2>/dev/null)" = "healthy" ] \
      && [ "$(docker inspect -f '{{.State.Status}}' hairmatch_backend 2>/dev/null)" = "running" ]; then
      return 0
    fi
    sleep 3
  done
  return 1
}

main_services_unchanged() { # compares against a snapshot taken by snapshot_main
  [ "$(main_states_core)" = "$(cat "$WORK/core_snapshot.txt")" ]
}
# Identity of the app containers: id, state, start time and restart count. A container that was recreated or
# restarted changes this line; "Up 3 minutes" style text would hide it.
main_states_core() {
  for c in hairmatch_db hairmatch_localstack hairmatch_ministack hairmatch_backend; do
    docker inspect -f '{{.Name}} {{.Id}} {{.State.Status}} {{.State.StartedAt}} {{.RestartCount}}' "$c" 2>/dev/null
  done | sort
}

marker_py() { # marker_py write|verify <marker file>
  PYTHONPATH="$SCRIPTS" python3 - "$1" "$2" <<'EOF'
import json, sys, time, uuid, urllib.parse
import smoke
action, path = sys.argv[1], sys.argv[2]
if action == "write":
    m = {"service": f"obs-modes-{uuid.uuid4().hex[:8]}", "trace": uuid.uuid4().hex, "folder": f"obs-modes-{uuid.uuid4().hex[:8]}"}
    smoke.TRACE_ID = m["trace"]
    ok = smoke.send_traces(service=m["service"], trace_id=m["trace"])[0] == 200
    ok &= smoke.send_logs([{"body": "modes marker", "trace_id": m["trace"]}], service=m["service"])[0] == 200
    ok &= smoke.send_histogram(service=m["service"], count=1)[0] == 200
    s, _ = smoke.http("POST", f"{smoke.GRAFANA}/api/folders", {"uid": m["folder"], "title": m["folder"]})
    ok &= s == 200
    # The marker has to be stored before the stack stops: wait until the three backends return it.
    ok &= bool(smoke.wait_for(lambda: smoke.tempo_trace(m["trace"]), 30))
    ok &= bool(smoke.wait_for(lambda: smoke.loki_lines(f'{{service_name="{m["service"]}"}}'), 30))
    ok &= bool(smoke.wait_for(lambda: smoke.prom_query(f'http_server_request_duration_seconds_count{{job="{m["service"]}"}}'), 30))
    json.dump(m, open(path, "w"))
    sys.exit(0 if ok else 1)
else:
    m = json.load(open(path))
    checks = {
        "tempo": lambda: smoke.tempo_trace(m["trace"]),
        "loki": lambda: smoke.loki_lines(f'{{service_name="{m["service"]}"}}'),
        # count_over_time: the sample is older than the 5 minute lookback of an instant query.
        "prometheus": lambda: smoke.prom_query(f'count_over_time(http_server_request_duration_seconds_count{{job="{m["service"]}"}}[6h])'),
        "grafana": lambda: smoke.http("GET", f'{smoke.GRAFANA}/api/folders/{m["folder"]}')[0] == 200,
    }
    bad = [name for name, fn in checks.items() if not smoke.wait_for(fn, 60)]
    print("missing after the switch: " + ", ".join(bad) if bad else "all four kept their data")
    sys.exit(1 if bad else 0)
EOF
}

# --- 1. standalone (OBS-01) ----------------------------------------------------------------------------------------

echo "== 1. standalone"
q $BOTH down --remove-orphans
q $OBS down
q $MAIN down
q $OBS up -d
if wait_obs_running "$OBS"; then pass OBS-01 "the 8 services are running within 60 s (standalone, nothing else of Hairmatch up)"; else fail OBS-01 "not every service is running within 60 s"; fi
sleep 20
check OBS-01 "no service is restarting" no_restarts "$OBS"
check OBS-13 "the Collector accepts OTLP from the host (127.0.0.1:4318)" python3 "$SCRIPTS/smoke.py" --mode standalone --only signals
if marker_py write "$WORK/marker.json"; then pass OBS-10 "a marker (trace, log, metric, Grafana folder) is stored in standalone mode"; else fail OBS-10 "the marker was not stored in standalone mode"; fi

# --- 2. main compose alone (OBS-03) --------------------------------------------------------------------------------

echo "== 2. main compose without the stack"
q $OBS down
q $MAIN up -d
if wait_main_ready; then pass OBS-03 "db, localstack and ministack are healthy and django is running, without the stack"; else fail OBS-03 "the main compose is not healthy without the stack"; fi
sleep 10
check OBS-03 "django is still running 10 s later" test "$(docker inspect -f '{{.State.Status}}' hairmatch_backend)" = running

# --- 3. combined (OBS-04, OBS-12, OBS-43, OBS-10) ------------------------------------------------------------------

echo "== 3. combined"
q $BOTH up -d
if wait_obs_running "$BOTH"; then pass OBS-04 "the 8 services run in the hairmatch project next to the app"; else fail OBS-04 "the stack did not come up in combined mode"; fi
OTLP_PROBE="import urllib.request as u; r = u.urlopen(u.Request('http://otel-collector:4318/v1/traces', data=b'{}', headers={'Content-Type': 'application/json'}), timeout=10); print(r.status)"
status=$(docker exec hairmatch_backend python -c "$OTLP_PROBE" 2>&1 | tail -1)
if [ "$status" = "200" ]; then pass OBS-04 "hairmatch_backend gets HTTP 200 from http://otel-collector:4318 by name"; else fail OBS-04 "hairmatch_backend got '$status' from otel-collector:4318"; fi

# OBS-12: every bind mount of the stack points to something real. Docker creates a missing source as an empty
# directory, which is exactly the failure this guards against.
mounts_ok=1
for service in $OBS_SERVICES; do
  id=$($BOTH ps -q "$service" 2>/dev/null)
  while read -r source; do
    [ -z "$source" ] && continue
    case "$source" in
      /|/var/run/docker.sock) continue ;;
    esac
    case "$source" in
      "$PWD"/docker/observability/*) ;;
      *) echo "    | $service mounts $source outside docker/observability"; mounts_ok=0; continue ;;
    esac
    if [ -d "$source" ] && [ -z "$(ls -A "$source")" ]; then echo "    | $service mounts the empty directory $source"; mounts_ok=0; fi
    if [ ! -e "$source" ]; then echo "    | $service mounts the missing path $source"; mounts_ok=0; fi
  done < <(docker inspect -f '{{range .Mounts}}{{if eq .Type "bind"}}{{println .Source}}{{end}}{{end}}' "$id")
done
for file in otel/config.yaml loki/config.yaml tempo/config.yaml prometheus/prometheus.yml alloy/config.alloy; do
  [ -f "docker/observability/$file" ] || { echo "    | $file is not a file on the host"; mounts_ok=0; }
done
# The Collector config seen from inside the container is the repository file (the image has no shell: copy it out).
if docker cp hairmatch_obs_otel_collector:/etc/otelcol/config.yaml "$WORK/collector.yaml" >/dev/null 2>&1 \
  && cmp -s "$WORK/collector.yaml" docker/observability/otel/config.yaml; then :; else echo "    | the Collector config inside the container differs from the repository file"; mounts_ok=0; fi
if [ "$mounts_ok" = 1 ]; then pass OBS-12 "in combined mode every bind mount is the repository file or directory, none is empty"; else fail OBS-12 "a bind mount is empty, missing or outside docker/observability"; fi

python3 "$SCRIPTS/smoke.py" --mode combined >"$WORK/smoke_combined.txt" 2>&1
smoke_rc=$?
grep -E '^(FAIL|smoke:)' "$WORK/smoke_combined.txt" | sed 's/^/    | /'
if [ $smoke_rc -eq 0 ]; then pass OBS-43 "smoke.py --mode combined passes (pg_up == 1 included)"; else fail OBS-43 "smoke.py --mode combined failed"; fi

if marker_py verify "$WORK/marker.json"; then pass OBS-10 "the standalone marker is still in Prometheus, Loki, Tempo and Grafana after the switch to combined"; else fail OBS-10 "data from standalone mode is missing in combined mode"; fi

# The reverse direction of OBS-10: data written in combined mode must survive the switch back to standalone.
if marker_py write "$WORK/marker2.json"; then pass OBS-10 "a second marker is stored in combined mode"; else fail OBS-10 "the marker was not stored in combined mode"; fi

# --- 4. removing the stack leaves the app alone (OBS-05) -----------------------------------------------------------

echo "== 4. remove the stack from the combined project"
main_states_core >"$WORK/core_snapshot.txt"
q $BOTH rm -sf $OBS_SERVICES
check OBS-05 "no observability container is left" test -z "$(docker ps -a --filter name=hairmatch_obs_ -q)"
sleep 5
if main_services_unchanged; then pass OBS-05 "db, localstack, ministack and django keep their state after rm -sf of the stack"; else fail OBS-05 "the app containers changed when the stack was removed"; fi

# --- 5. two modes at once (OBS-60) ---------------------------------------------------------------------------------

echo "== 5. both modes at once"
q $BOTH up -d
wait_obs_running "$BOTH" >/dev/null
main_states_core >"$WORK/core_snapshot.txt"
CONFLICT='already in use|conflict|already allocated|address already in use'
if $OBS up -d >"$WORK/dup1.out" 2>&1; then
  fail OBS-60 "standalone up succeeded while the combined mode was running"
elif grep -qiE "$CONFLICT" "$WORK/dup1.out"; then
  pass OBS-60 "standalone up fails with a name or port conflict while the combined mode is running"
else
  fail OBS-60 "standalone up failed, but not because of a conflict"; tail -3 "$WORK/dup1.out" | sed 's/^/    | /'
fi
if wait_obs_running "$BOTH" && main_services_unchanged; then pass OBS-60 "the combined mode keeps running after the failed standalone up"; else fail OBS-60 "the failed standalone up disturbed the combined mode"; fi

q $BOTH down --remove-orphans
q $OBS down
q $MAIN down
q $OBS up -d
wait_obs_running "$OBS" >/dev/null
if $BOTH up -d >"$WORK/dup2.out" 2>&1; then
  fail OBS-60 "combined up succeeded while the standalone mode was running"
elif grep -qiE "$CONFLICT" "$WORK/dup2.out"; then
  pass OBS-60 "combined up fails with a name or port conflict while the standalone mode is running"
else
  fail OBS-60 "combined up failed, but not because of a conflict"; tail -3 "$WORK/dup2.out" | sed 's/^/    | /'
fi
if marker_py verify "$WORK/marker2.json"; then pass OBS-10 "the combined-mode marker is in Prometheus, Loki, Tempo and Grafana after the switch to standalone"; else fail OBS-10 "data from combined mode is missing in standalone mode"; fi
if wait_obs_running "$OBS" && no_restarts "$OBS"; then pass OBS-60 "the standalone mode keeps running after the failed combined up"; else fail OBS-60 "the failed combined up disturbed the standalone mode"; fi

# Clean up the marker folder, then the EXIT trap restores the main compose.
python3 - "$WORK/marker.json" "$WORK/marker2.json" <<'EOF' 2>/dev/null
import json, sys
sys.path.insert(0, "docker/observability/scripts")
import smoke
for path in sys.argv[1:]:
    m = json.load(open(path))
    smoke.http("DELETE", f'{smoke.GRAFANA}/api/folders/{m["folder"]}')
EOF
