# factory/providers/serper.py
# Google search via Serper (serper.dev). READY, needs SERPER_API_KEY. ~$0.001/search. Used by Discovery
# and the Signal Spotter v2 (press/"why-now"). Returns organic results [{title, link, snippet}].
# UNTESTED until a key is present (graceful no-op without one).
import os, json, urllib.request
from factory.packages import budget

PROVIDER = "serper"
EST_USD = budget.price("serper")
URL = "https://google.serper.dev/search"


def search(query, num=10, client_id=None):
    key = os.environ.get("SERPER_API_KEY")
    if not key:
        return {"ok": False, "reason": "no SERPER_API_KEY"}
    ok, reason = budget.can_spend(client_id, PROVIDER, EST_USD)
    if not ok:
        return {"ok": False, "reason": reason}
    body = json.dumps({"q": query, "num": num}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
                                 headers={"X-API-KEY": key, "Content-Type": "application/json"})
    try:  # NEVER raise: a bad query / 400 / timeout must return cleanly, not crash the whole mine_report run
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "reason": "serper %s" % str(e)[:120], "results": []}
    results = [{"title": o.get("title"), "link": o.get("link"), "snippet": o.get("snippet")}
               for o in (j.get("organic") or [])]
    budget.log_cost(PROVIDER, EST_USD, client_id=client_id, job_type="search", estimated=True)
    return {"ok": True, "results": results}
