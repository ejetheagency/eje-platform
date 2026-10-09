# factory/providers/health.py
# REAL provider health probes (operator 2026-10-08): every provider the nightly uses gets a LIVE test call at the
# start of the run, so a dead / empty / rate-limited provider is VISIBLE in the funnel email's first line BEFORE the
# run, not discovered after. check_all() -> {provider: (STATUS, detail)}; STATUS in
#   OK | DOWN | OUT_OF_CREDITS | NO_KEY | DISABLED
# Probes hit each vendor's RAW endpoint directly (not the budgeted wrapper) so can_spend / caps can't mask the true
# vendor state. Prefer free/credit endpoints where they exist. NEVER raises.
import os, json, urllib.request, urllib.parse, urllib.error
from factory.packages import budget


def _disabled():
    try:
        return set(budget._cfg().get("disabled_providers", []) or [])
    except Exception:
        return set()


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "EJEFactory/health"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def _serper():
    key = os.environ.get("SERPER_API_KEY")
    if not key:
        return ("NO_KEY", "")
    try:
        body = json.dumps({"q": "cafe", "num": 1}).encode()
        req = urllib.request.Request("https://google.serper.dev/search", data=body, method="POST",
                                     headers={"X-API-KEY": key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as r:
            json.loads(r.read().decode()); return ("OK", "")
    except urllib.error.HTTPError as e:
        b = e.read().decode("utf-8", "ignore")
        if "credit" in b.lower():
            return ("OUT_OF_CREDITS", b[:60])
        if e.code == 429:
            return ("DOWN", "429 rate-limited")
        return ("DOWN", "%d %s" % (e.code, b[:40]))
    except Exception as e:
        return ("DOWN", str(e)[:60])


def _hunter():
    key = os.environ.get("HUNTER_API_KEY")
    if not key:
        return ("NO_KEY", "")
    try:  # /account is free and reports remaining searches
        d = _get("https://api.hunter.io/v2/account?api_key=%s" % key)
        req = (((d.get("data") or {}).get("requests") or {}).get("searches") or {})
        used, total = req.get("used"), req.get("available")
        if total is not None and used is not None and used >= total:
            return ("OUT_OF_CREDITS", "%s/%s" % (used, total))
        return ("OK", "%s/%s searches used" % (used, total))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return ("DOWN", "429 rate-limited")
        if e.code in (401, 403):
            return ("NO_KEY", "%d" % e.code)
        return ("DOWN", "%d" % e.code)
    except Exception as e:
        return ("DOWN", str(e)[:60])


def _prospeo():
    from factory.providers import prospeo
    r = prospeo.find_email("Test", "User", "example.com", client_id=None)
    if r.get("ok"):
        return ("OK", "")
    rs = r.get("reason") or ""
    if "no PROSPEO" in rs:
        return ("NO_KEY", "")
    if "DEPRECATED" in rs.upper() or "removed" in rs.lower():
        return ("DOWN", "deprecated endpoint")
    return ("DOWN", rs[:60])


def _apollo():
    from factory.providers import apollo
    r = apollo.find_decisor("example.com", client_id=None)
    if r.get("ok"):
        return ("OK", "")
    rs = r.get("reason") or ""
    if "no APOLLO" in rs:
        return ("NO_KEY", "")
    if "deprecated" in rs.lower():
        return ("DOWN", "deprecated endpoint")
    return ("DOWN", rs[:60])


def _mv():
    key = os.environ.get("MILLIONVERIFIER_API_KEY")
    if not key:
        return ("NO_KEY", "")
    try:  # credits endpoint is free
        d = _get("https://api.millionverifier.com/api/v3/credits?api=%s" % key)
        c = d.get("credits", d.get("Credits"))
        c = int(c) if c is not None else None
        if c is not None and c <= 0:
            return ("OUT_OF_CREDITS", "0")
        return ("OK", "%s credits" % c)
    except Exception as e:
        return ("DOWN", str(e)[:60])


def _places():
    key = os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        return ("NO_KEY", "")
    try:
        d = _get("https://maps.googleapis.com/maps/api/place/textsearch/json?" +
                 urllib.parse.urlencode({"query": "cafe Quito", "key": key}))
        s = d.get("status")
        if s in ("OK", "ZERO_RESULTS"):
            return ("OK", s)
        if s == "OVER_QUERY_LIMIT":
            return ("OUT_OF_CREDITS", s)
        if s == "REQUEST_DENIED":
            return ("NO_KEY", (d.get("error_message") or s)[:50])
        return ("DOWN", (d.get("error_message") or s or "?")[:50])
    except Exception as e:
        return ("DOWN", str(e)[:60])


def _cheap_llm():
    from factory.providers import cheap_llm
    try:
        out = cheap_llm.generate("Reply with exactly: ok", client_id=None, job_type="health")
        return ("OK", out.get("provider", ""))
    except Exception as e:
        return ("DOWN", str(e)[:60])


PROBES = [("serper", _serper), ("google_places", _places), ("millionverifier", _mv),
          ("hunter", _hunter), ("prospeo", _prospeo), ("apollo", _apollo), ("cheap_llm", _cheap_llm)]
_SHORT = {"serper": "serper", "google_places": "places", "millionverifier": "MV",
          "hunter": "hunter", "prospeo": "prospeo", "apollo": "apollo", "cheap_llm": "LLM"}


def check_all():
    dis = _disabled()
    out = {}
    for name, fn in PROBES:
        if name in dis:
            out[name] = ("DISABLED", "config"); continue
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = ("DOWN", str(e)[:60])
    return out


def line(results):
    parts = []
    for name, _ in PROBES:
        if name in results:
            parts.append("%s %s" % (_SHORT[name], results[name][0]))
    bad = [n for n, (st, _) in results.items() if st in ("DOWN", "OUT_OF_CREDITS")]
    head = "providers %s: " % ("ALL OK" if not bad else ("%d DOWN/OUT" % len(bad)))
    return head + " | ".join(parts)


if __name__ == "__main__":
    r = check_all()
    print(line(r))
    for n, (st, d) in r.items():
        print("  %-16s %-14s %s" % (n, st, d))
