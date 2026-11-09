#!/usr/bin/env python3
"""Minimal OTLP receiver for tests: answers 200 to every request and logs the method, path and Authorization.

Runs as the `otlp-capture` service (profile `verify`); check_destination.sh reads its log to prove where the
Collector sends each signal. Standard library only.
"""
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class Capture(BaseHTTPRequestHandler):
    def _record(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        # One line per request; the script greps for "<method> <path> auth=<header>".
        print(f"{self.command} {self.path} auth={self.headers.get('Authorization', '')}", flush=True)
        body = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_POST = do_PUT = do_GET = _record

    def log_message(self, *args):  # the request line above is the only output
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    HTTPServer(("0.0.0.0", port), Capture).serve_forever()
