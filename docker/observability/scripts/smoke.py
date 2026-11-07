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
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COLLECTOR_CONFIG = ROOT / "docker/observability/otel/config.yaml"

LOKI = "http://127.0.0.1:3100"
TEMPO = "http://127.0.0.1:3200"
PROM = "http://127.0.0.1:9090"
PYROSCOPE = "http://127.0.0.1:4040"
GRAFANA = "http://127.0.0.1:3000"
COLLECTOR = "http://127.0.0.1:4318"
FARO = "http://127.0.0.1:12347"

RUN_ID = uuid.uuid4().hex[:8]
SERVICE = f"obs-smoke-{RUN_ID}"
# Shared by every section: the span, the log and the metric exemplar carry the same trace.
TRACE_ID = uuid.uuid4().hex
SPAN_ID = uuid.uuid4().hex[:16]
ROUTE = "/api/smoke"

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


def http_headers(method, url, headers=None, timeout=10):
    """Return (status, response headers as a lowercase dict)."""
    req = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}
    except Exception as e:
        return 0, {"error": str(e)}


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


def docker(*args):
    """Run the docker CLI; return (exit code, stdout+stderr)."""
    proc = subprocess.run(["docker", *args], capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


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

    wait_ready("Prometheus", f"{PROM}/-/ready", "OBS-11")
    _, flags = get_json(f"{PROM}/api/v1/status/flags")
    flags = (flags or {}).get("data", {})
    # Prometheus prints 7d back as 1w.
    check(flags.get("storage.tsdb.retention.time") in ("7d", "1w"), "OBS-11", "Prometheus retention is 7 days",
          f"got {flags.get('storage.tsdb.retention.time')}")
    check(flags.get("web.enable-otlp-receiver") == "true", "OBS-16", "Prometheus has the OTLP receiver enabled")
    check("exemplar-storage" in flags.get("enable-feature", ""), "OBS-18", "Prometheus has exemplar-storage enabled")
    _, cfg = get_json(f"{PROM}/api/v1/status/config")
    yaml_cfg = (cfg or {}).get("data", {}).get("yaml", "")
    check("out_of_order_time_window: 30m" in yaml_cfg, "OBS-16", "Prometheus accepts out-of-order samples for 30m")
    check("container.name" in yaml_cfg and "service.instance.id" in yaml_cfg and "host.name" in yaml_cfg, "OBS-46",
          "Prometheus promotes container.name, host.name and service.instance.id to labels")

    # Pyroscope holds /ready at 503 for ~15 s after start (metastore min-ready-duration).
    wait_ready("Pyroscope", f"{PYROSCOPE}/ready", "OBS-47")


# ---------------------------------------------------------------------------
# OTLP/JSON senders (OTLP/JSON encodes trace and span ids as hex strings)
# ---------------------------------------------------------------------------

def kv(key, value):
    if isinstance(value, bool):
        v = {"boolValue": value}
    elif isinstance(value, int):
        v = {"intValue": str(value)}
    elif isinstance(value, float):
        v = {"doubleValue": value}
    elif isinstance(value, dict):
        v = {"kvlistValue": {"values": [kv(k, x) for k, x in value.items()]}}
    else:
        v = {"stringValue": str(value)}
    return {"key": key, "value": v}


def kvs(d):
    return [kv(k, v) for k, v in (d or {}).items()]


def resource(service, extra=None):
    return {"attributes": kvs({"service.name": service, **(extra or {})})}


def send_traces(service=None, trace_id=None, span_id=None, name="smoke span", span_attrs=None,
                resource_attrs=None, base=COLLECTOR):
    now = time.time_ns()
    payload = {"resourceSpans": [{
        "resource": resource(service or SERVICE, resource_attrs),
        "scopeSpans": [{"scope": {"name": "obs-smoke"}, "spans": [{
            "traceId": trace_id or TRACE_ID, "spanId": span_id or SPAN_ID, "name": name, "kind": 2,
            "startTimeUnixNano": str(now - 50_000_000), "endTimeUnixNano": str(now),
            "attributes": kvs(span_attrs),
        }]}],
    }]}
    return http("POST", f"{base}/v1/traces", payload)


def send_logs(records, service=None, resource_attrs=None, base=COLLECTOR):
    """records: list of dicts with body (str or dict), attributes, trace_id, span_id."""
    now = time.time_ns()
    log_records = []
    for i, r in enumerate(records):
        body = r["body"]
        rec = {
            "timeUnixNano": str(now + i), "severityNumber": 9, "severityText": "INFO",
            "body": kv("b", body)["value"], "attributes": kvs(r.get("attributes")),
        }
        if r.get("trace_id"):
            rec["traceId"], rec["spanId"] = r["trace_id"], r.get("span_id", SPAN_ID)
        log_records.append(rec)
    payload = {"resourceLogs": [{
        "resource": resource(service or SERVICE, resource_attrs),
        "scopeLogs": [{"scope": {"name": "obs-smoke"}, "logRecords": log_records}],
    }]}
    return http("POST", f"{base}/v1/logs", payload)


def send_histogram(service=None, route=ROUTE, status=200, count=1, trace_id=None, at_ns=None,
                   point_attrs=None, resource_attrs=None, base=COLLECTOR):
    """One cumulative http.server.request.duration point. Rates need two points, so callers send it twice."""
    at = at_ns or time.time_ns()
    point = {
        "startTimeUnixNano": str(at - 600_000_000_000), "timeUnixNano": str(at),
        "count": str(count), "sum": 0.05 * count,
        "explicitBounds": [0.05, 0.1, 0.5, 1.0],
        "bucketCounts": [str(count), "0", "0", "0", "0"],
        "attributes": kvs({"http.route": route, "http.response.status_code": status, **(point_attrs or {})}),
    }
    if trace_id:
        point["exemplars"] = [{"timeUnixNano": str(at), "asDouble": 0.04, "traceId": trace_id, "spanId": SPAN_ID}]
    payload = {"resourceMetrics": [{
        "resource": resource(service or SERVICE, resource_attrs),
        "scopeMetrics": [{"scope": {"name": "obs-smoke"}, "metrics": [{
            "name": "http.server.request.duration", "unit": "s",
            "histogram": {"aggregationTemporality": 2, "dataPoints": [point]},
        }]}],
    }]}
    return http("POST", f"{base}/v1/metrics", payload)


_signals_sent = False
SMOKE_LOG = f"smoke log {RUN_ID} linked to its trace"


def ensure_signals():
    """Send the span, the log and the metric once per run, all on the same service and trace."""
    global _signals_sent
    if _signals_sent:
        return []
    _signals_sent = True
    results = [
        send_traces(span_attrs={"smoke.run": RUN_ID}),
        send_logs([{"body": SMOKE_LOG, "trace_id": TRACE_ID, "attributes": {"smoke.run": RUN_ID}}]),
    ]
    now = time.time_ns()
    for status in (200, 500):
        # Two points per series: the first 30 s back, the second now (the exemplar rides on the 200 series).
        results.append(send_histogram(status=status, count=1, at_ns=now - 30_000_000_000))
        results.append(send_histogram(status=status, count=3, at_ns=now, trace_id=TRACE_ID if status == 200 else None))
    return results


def prom_query(expr):
    status, body = get_json(f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr}))
    return (body or {}).get("data", {}).get("result", [])


def loki_query(expr, limit=100):
    now = time.time_ns()
    qs = urllib.parse.urlencode({"query": expr, "start": now - 3_600_000_000_000, "end": now + 60_000_000_000,
                                 "limit": limit, "direction": "forward"})
    _, body = get_json(f"{LOKI}/loki/api/v1/query_range?{qs}")
    return (body or {}).get("data", {}).get("result", [])


def loki_lines(expr):
    """Flat list of (line, labels, structured_metadata) for a LogQL stream selector."""
    out = []
    for stream in loki_query(expr):
        for value in stream["values"]:
            meta = value[2].get("structuredMetadata", value[2]) if len(value) > 2 else {}
            out.append((value[1], stream["stream"], meta))
    return out


def tempo_trace(trace_id):
    status, body = http("GET", f"{TEMPO}/api/traces/{trace_id}", headers={"Accept": "application/json"})
    return json.loads(body) if status == 200 else None


# ---------------------------------------------------------------------------
# signals
# ---------------------------------------------------------------------------

def collector_pipelines():
    """{pipeline: [processors]} read from the Collector config (flow-style lists), without a YAML library."""
    text = COLLECTOR_CONFIG.read_text()
    service = text.split("\nservice:", 1)[1]
    pipes = {}
    for m in re.finditer(r"^    (\w+):\n(?:      \w+: .*\n)*?      processors: \[(.*?)\]", service, re.M):
        pipes[m.group(1)] = [p.strip() for p in m.group(2).split(",")]
    return pipes


def section_signals(args):
    results = ensure_signals()
    check(all(s == 200 for s, _ in results), "OBS-13", "the Collector accepts OTLP/HTTP on 127.0.0.1:4318",
          f"statuses: {[s for s, _ in results]}")

    trace = wait_for(lambda: tempo_trace(TRACE_ID), timeout=30)
    spans = [s for rs in (trace or {}).get("batches", []) for ss in rs.get("scopeSpans", []) for s in ss.get("spans", [])]
    check(any(s.get("spanId") for s in spans), "OBS-14", "Tempo returns the span by trace_id", f"trace_id={TRACE_ID}")

    line = wait_for(lambda: next((x for x in loki_lines(f'{{service_name="{SERVICE}"}}') if x[0] == SMOKE_LOG), None), timeout=30)
    check(line is not None, "OBS-15", f'Loki returns the log for {{service_name="{SERVICE}"}}')

    series = wait_for(lambda: prom_query(f'http_server_request_duration_seconds_count{{job="{SERVICE}"}}'), timeout=30)
    check(bool(series), "OBS-16", f'Prometheus returns http_server_request_duration_seconds_count{{job="{SERVICE}"}}')

    def exemplar_trace_ids():
        now = time.time()
        qs = urllib.parse.urlencode({"query": f'http_server_request_duration_seconds_bucket{{job="{SERVICE}"}}',
                                     "start": now - 3600, "end": now + 60})
        _, body = get_json(f"{PROM}/api/v1/query_exemplars?{qs}")
        return {e["labels"].get("trace_id") for r in (body or {}).get("data", []) for e in r.get("exemplars", [])}

    ids = wait_for(exemplar_trace_ids, timeout=30)
    check(TRACE_ID in (ids or set()), "OBS-18", "Prometheus query_exemplars returns the trace_id", f"got {ids}")

    pipes = collector_pipelines()
    ok = bool(pipes) and all(p[0] == "memory_limiter" and p[-1] == "batch" for p in pipes.values())
    check(ok, "OBS-32", "every pipeline starts with memory_limiter and ends with batch", f"pipelines: {pipes}")
    check(len(pipes) == 3, "OBS-32", "the Collector has traces, metrics and logs pipelines", f"pipelines: {sorted(pipes)}")


# ---------------------------------------------------------------------------
# redaction
# ---------------------------------------------------------------------------

# Exact inputs and outputs from the spec (reference table under the redaction stories).
# (input, expected output, extra rule); the extra rule is a regex that must NOT appear in the stored value.
REDACTION_CASES = [
    ("OBS-22", "contato joao.silva@example.com", "contato [email]", None),
    ("OBS-23", "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl", "token [jwt]", None),
    ("OBS-24", "cpf 123.456.789-09", "cpf [cpf]", r"123\.456\.789-09"),
    ("OBS-25", "cnpj 12.345.678/0001-95", "cnpj [cnpj]", r"\d{3}"),
    ("OBS-25", "cnpj 12345678000195", "cnpj [cnpj]", r"\d{3}"),
    ("OBS-26", "tel +55 (92) 99123-4567", "tel [telefone]", None),
    ("OBS-26", "tel (92) 99123-4567", "tel [telefone]", None),
    ("OBS-27", "doc 12345678909", "doc [cpf]", r"\d{4}"),
    # The label may be [email]; the requirement is only that no 4-digit run survives.
    ("OBS-27", "jid 5592991234567@s.whatsapp.net", None, r"\d{4}"),
    # Control: text without personal data must arrive untouched.
    ("control", "pedido 42 ok", "pedido 42 ok", None),
]
URL_KEYS = ["url.query", "url.full", "http.url", "http.target"]
URL_VALUE = "q=redaction-marker"
RED_SERVICE = f"{SERVICE}-red"


def attr_map(attrs):
    """OTLP/JSON attribute list -> {key: python value}."""
    out = {}
    for a in attrs or []:
        v = a["value"]
        out[a["key"]] = v.get("stringValue", v.get("intValue", v.get("doubleValue", v.get("boolValue", v))))
    return out


def judge(req, label, got, expected, forbidden):
    if expected is not None:
        ok = got == expected
        detail = f"got {got!r}, want {expected!r}"
    else:
        ok, detail = got is not None, f"got {got!r}"
    if ok and forbidden and re.search(forbidden, got):
        ok, detail = False, f"{got!r} still matches /{forbidden}/"
    check(ok, req, f"{label}: " + (f"stored {got!r}" if expected is None else f"-> {expected!r}"), detail)


def section_redaction(args):
    # One request per case and place: string body + log attribute, map body, resource attribute, span.
    for i, (_, text, _, _) in enumerate(REDACTION_CASES):
        send_logs([
            {"body": text, "attributes": {"smoke.case": f"s{i}", "pii": text}},
            {"body": {"msg": text, "count": 7}, "attributes": {"smoke.case": f"m{i}"}},
        ], service=RED_SERVICE)
        send_logs([{"body": f"resource case {i}", "attributes": {"smoke.case": f"r{i}"}}],
                  service=RED_SERVICE, resource_attrs={"pii.resource": text})
        send_traces(service=RED_SERVICE, trace_id=uuid.uuid4().hex[:31] + format(i, "x"), span_id=uuid.uuid4().hex[:16],
                    name=f"case-{i}", span_attrs={"pii": text, "smoke.case": f"t{i}"},
                    resource_attrs={"pii.resource": text})
    # Non-string values are not redacted (OBS-59), and the URL keys are removed from log and span.
    url_attrs = {**{k: URL_VALUE for k in URL_KEYS}, "smoke.keep": "yes", "smoke.case": "url"}
    send_logs([{"body": "url keys case", "attributes": url_attrs}], service=RED_SERVICE)
    url_trace = uuid.uuid4().hex
    send_traces(service=RED_SERVICE, trace_id=url_trace, name="url-case", span_attrs={**url_attrs, "smoke.case": "url"})
    int_trace = uuid.uuid4().hex
    send_traces(service=RED_SERVICE, trace_id=int_trace, name="int-case", span_attrs={"phone.int": 5592991234567})
    # Metric points: the same four keys must not become labels.
    metric_service = f"{SERVICE}-url"
    now = time.time_ns()
    for n, ts in ((1, now - 30_000_000_000), (3, now)):
        send_histogram(service=metric_service, count=n, at_ns=ts, route="/url-case",
                       point_attrs={**{k: URL_VALUE for k in URL_KEYS}, "smoke.keep": "yes"})

    def stored_logs():
        lines = loki_query(f'{{service_name="{RED_SERVICE}"}}', limit=500)
        found = {}
        for stream in lines:
            for value in stream["values"]:
                found[stream["stream"].get("smoke_case")] = (value[1], stream["stream"])
        return found if len(found) >= 3 * len(REDACTION_CASES) + 1 else None

    logs = wait_for(stored_logs, timeout=45) or {}
    check(bool(logs), "OBS-15", "Loki stored every redaction log", f"stored {len(logs)}")

    for i, (req, text, expected, forbidden) in enumerate(REDACTION_CASES):
        line, labels = logs.get(f"s{i}", (None, {}))
        judge(req, f"string body {text!r}", line, expected, forbidden)
        judge("OBS-28", f"log attribute {text!r}", labels.get("pii"), expected, forbidden)
        line, _ = logs.get(f"m{i}", (None, {}))
        try:
            msg = json.loads(line)["msg"]
        except (TypeError, ValueError, KeyError):
            msg = line
        judge("OBS-29", f"map body {text!r}", msg, expected, forbidden)
        _, labels = logs.get(f"r{i}", (None, {}))
        judge("OBS-28", f"resource attribute {text!r}", labels.get("pii_resource"), expected, forbidden)

    # Spans: look the traces up by their span name through the TraceQL search API.
    for i, (req, text, expected, forbidden) in enumerate(REDACTION_CASES):
        def span_attrs_for(i=i):
            qs = urllib.parse.urlencode({"q": f'{{ resource.service.name = "{RED_SERVICE}" && name = "case-{i}" }}'})
            _, body = get_json(f"{TEMPO}/api/search?{qs}")
            traces = (body or {}).get("traces", [])
            if not traces:
                return None
            trace = tempo_trace(traces[0]["traceID"])
            for rs in (trace or {}).get("batches", []):
                for ss in rs.get("scopeSpans", []):
                    for s in ss.get("spans", []):
                        return attr_map(s.get("attributes")), attr_map(rs.get("resource", {}).get("attributes"))
            return None
        found = wait_for(span_attrs_for, timeout=30)
        span_a, res_a = found if found else ({}, {})
        judge("OBS-28", f"span attribute {text!r}", span_a.get("pii"), expected, forbidden)
        judge("OBS-28", f"span resource attribute {text!r}", res_a.get("pii.resource"), expected, forbidden)

    # OBS-30: the four URL keys are gone from the log, the span and the metric series; other attributes stay.
    _, labels = logs.get("url", (None, {}))
    leaked = [k for k in URL_KEYS if k.replace(".", "_") in labels]
    check(not leaked and labels.get("smoke_keep") == "yes", "OBS-30", "the url.* and http.* keys are gone from the log",
          f"labels: {sorted(labels)}")

    def url_span():
        qs = urllib.parse.urlencode({"q": f'{{ resource.service.name = "{RED_SERVICE}" && name = "url-case" }}'})
        _, body = get_json(f"{TEMPO}/api/search?{qs}")
        traces = (body or {}).get("traces", [])
        trace = tempo_trace(traces[0]["traceID"]) if traces else None
        spans = [s for rs in (trace or {}).get("batches", []) for ss in rs.get("scopeSpans", []) for s in ss.get("spans", [])]
        return attr_map(spans[0].get("attributes")) if spans else None
    span_a = wait_for(url_span, timeout=30) or {}
    leaked = [k for k in URL_KEYS if k in span_a]
    check(bool(span_a) and not leaked and span_a.get("smoke.keep") == "yes", "OBS-30",
          "the url.* and http.* keys are gone from the span", f"attributes: {sorted(span_a)}")

    series = wait_for(lambda: prom_query(f'http_server_request_duration_seconds_count{{job="{metric_service}"}}'), timeout=30)
    metric = (series or [{}])[0].get("metric", {})
    leaked = [k for k in URL_KEYS if k.replace(".", "_") in metric]
    check(bool(series) and not leaked and metric.get("smoke_keep") == "yes", "OBS-30",
          "the url.* and http.* keys are gone from the metric series", f"labels: {sorted(metric)}")

    # OBS-59: a personal number sent as an integer is not redacted (accepted, documented limitation).
    int_span = wait_for(lambda: tempo_trace(int_trace), timeout=30)
    spans = [s for rs in (int_span or {}).get("batches", []) for ss in rs.get("scopeSpans", []) for s in ss.get("spans", [])]
    value = attr_map(spans[0].get("attributes")).get("phone.int") if spans else None
    check(str(value) == "5592991234567", "OBS-59", "an integer attribute is left as it was", f"got {value!r}")

    # OBS-31: redaction runs before the exporter, with the same processors whatever the destination.
    pipes = collector_pipelines()
    order = ["memory_limiter", "attributes/pii", "transform/pii", "batch"]
    want = {"traces": order, "logs": order, "metrics": [p for p in order if p != "transform/pii"]}
    check(pipes == want, "OBS-31", "attributes/pii and transform/pii run between memory_limiter and batch", f"pipelines: {pipes}")


# ---------------------------------------------------------------------------
# grafana
# ---------------------------------------------------------------------------

DATASOURCE_UIDS = ["prometheus", "loki", "tempo", "pyroscope"]


def grafana_ds(uid):
    _, body = get_json(f"{GRAFANA}/api/datasources/uid/{uid}")
    return body or {}


def section_grafana(args):
    ensure_signals()
    # OBS-42: open without login, as an anonymous Admin.
    wait_ready("Grafana", f"{GRAFANA}/api/health", "OBS-42")
    try:
        with urllib.request.urlopen(f"{GRAFANA}/", timeout=10) as resp:
            landed = resp.geturl()
    except Exception as e:
        landed = f"error: {e}"
    status, _ = http("GET", f"{GRAFANA}/api/org/users")  # Admin-only endpoint
    check("/login" not in landed and status == 200, "OBS-42",
          "Grafana opens without a login screen, with anonymous Admin", f"landed on {landed}, /api/org/users={status}")

    # OBS-38: four provisioned, read-only data sources with fixed UIDs.
    _, listed = get_json(f"{GRAFANA}/api/datasources")
    by_uid = {d["uid"]: d for d in listed or []}
    check(sorted(by_uid) == sorted(DATASOURCE_UIDS), "OBS-38", "the data source UIDs are prometheus, loki, tempo and pyroscope",
          f"got {sorted(by_uid)}")
    check(all(by_uid.get(u, {}).get("readOnly") is True for u in DATASOURCE_UIDS), "OBS-38",
          "every data source is provisioned (readOnly)")

    # OBS-39: health of each data source. Grafana 13 installs its core data source plugins in the background on the
    # first start, so Prometheus can answer "Plugin not registered" for a while.
    for uid in DATASOURCE_UIDS:
        def health(uid=uid):
            _, body = get_json(f"{GRAFANA}/api/datasources/uid/{uid}/health", timeout=20)
            return body if (body or {}).get("status") == "OK" else None
        ok = wait_for(health, timeout=120, interval=3)
        check(ok is not None, "OBS-39", f"data source {uid} health is OK", f"last: {get_json(f'{GRAFANA}/api/datasources/uid/{uid}/health')[1]}")

    # OBS-21 / OBS-20 / OBS-19: the links between signals are in the provisioned configuration.
    dests = grafana_ds("prometheus").get("jsonData", {}).get("exemplarTraceIdDestinations", [])
    check(any(d.get("name") == "trace_id" and d.get("datasourceUid") == "tempo" for d in dests), "OBS-21",
          "Prometheus exemplar trace_id opens in Tempo", f"got {dests}")
    fields = grafana_ds("loki").get("jsonData", {}).get("derivedFields", [])
    check(any(f.get("name") == "trace_id" and f.get("datasourceUid") == "tempo" and f.get("matcherRegex") == "trace_id"
              and f.get("matcherType") == "label" for f in fields), "OBS-20",
          "Loki derived field turns trace_id into a Tempo link", f"got {fields}")
    tempo_cfg = grafana_ds("tempo").get("jsonData", {}).get("tracesToLogsV2", {})
    query = tempo_cfg.get("query", "")
    check(tempo_cfg.get("datasourceUid") == "loki" and "service_name" in query and "trace_id" in query, "OBS-19",
          "Tempo trace-to-logs points at Loki, filtering by service_name and trace_id", f"got {tempo_cfg}")

    # OBS-17: run the LogQL that Tempo generates, with the placeholders filled by the smoke span.
    logql = query.replace('${__span.tags["service.name"]}', SERVICE).replace("${__trace.traceId}", TRACE_ID)

    def trace_logs():
        now = time.time_ns()
        qs = urllib.parse.urlencode({"query": logql, "start": now - 3_600_000_000_000, "end": now + 60_000_000_000})
        _, body = get_json(f"{GRAFANA}/api/datasources/proxy/uid/loki/loki/api/v1/query_range?{qs}")
        lines = [v[1] for s in (body or {}).get("data", {}).get("result", []) for v in s["values"]]
        return lines or None
    lines = wait_for(trace_logs, timeout=30)
    check(lines is not None and SMOKE_LOG in lines, "OBS-17", "the trace-to-logs query returns the log of the trace",
          f"query {logql!r} -> {lines}")

    # OBS-40: the dashboard lives in the Hairmatch folder, with a service variable and three panels.
    found = wait_for(lambda: [d for d in (get_json(f"{GRAFANA}/api/search?" + urllib.parse.urlencode({"query": "API"}))[1] or [])
                              if d.get("title") == "API \u00b7 RED" and d.get("folderTitle") == "Hairmatch"], timeout=60)
    check(bool(found), "OBS-40", 'dashboard "API · RED" is in the folder "Hairmatch"')
    _, dash = get_json(f"{GRAFANA}/api/dashboards/uid/{found[0]['uid']}") if found else (0, None)
    model = (dash or {}).get("dashboard", {})
    variables = [v.get("name") for v in model.get("templating", {}).get("list", [])]
    var_query = next((v["query"]["query"] for v in model.get("templating", {}).get("list", []) if v.get("name") == "service"), "")
    check(variables == ["service"] and "label_values(" in var_query and ", job)" in var_query, "OBS-40",
          "the dashboard has the variable service, with the values of job", f"variables {variables}, query {var_query!r}")
    panels = model.get("panels", [])
    exprs = [p["targets"][0]["expr"] for p in panels]
    check(len(panels) == 3 and all("http_route" in e for e in exprs), "OBS-40",
          "the dashboard has three panels, all by http_route", f"exprs {exprs}")
    rate, errors, p95 = (exprs + ["", "", ""])[:3]
    check(rate.startswith("sum by (http_route) (rate(http_server_request_duration_seconds_count")
          and 'http_response_status_code=~"5.."' not in rate
          and 'http_response_status_code=~"5.."' in errors
          and p95.startswith("histogram_quantile(0.95"), "OBS-40",
          "the panels are request rate, 5xx rate and p95 duration", f"exprs {exprs}")

    # OBS-41: every panel query returns a series for the smoke service ($service replaced by the smoke service.name).
    for panel in panels:
        expr = panel["targets"][0]["expr"].replace("$service", SERVICE)
        result = wait_for(lambda expr=expr: prom_query(expr), timeout=30)
        check(bool(result), "OBS-41", f"panel {panel['title']!r} returns a series for {SERVICE}", f"expr {expr}")


# ---------------------------------------------------------------------------
# faro
# ---------------------------------------------------------------------------

# Payload shape: the Go structs in grafana/alloy v1.21.3,
# internal/component/faro/receiver/internal/payload/payload.go (Payload, Meta, App, Log, Exception, Stacktrace).
# Only `timestamp` is always serialized there; the rest is optional.
FARO_ORIGIN = "http://localhost:8081"


def section_faro(args):
    marker = f"faro-{RUN_ID}"
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    payload = {
        "meta": {"sdk": {"name": "obs-smoke", "version": "0.0.0"},
                 "app": {"name": "hairmatch-web-smoke", "version": "0.0.0", "environment": "dev"},
                 "page": {"url": "http://localhost:8081/"}},
        "logs": [{"message": f"{marker} login by maria.souza@example.com", "level": "info", "timestamp": stamp}],
        "exceptions": [{"type": "Error", "value": f"{marker}-exc failed for maria.souza@example.com", "timestamp": stamp,
                        "stacktrace": {"frames": [{"filename": "app.js", "function": "login", "lineno": 1, "colno": 2}]}}],
    }
    status, body = http("POST", f"{FARO}/collect", payload, headers={"Origin": FARO_ORIGIN})
    check(status in (200, 202, 204), "OBS-48", "the Faro receiver accepts a payload with a log and an exception",
          f"status {status}: {body[:200]}")

    def stored():
        found = loki_lines(f'{{service_name=~".+"}} |= "{marker}"')
        return found or None
    lines = wait_for(stored, timeout=30) or []
    texts = [x[0] for x in lines]
    log_line = next((x for x in texts if f"{marker} login" in x), None)
    check(log_line is not None and "[email]" in log_line and "maria.souza@example.com" not in log_line, "OBS-48",
          "the Faro log reaches Loki through the Collector, with the e-mail replaced by [email]", f"stored {texts}")
    check(not any("maria.souza@example.com" in x for x in texts), "OBS-48",
          "no stored Faro line keeps the e-mail", f"stored {texts}")

    # OBS-49 / OBS-50: CORS preflight.
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    status, hdrs = http_headers("OPTIONS", f"{FARO}/collect", {**preflight, "Origin": FARO_ORIGIN})
    check(hdrs.get("access-control-allow-origin") == FARO_ORIGIN, "OBS-49",
          f"the preflight from {FARO_ORIGIN} gets that Access-Control-Allow-Origin", f"status {status}, headers {hdrs}")
    status, hdrs = http_headers("OPTIONS", f"{FARO}/collect", {**preflight, "Origin": "http://evil.example"})
    allow = hdrs.get("access-control-allow-origin")
    check(allow not in ("http://evil.example", "*"), "OBS-50",
          "the preflight from another origin does not get its origin allowed", f"status {status}, allow-origin {allow!r}")


# ---------------------------------------------------------------------------
# infra
# ---------------------------------------------------------------------------

COLLECTOR_CONTAINER = "hairmatch_obs_otel_collector"


def section_infra(args):
    # OBS-45: host memory and disk, within 60 s of the stack coming up.
    for metric in ("system_memory_usage_bytes", "system_filesystem_usage_bytes"):
        series = wait_for(lambda m=metric: prom_query(m), timeout=60, interval=3)
        check(bool(series), "OBS-45", f"Prometheus has {metric}")

    # OBS-46: a memory series per container, labelled with the container name, the Collector's included.
    def container_names():
        names = {r["metric"].get("container_name") for r in prom_query("container_memory_usage_total_bytes")}
        return names if COLLECTOR_CONTAINER in names else None
    names = wait_for(container_names, timeout=60, interval=3)
    check(names is not None, "OBS-46", f"container_memory_usage_total_bytes{{container_name={COLLECTOR_CONTAINER!r}}} exists",
          f"got {sorted(n for n in (names or set()) if n)}")

    # The Docker API version must be accepted (Docker Engine 29 refuses anything below 1.44).
    code, logs = docker("logs", COLLECTOR_CONTAINER, "--since", "5m")
    bad = [l for l in logs.splitlines() if re.search(r"(client version|API version|too old)", l, re.I) and re.search(r"error|fail", l, re.I)]
    check(code == 0 and not bad, "OBS-46", "the Collector log has no Docker API version error", f"{bad[:2]}")

    # OBS-44 (standalone) / OBS-43 (combined): pg_up says whether the exporter reaches the app's Postgres.
    want = 1.0 if args.mode == "combined" else 0.0
    req = "OBS-43" if args.mode == "combined" else "OBS-44"

    def pg_up():
        # The latest sample, polled until it shows the expected value (a stale one from the other mode differs).
        res = prom_query('pg_up{job="postgres"}')
        return float(res[0]["value"][1]) if res else None
    value = wait_for(lambda: pg_up() == want and want + 1, timeout=60, interval=3)
    check(value, req, f"Prometheus has pg_up == {int(want)} ({args.mode} mode)", f"pg_up is {pg_up()}")

    if args.mode == "standalone":
        # The exporter must survive without a database: running, and never restarted, after a full minute.
        code, out = docker("inspect", "hairmatch_obs_postgres_exporter", "--format",
                           "{{.State.Running}} {{.RestartCount}} {{.State.StartedAt}}")
        running, restarts, started = (out.split() + ["", "", ""])[:3]
        age = time.time() - time.mktime(time.strptime(started[:19], "%Y-%m-%dT%H:%M:%S")) + time.timezone if started else 0
        if 0 < age < 60:
            time.sleep(60 - age)
            code, out = docker("inspect", "hairmatch_obs_postgres_exporter", "--format", "{{.State.Running}} {{.RestartCount}}")
            running, restarts = out.split()[:2]
        check(code == 0 and running == "true" and restarts == "0", "OBS-44",
              "the postgres-exporter is still running, with no restarts, after 60 s", f"inspect: {out}")


SECTIONS = {
    "ready": section_ready,
    "signals": section_signals,
    "redaction": section_redaction,
    "grafana": section_grafana,
    "infra": section_infra,
    "faro": section_faro,
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
