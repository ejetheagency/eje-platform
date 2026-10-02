# factory/service.py  —  Always-on night-shift service (for Railway / any always-on host).
# Self-schedules run_nightly once a day at FACTORY_RUN_HOUR_UTC, and exposes a tiny HTTP server so the
# host's healthcheck passes and you can trigger a run manually (GET /run). stdlib only, no deps.
# Start command:  python3 -m factory.service
import os, json, time, threading, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from factory import run_nightly

PORT = int(os.environ.get("PORT", "8080"))
RUN_HOUR_UTC = int(os.environ.get("FACTORY_RUN_HOUR_UTC", "9"))  # ~06:00 Chile; set per your window
_state = {"last_run": None, "last_result": None, "run_hour_utc": RUN_HOUR_UTC}
_last_run_date = None


def _run():
    global _last_run_date
    _last_run_date = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        run_nightly.main()
        _state["last_result"] = "ok"
    except Exception as e:
        _state["last_result"] = "error: %s" % e
    _state["last_run"] = datetime.datetime.now(datetime.timezone.utc).isoformat()


def _loop():
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        if now.hour == RUN_HOUR_UTC and _last_run_date != now.date().isoformat():
            _run()
        time.sleep(45)


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/run"):   # manual trigger (test the deploy)
            _run()
            return self._json({"ran": True, **_state})
        return self._json({"service": "eje-factory", **_state})

    def _json(self, d):
        b = json.dumps(d).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=_loop, daemon=True).start()
    print("eje-factory service on :%d, nightly at %02d:00 UTC" % (PORT, RUN_HOUR_UTC))
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
