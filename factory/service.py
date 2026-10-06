# factory/service.py  —  Always-on night-shift service (Railway). Self-schedules run_nightly daily, and
# exposes a tiny HTTP API. /run is guarded by a secret and runs ASYNC (never blocks the health server).
#   GET /                              -> health + state
#   GET /run?key=SECRET[&client=X][&max=N] -> trigger a run in a background thread
import os, json, time, threading, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from factory import run_nightly

VERSION = "2026-10-06-shipgate"  # bump each deploy to verify it landed via /health
PORT = int(os.environ.get("PORT", "8080"))
RUN_HOUR_UTC = int(os.environ.get("FACTORY_RUN_HOUR_UTC", "9"))
RUN_SECRET = os.environ.get("FACTORY_RUN_SECRET", "")
_state = {"version": VERSION, "last_run": None, "last_result": None, "running": False, "run_hour_utc": RUN_HOUR_UTC}
_last_run_date = None
_lock = threading.Lock()


def _run(client=None, max_leads=None):
    with _lock:
        if _state["running"]:
            return
        _state["running"] = True
    try:
        _state["last_result"] = run_nightly.run(client=client, max_leads=max_leads)
    except Exception as e:
        _state["last_result"] = "error: %s" % e
    finally:
        _state["last_run"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _state["running"] = False


def _loop():
    global _last_run_date
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        if now.hour == RUN_HOUR_UTC and _last_run_date != now.date().isoformat() and not _state["running"]:
            _last_run_date = now.date().isoformat()
            threading.Thread(target=_run, daemon=True).start()
        time.sleep(45)


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path.startswith("/run"):
            if not RUN_SECRET or qs.get("key", [None])[0] != RUN_SECRET:
                return self._json({"error": "forbidden"}, 403)
            if _state["running"]:
                return self._json({"started": False, "reason": "already running"})
            client = qs.get("client", [None])[0]
            mx = qs.get("max", [None])[0]
            threading.Thread(target=_run, kwargs={"client": client, "max_leads": int(mx) if mx else None}, daemon=True).start()
            return self._json({"started": True, "client": client, "max": mx})
        return self._json({"service": "eje-factory", **_state})

    def _json(self, d, code=200):
        b = json.dumps(d, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=_loop, daemon=True).start()
    print("eje-factory on :%d, nightly %02d:00 UTC" % (PORT, RUN_HOUR_UTC))
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
