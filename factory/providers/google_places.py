# factory/providers/google_places.py
# Discovery (D1) via Google Places Text Search. READY, needs GOOGLE_PLACES_API_KEY (or GOOGLE_MAPS_API_KEY).
# Basic text search is free. Finds businesses per ICP query+location -> seeds `companies` (deduped).
# Website comes later from enrichment. UNTESTED until a key is present.
import os, json, urllib.request, urllib.parse
from factory.packages import db

PROVIDER = "google_places"
URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"


def _dedupe_key(name, address):
    import re
    n = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    a = re.sub(r"[^a-z0-9]", "", (address or "").lower())[:20]
    return "place:" + n + "|" + a


def discover(query, limit=20, seed_companies=False):
    key = os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        return {"ok": False, "reason": "no GOOGLE_PLACES_API_KEY"}
    url = URL + "?" + urllib.parse.urlencode({"query": query, "key": key})
    with urllib.request.urlopen(url, timeout=20) as r:
        j = json.loads(r.read().decode())
    found = []
    for p in (j.get("results") or [])[:limit]:
        found.append({"name": p.get("name"), "address": p.get("formatted_address"),
                      "place_id": p.get("place_id"), "dedupe_key": _dedupe_key(p.get("name"), p.get("formatted_address"))})
    seeded = 0
    if seed_companies:
        for f in found:
            exists = db.select("companies", "dedupe_key=eq.%s&select=id" % urllib.parse.quote(f["dedupe_key"], safe=""))
            if not exists:
                db.insert("companies", {"dedupe_key": f["dedupe_key"], "name": f["name"]}, returning=False)
                seeded += 1
    return {"ok": True, "found": len(found), "seeded": seeded, "results": found}
