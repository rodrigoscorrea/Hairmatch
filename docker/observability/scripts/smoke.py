#!/usr/bin/env python3
"""Smoke test for the observability stack, against the running containers. Standard library only.

    python3 docker/observability/scripts/smoke.py --mode standalone
    python3 docker/observability/scripts/smoke.py --mode combined --only infra

Sections: ready, signals, redaction, infra, grafana, faro.
Prints `PASS <OBS-NN>: ...` or `FAIL <OBS-NN>: <reason>` per check, then a count. Exits 1 on any FAIL.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

LOKI = "http://127.0.0.1:3100"
TEMPO = "http://127.0.0.1:3200"
PROM = "http://127.0.0.1:9090"
PYROSCOPE = "http://127.0.0.1:4040"
GRAFANA = "http://127.0.0.1:3000"
COLLECTOR = "http://127.0.0.1:4318"
FARO = "http://127.0.0.1:12347"

RUN_ID = uuid.uuid4().hex[:8]
SERVICE = f"obs-smoke-{RUN_ID}"

passes = 0
failures = 0


def check(ok, req, message, detail=""):
    global passes, failures
    if ok:
        passes += 1
        print(f"PASS {req}: {message}")
    else:
        failures += 1
        print(f"FAIL {req}: {message}" + (f" ({detail})" if detail else ""))
    return ok


def http(method, url, body=None, headers=None, timeout=10):
    """Return (status, body text). Network errors come back as (0, error text)."""
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:  # connection refused, timeout, reset
        return 0, str(e)


def get_json(url, timeout=10):
    status, text = http("GET", url, timeout=timeout)
    try:
        return status, json.loads(text)
    except ValueError:
        return status, None


def wait_for(fn, timeout=30, interval=1.0):
    """Poll fn() until it returns something truthy; return that value, or None on timeout."""
    deadline = time.time() + timeout
    while True:
        value = fn()
        if value:
            return value
        if time.time() >= deadline:
            return None
        time.sleep(interval)


def wait_ready(name, url, req, timeout=60):
    ok = wait_for(lambda: http("GET", url)[0] == 200, timeout=timeout)
    check(bool(ok), req, f"{name} {urllib.parse.urlparse(url).path} answers 200", f"last: {http('GET', url)}")


# ---------------------------------------------------------------------------
# ready
# ---------------------------------------------------------------------------

def section_ready(args):
    # Loki reports "ready" only after its ingester has warmed up (about 15 s after start).
    wait_ready("Loki", f"{LOKI}/ready", "OBS-11")

    # OBS-11 (Loki): 168h is printed back by Loki as 1w.
    _, cfg = http("GET", f"{LOKI}/config")
    limits = cfg.split("\nlimits_config:", 1)[-1]
    m = re.search(r"^\s+retention_period: (\S+)", limits, re.M)
    check(m is not None and m.group(1) in ("168h", "1w", "7d"), "OBS-11",
          "Loki limits_config.retention_period is 7 days", f"got {m.group(1) if m else None}")
    check("retention_enabled: true" in cfg, "OBS-11", "Loki compactor has retention enabled")

    wait_ready("Tempo", f"{TEMPO}/ready", "OBS-11")
    # Tempo also prints a 336h default for its unused backend_scheduler/backend_worker; only the compactor counts.
    _, cfg = http("GET", f"{TEMPO}/status/config")
    compactor = re.search(r"^compactor:\n(.*?)(?=^\S)", cfg, re.M | re.S)
    m = re.search(r"^\s+block_retention: (\S+)", compactor.group(1), re.M) if compactor else None
    check(m is not None and m.group(1) == "168h0m0s", "OBS-11", "Tempo compactor block_retention is 168h",
          f"got {m.group(1) if m else None}")


SECTIONS = {
    "ready": section_ready,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["standalone", "combined"], default="standalone")
    parser.add_argument("--only", choices=list(SECTIONS), help="run a single section")
    args = parser.parse_args()

    for name, fn in SECTIONS.items():
        if args.only and args.only != name:
            continue
        print(f"== {name}")
        fn(args)

    print(f"smoke: {passes} PASS, {failures} FAIL (mode={args.mode}, service={SERVICE})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
