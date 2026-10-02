# factory/workers/discovery.py
# Discovery (D1). Turns a client's ICP into candidate companies + DISCOVERED client_leads, via Google Places.
# Companies are GLOBAL + deduped (enrich once, reuse across clients). READY, needs GOOGLE_PLACES_API_KEY.
# Queries come from clients.icp_config.discovery_queries (list) or are derived from industry + geos.
import urllib.parse
from factory.packages import db
from factory.providers import google_places


def _queries(icp):
    qs = icp.get("discovery_queries")
    if isinstance(qs, list) and qs:
        return qs
    industry = icp.get("industry") or icp.get("sector") or ""
    geos = icp.get("geos") or icp.get("locations") or icp.get("countries") or []
    if isinstance(geos, str):
        geos = [geos]
    if industry and geos:
        return ["%s en %s" % (industry, g) for g in geos]
    return [industry] if industry else []


def discover_for_client(client_id, max_leads=25):
    c = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
    icp = (c[0].get("icp_config") or {}) if c else {}
    queries = _queries(icp)
    if not queries:
        return {"ok": False, "reason": "no discovery_queries/industry+geos in icp_config"}
    created, scanned, details_calls = 0, 0, 0
    for q in queries:
        if created >= max_leads:
            break
        res = google_places.discover(q, limit=20)  # free text search; no Details billed here
        if not res.get("ok"):
            return res  # e.g. no key
        for f in res["results"]:
            if created >= max_leads:
                break
            scanned += 1
            # dedup on the free name/address key FIRST (no paid call)
            dk = urllib.parse.quote(f["dedupe_key"], safe="")
            ex = db.select("companies", "dedupe_key=eq.%s&select=id" % dk)
            if ex:
                cid = ex[0]["id"]
            else:
                # genuinely new candidate -> NOW pay for the website (lazy), then dedup again by resolved domain
                det = google_places.get_website(f.get("place_id"), client_id)
                details_calls += 1
                website = det.get("website") if det.get("ok") else None
                dom = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0] if website else None
                key2 = dom or f["dedupe_key"]
                ex2 = db.select("companies", "dedupe_key=eq.%s&select=id" % urllib.parse.quote(key2, safe=""))
                if ex2:
                    cid = ex2[0]["id"]
                else:
                    cid = db.insert("companies", {"dedupe_key": key2, "name": f["name"], "website": website, "domain": dom})[0]["id"]
            link = db.select("client_leads", "client_id=eq.%s&company_id=eq.%s&select=id" % (client_id, cid))
            if not link:
                db.insert("client_leads", {"client_id": client_id, "company_id": cid,
                                           "state": "DISCOVERED", "source": "discovery_places"}, returning=False)
                created += 1
    return {"ok": True, "scanned": scanned, "created": created, "details_calls": details_calls}
