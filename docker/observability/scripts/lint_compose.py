#!/usr/bin/env python3
"""Static checks for the observability compose file (no running containers needed).

Prints one PASS/FAIL line per check and exits 1 on any FAIL.

    python3 docker/observability/scripts/lint_compose.py
    python3 docker/observability/scripts/lint_compose.py --self-test

Structure comes from `docker compose config --format json`, or from PyYAML when Docker is missing.
Checks on the raw text (top-level `name:` and the bind-mount prefix) use the file as written, because
`config` resolves both away.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OBS_COMPOSE = ROOT / "docker/observability/docker-compose.observability.yml"
MAIN_COMPOSE = ROOT / "docker/docker-compose.yml"

# Names the main compose must never mention (OBS-02).
STACK_NAMES = [
    "otel-collector", "loki", "tempo", "prometheus", "pyroscope", "alloy",
    "grafana", "postgres-exporter", "otlp-capture",
]

results = []  # (ok, requirement, message) for every check run


def report(ok, req, message):
    results.append((ok, req, message))


def strip_comments(text):
    return "\n".join(re.sub(r"(^|\s)#.*$", "", line) for line in text.splitlines())


def load_services(path):
    """Return (services dict, error). Ports come back as dicts when Compose resolved them."""
    if shutil.which("docker"):
        proc = subprocess.run(
            ["docker", "compose", "-f", str(path), "config", "--format", "json"],
            capture_output=True, text=True, cwd=str(path.parent),
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout).get("services") or {}, None
        return None, proc.stderr.strip()
    try:
        import yaml
    except ImportError:
        return None, "neither docker nor PyYAML is available to parse the compose file"
    return (yaml.safe_load(path.read_text()) or {}).get("services") or {}, None


def port_host_ip(port):
    """Host IP of a published port, from Compose's resolved dict or a raw short string."""
    if isinstance(port, dict):
        return port.get("host_ip")
    parts = str(port).split(":")
    return parts[0] if len(parts) == 3 else None


def lint_obs_compose(path):
    text = path.read_text()
    code = strip_comments(text)
    services, err = load_services(path)
    if services is None:
        report(False, "OBS-06", f"cannot parse {path.name}: {err}")
        return

    # OBS-06: no project name, or the combined mode would rename the app project.
    has_name = re.search(r"^name\s*:", code, re.M) is not None
    report(not has_name, "OBS-06", "no top-level `name:` in the observability compose")

    # OBS-07: exact version tags only.
    bad = [f"{n} ({s.get('image')})" for n, s in services.items()
           if not re.search(r":[vV]?\d+\.\d+\.\d+", s.get("image", ""))]
    report(not bad, "OBS-07", "every image has an exact version tag" + (f"; bad: {', '.join(bad)}" if bad else ""))

    # OBS-08: every published port is bound to loopback.
    bad = [f"{n} ({p})" for n, s in services.items() for p in s.get("ports", [])
           if port_host_ip(p) != "127.0.0.1"]
    report(not bad, "OBS-08", "every published port is bound to 127.0.0.1" + (f"; bad: {', '.join(bad)}" if bad else ""))

    # OBS-09: json-file with 10m x 3 on every service.
    bad = []
    for n, s in services.items():
        log = s.get("logging") or {}
        opts = log.get("options") or {}
        if log.get("driver") != "json-file" or str(opts.get("max-size")) != "10m" or str(opts.get("max-file")) != "3":
            bad.append(n)
    report(not bad, "OBS-09", "every service rotates logs (json-file, 10m x 3)" + (f"; bad: {', '.join(bad)}" if bad else ""))

    # OBS-12 (prefix part): relative bind-mount sources must start with ${OBS_DIR:-.}/.
    bad = []
    for m in re.finditer(r"^\s+-\s+[\"']?(\$\{[^}]*\}[^\s\"':]*|[^\s\"':]+):", code, re.M):
        src = m.group(1)
        if (src.startswith(".") or src.startswith("$")) and not src.startswith("${OBS_DIR:-.}/"):
            bad.append(src)
    report(not bad, "OBS-12", "every relative bind mount starts with ${OBS_DIR:-.}/" + (f"; bad: {', '.join(bad)}" if bad else ""))


def lint_main_compose(path):
    # OBS-02: the main compose never references the stack.
    code = strip_comments(path.read_text())
    hits = [n for n in STACK_NAMES if re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", code)]
    if re.search(r"OBS_|hairmatch_obs_|observability", code):
        hits.append("OBS_/hairmatch_obs_/observability")
    report(not hits, "OBS-02", "docker/docker-compose.yml does not reference the observability stack"
           + (f"; found: {', '.join(hits)}" if hits else ""))


SELF_TEST_BASE = """\
x-logging: &l
  driver: json-file
  options: {max-size: 10m, max-file: "3"}
services:
  svc:
    image: foo/bar:1.2.3
    ports: ["127.0.0.1:3000:3000"]
    logging: *l
    volumes:
      - ${OBS_DIR:-.}/a.txt:/a.txt:ro
"""

# (label, replacement applied to the base, requirement that must fail)
SELF_TEST_MUTATIONS = [
    ("project name", lambda t: "name: x\n" + t, "OBS-06"),
    ("latest tag", lambda t: t.replace("foo/bar:1.2.3", "foo/bar:latest"), "OBS-07"),
    ("major-only tag", lambda t: t.replace("foo/bar:1.2.3", "foo/bar:1"), "OBS-07"),
    ("public port", lambda t: t.replace("127.0.0.1:3000:3000", "3000:3000"), "OBS-08"),
    ("no logging", lambda t: t.replace("    logging: *l\n", ""), "OBS-09"),
    ("bad rotation", lambda t: t.replace("max-size: 10m", "max-size: 50m"), "OBS-09"),
    ("bare relative mount", lambda t: t.replace("${OBS_DIR:-.}/a.txt", "./a.txt"), "OBS-12"),
]


def self_test():
    """Prove the lint discriminates: the base passes, each mutation fails the expected check."""
    ok_all = True
    with tempfile.TemporaryDirectory() as tmp:
        def failed_checks(text):
            results.clear()
            path = Path(tmp) / "c.yml"
            path.write_text(text)
            lint_obs_compose(path)
            return [req for ok, req, _ in results if not ok]

        base_failed = failed_checks(SELF_TEST_BASE)
        ok_all &= not base_failed
        print(f"{'PASS' if not base_failed else 'FAIL'} self-test: the valid base passes every check"
              + (f"; failed: {base_failed}" if base_failed else ""))
        for label, mutate, req in SELF_TEST_MUTATIONS:
            good = req in failed_checks(mutate(SELF_TEST_BASE))
            ok_all &= good
            print(f"{'PASS' if good else 'FAIL'} self-test: {label} makes {req} fail")
    return 0 if ok_all else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--compose", type=Path, default=OBS_COMPOSE)
    parser.add_argument("--main", type=Path, default=MAIN_COMPOSE)
    parser.add_argument("--self-test", action="store_true", help="mutate a valid compose and expect each mutation to fail")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    lint_obs_compose(args.compose)
    lint_main_compose(args.main)
    for ok, req, message in results:
        print(f"{'PASS' if ok else 'FAIL'} {req}: {message}")
    failures = sum(1 for ok, _, _ in results if not ok)
    print(f"lint_compose: {len(results) - failures} PASS, {failures} FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
