#!/usr/bin/env python3
"""
Checks the Grafana dashboards in docker/observability/grafana/dashboards/.

Static (always): every file is valid JSON, uids and titles are unique, every panel with data has a query, and each
query points to one of the four provisioned data sources.

Live (--live, needs the stack up): asks Grafana for each panel's queries (POST /api/ds/query), the same call the
browser makes, with the variables resolved. A query error fails the run. A panel that returns no rows is listed as
"no data" and only fails with --strict (events that never happened, like Gemini calls, have no series yet).

    python3 docker/observability/scripts/check_dashboards.py            # static only
    python3 docker/observability/scripts/check_dashboards.py --live     # also runs the queries
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DASHBOARDS = Path(__file__).resolve().parent.parent / "grafana" / "dashboards"
GRAFANA = "http://127.0.0.1:3000"
DATASOURCES = {"prometheus", "loki", "tempo", "pyroscope"}
NO_QUERY_TYPES = {"row", "text"}


def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, {"message": exc.read().decode(errors="replace")[:300]}
    except OSError as exc:
        return 0, {"message": str(exc)}


def walk(panels):
    for panel in panels:
        yield panel
        yield from walk(panel.get("panels", []))


def static_check(files):
    problems, seen_uid, seen_title = [], {}, {}
    for path in files:
        try:
            dash = json.loads(path.read_text())
        except ValueError as exc:
            problems.append(f"{path.name}: invalid JSON ({exc})")
            continue
        if dash.get("uid") in seen_uid:
            problems.append(f"{path.name}: uid {dash.get('uid')!r} is also in {seen_uid[dash.get('uid')]}")
        if dash.get("title") in seen_title:
            problems.append(f"{path.name}: title {dash.get('title')!r} is also in {seen_title[dash.get('title')]}")
        seen_uid[dash.get("uid")] = path.name
        seen_title[dash.get("title")] = path.name
        ids = [p.get("id") for p in walk(dash.get("panels", []))]
        if len(ids) != len(set(ids)):
            problems.append(f"{path.name}: duplicated panel ids")
        for var in dash.get("templating", {}).get("list", []):
            ds = var.get("datasource")
            if ds and ds.get("uid") not in DATASOURCES:
                problems.append(f"{path.name}: variable {var['name']} uses an unknown data source {ds}")
        for panel in walk(dash.get("panels", [])):
            if panel.get("type") in NO_QUERY_TYPES:
                continue
            title = f"{path.name} / {panel.get('title')!r}"
            targets = panel.get("targets") or []
            if not targets:
                problems.append(f"{title}: no queries")
            for target in targets:
                uid = (target.get("datasource") or panel.get("datasource") or {}).get("uid")
                if uid not in DATASOURCES:
                    problems.append(f"{title}: unknown data source {uid!r}")
                if not any(target.get(k) for k in ("expr", "query", "profileTypeId")):
                    problems.append(f"{title}: empty query")
    return problems


def resolve_variables(dash):
    """Value of each dashboard variable, picked the way the browser would on load."""
    values = {"__rate_interval": "1m", "__range": "1h", "__auto": "1m", "__interval": "1m", "__interval_ms": "60000"}
    for var in dash.get("templating", {}).get("list", []):
        name = var["name"]
        current = (var.get("current") or {}).get("value")
        if var.get("includeAll") and (current in (None, "$__all", "")):
            values[name] = var.get("allValue") or ".*"
        elif current not in (None, "", "$__all"):
            values[name] = current if isinstance(current, str) else "|".join(current)
        elif var["type"] == "textbox":
            values[name] = ""
        elif var["type"] == "query" and var["datasource"]["uid"] == "prometheus":
            match = re.match(r"label_values\((.+),\s*(\w+)\)$", var["query"]["query"])
            status, body = http("GET", f"{GRAFANA}/api/datasources/proxy/uid/prometheus/api/v1/series?match[]="
                                + urllib.request.quote(match.group(1)))
            found = sorted({s.get(match.group(2)) for s in (body or {}).get("data", []) if s.get(match.group(2))})
            regex = var.get("regex", "")
            if regex.startswith("/^(?!"):
                found = [f for f in found if not f.startswith(regex[5:].split(")")[0])]
            values[name] = found[0] if found else ""
        elif var["type"] == "query" and var["datasource"]["uid"] == "pyroscope":
            if name == "profile_type":
                status, body = http("POST", f"{GRAFANA}/api/datasources/proxy/uid/pyroscope/querier.v1.QuerierService/ProfileTypes", {})
                ids = [p["ID"] for p in (body or {}).get("profileTypes", [])]
                values[name] = next((i for i in ids if "cpu" in i), ids[0] if ids else "")
            else:
                now = int(time.time() * 1000)
                status, body = http("POST", f"{GRAFANA}/api/datasources/proxy/uid/pyroscope/querier.v1.QuerierService/LabelValues",
                                    {"name": "service_name", "matchers": [], "start": now - 3600_000, "end": now})
                names = (body or {}).get("names", [])
                values[name] = names[0] if names else ""
        else:
            values[name] = ".*"
    return values


def interpolate(text, values):
    for name in sorted(values, key=len, reverse=True):
        text = text.replace("${" + name + "}", values[name]).replace("$" + name, values[name])
    return text


def frame_rows(result):
    return sum(len(f["data"]["values"][0]) if f["data"]["values"] else 0 for f in result.get("frames", []))


def live_check(files, strict):
    status, health = http("GET", f"{GRAFANA}/api/health")
    if status != 200:
        return [f"Grafana is not reachable at {GRAFANA} ({health})"], []
    status, found = http("GET", f"{GRAFANA}/api/search?type=dash-db")
    provisioned = {d["uid"] for d in found or []}
    errors, nodata = [], []
    for path in files:
        dash = json.loads(path.read_text())
        if dash["uid"] not in provisioned:
            errors.append(f"{path.name}: Grafana has not loaded dashboard {dash['uid']!r}")
            continue
        values = resolve_variables(dash)
        for panel in walk(dash.get("panels", [])):
            if panel.get("type") in NO_QUERY_TYPES:
                continue
            queries = []
            for target in panel.get("targets", []):
                q = json.loads(interpolate(json.dumps(target), values))
                q.update({"intervalMs": 60000, "maxDataPoints": 500})
                q.setdefault("datasource", panel.get("datasource"))
                queries.append(q)
            status, body = http("POST", f"{GRAFANA}/api/ds/query", {"queries": queries, "from": "now-1h", "to": "now"})
            title = f"{path.name} / {panel.get('title')!r}"
            if status != 200:
                errors.append(f"{title}: HTTP {status} {(body or {}).get('message', '')}")
                continue
            rows = 0
            for ref, result in body["results"].items():
                if result.get("error"):
                    errors.append(f"{title} [{ref}]: {result['error'][:200]}")
                rows += frame_rows(result)
            if rows == 0:
                nodata.append(title)
    if strict:
        errors += [f"{t}: no data" for t in nodata]
    return errors, nodata


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="also run every panel query through Grafana")
    parser.add_argument("--strict", action="store_true", help="with --live, a panel without data fails")
    args = parser.parse_args()
    files = sorted(DASHBOARDS.glob("*.json"))
    problems = static_check(files)
    print(f"static: {len(files)} dashboards, {len(problems)} problems")
    nodata = []
    if args.live:
        errors, nodata = live_check(files, args.strict)
        problems += errors
        print(f"live: {len(problems) - len(static_check(files))} query errors, {len(nodata)} panels without data")
        for title in nodata:
            print(f"  no data: {title}")
    for problem in problems:
        print(f"FAIL {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
