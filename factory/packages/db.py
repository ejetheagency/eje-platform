# factory/packages/db.py
# Server-side Supabase access for the factory. Uses the SERVICE key (bypasses RLS) — this is the
# key-swap fix: workers must NOT use the anon key (RLS now returns 0 rows for anon). stdlib only.
import os, json, time, urllib.request, urllib.error


def _load_env():
    # repo root = up 3 from factory/packages/db.py
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    envp = os.path.join(root, ".env")
    if os.path.exists(envp):
        for line in open(envp):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_load_env()
SB = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
_H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}


class Conflict(Exception):
    """Unique-constraint / RLS-check violation (PostgREST 409 / 23505). Lets callers do select-on-conflict."""


def _req(method, path, body=None, extra=None, _tries=4):
    url = SB + "/rest/v1/" + path
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for attempt in range(_tries):
        req = urllib.request.Request(url, data=data, method=method, headers={**_H, **(extra or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                t = r.read().decode()
                return json.loads(t) if t.strip() else []
        except urllib.error.HTTPError as e:
            code = e.code
            body_txt = e.read().decode()[:400]
            if code == 409 or "23505" in body_txt:
                raise Conflict("%s %s -> %d: %s" % (method, path, code, body_txt))
            if code in (429, 500, 502, 503, 504) and attempt < _tries - 1:
                time.sleep(1.5 * (attempt + 1))
                last = RuntimeError("%s %s -> %d: %s" % (method, path, code, body_txt))
                continue
            raise RuntimeError("%s %s -> %d: %s" % (method, path, code, body_txt))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # transient network/timeout: back off and retry
            if attempt < _tries - 1:
                time.sleep(1.5 * (attempt + 1))
                last = e
                continue
            raise RuntimeError("%s %s failed after retries: %s" % (method, path, e))
    raise last or RuntimeError("request failed")


def select(table, query=""):
    return _req("GET", table + (("?" + query) if query else ""))


def insert(table, row, returning=True):
    hdr = {"Prefer": "return=representation"} if returning else {"Prefer": "return=minimal"}
    rows = _req("POST", table, [row] if isinstance(row, dict) else row, hdr)
    return rows


def update(table, query, patch):
    return _req("PATCH", table + "?" + query, patch, {"Prefer": "return=representation"})


def delete(table, query):
    return _req("DELETE", table + "?" + query, None, {"Prefer": "return=representation"})


def rpc(fn, args=None):
    return _req("POST", "rpc/" + fn, args or {})


def count(table, query=""):
    """Exact row count via Content-Range (avoids the 1000-row select cap)."""
    url = SB + "/rest/v1/" + table + "?" + ((query + "&") if query else "") + "select=id"
    req = urllib.request.Request(url, method="GET", headers={**_H, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            cr = r.headers.get("Content-Range", "")  # e.g. "0-0/1128"
            return int(cr.split("/")[-1]) if "/" in cr else 0
    except urllib.error.HTTPError as e:
        if e.code == 416:  # range not satisfiable = 0 rows
            cr = e.headers.get("Content-Range", "")
            return int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else 0
        raise RuntimeError("count %s -> %d: %s" % (table, e.code, e.read().decode()[:200]))


def select_all(table, query=""):
    """Paginated select past the 1000-row cap (for workers that must scan a whole table)."""
    out, off = [], 0
    while True:
        page = _req("GET", table + "?" + ((query + "&") if query else "") + "limit=1000&offset=%d" % off)
        out += page
        if len(page) < 1000:
            return out
        off += 1000
