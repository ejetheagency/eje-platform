# factory/providers/google_places.py
# Discovery (D1) via Google Places Text Search. READY, needs GOOGLE_PLACES_API_KEY (or GOOGLE_MAPS_API_KEY).
# Basic text search is free. Finds businesses per ICP query+location -> seeds `companies` (deduped).
# Website comes later from enrichment. UNTESTED until a key is present.
import os, json, re, urllib.request, urllib.parse
from factory.packages import db, budget

PROVIDER = "google_places"
URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS = "https://maps.googleapis.com/maps/api/place/details/json"
DETAILS_COST = 0.003  # Place Details (contact data) is a paid SKU, unlike basic text search


def _dedupe_key(name, address, website):
    if website:
        dom = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].lower()
        if dom:
            return dom  # a resolved domain is the strongest global dedupe key
    n = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    a = re.sub(r"[^a-z0-9]", "", (address or "").lower())[:20]
    return "place:" + n + "|" + a


def _details(place_id, key):
    url = DETAILS + "?" + urllib.parse.urlencode({"place_id": place_id, "fields": "website,formatted_phone_number", "key": key})
    with urllib.request.urlopen(url, timeout=15) as r:
        res = (json.loads(r.read().decode()).get("result") or {})
    return res.get("website"), res.get("formatted_phone_number")


def discover(query, limit=20):
    # FREE text search only (name/address/place_id). Website is fetched LAZILY via get_website() for the
    # companies we actually keep, so the paid Details SKU is not billed on every scanned result.
    key = os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        return {"ok": False, "reason": "no GOOGLE_PLACES_API_KEY"}
    url = URL + "?" + urllib.parse.urlencode({"query": query, "key": key})
    with urllib.request.urlopen(url, timeout=20) as r:
        j = json.loads(r.read().decode())
    found = [{"name": p.get("name"), "address": p.get("formatted_address"), "place_id": p.get("place_id"),
              "dedupe_key": _dedupe_key(p.get("name"), p.get("formatted_address"), None)}
             for p in (j.get("results") or [])[:limit]]
    return {"ok": True, "found": len(found), "results": found}


def get_website(place_id, client_id=None):
    # Paid Place Details (website + phone). Call ONLY for companies we keep. Cost-logged.
    key = os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key or not place_id:
        return {"ok": False}
    try:
        website, phone = _details(place_id, key)
    except Exception:
        return {"ok": False}
    budget.log_cost(PROVIDER, DETAILS_COST, client_id=client_id, job_type="place_details", estimated=True)
    return {"ok": True, "website": website, "phone": phone}
