# factory/packages/db.py
# Server-side Supabase access for the factory. Uses the SERVICE key (bypasses RLS) — this is the
# key-swap fix: workers must NOT use the anon key (RLS now returns 0 rows for anon). stdlib only.
import os, json, urllib.request, urllib.error


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


def _req(method, path, body=None, extra=None):
    url = SB + "/rest/v1/" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={**_H, **(extra or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode()
            return json.loads(t) if t.strip() else []
    except urllib.error.HTTPError as e:
        raise RuntimeError("%s %s -> %d: %s" % (method, path, e.code, e.read().decode()[:400]))


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
