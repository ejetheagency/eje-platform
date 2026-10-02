# factory/providers/brandfetch.py
# Better logos via Brandfetch. READY, needs BRANDFETCH_API_KEY. Falls back to logo.py (unavatar) when absent,
# and the app's monogram stays the final render-time fallback. UNTESTED until a key is present.
import os, json, urllib.request
from factory.packages import db, budget

PROVIDER = "brandfetch"
EST_USD = 0.0  # free tier
API = "https://api.brandfetch.io/v2/brands/"


def resolve(company_id):
    key = os.environ.get("BRANDFETCH_API_KEY")
    rows = db.select("companies", "id=eq.%s&select=domain,website,logo_url" % company_id)
    if not rows:
        return {"ok": False, "reason": "no company"}
    co = rows[0]
    if co.get("logo_url"):
        return {"ok": True, "reason": "already has logo"}
    dom = co.get("domain")
    if not dom and co.get("website"):
        dom = co["website"].replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    if not dom:
        return {"ok": False, "reason": "no domain"}
    if not key:
        # no key: defer to the free unavatar adapter
        from factory.providers import logo
        return logo.resolve(company_id)
    req = urllib.request.Request(API + dom, headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=15) as r:
        j = json.loads(r.read().decode())
    url = None
    for logo_obj in (j.get("logos") or []):
        for fmt in (logo_obj.get("formats") or []):
            if fmt.get("src"):
                url = fmt["src"]
                break
        if url:
            break
    if not url:
        from factory.providers import logo
        return logo.resolve(company_id)
    db.update("companies", "id=eq.%s" % company_id, {"logo_url": url})
    db.insert("assets", {"company_id": company_id, "kind": "logo", "url": url, "source": "brandfetch"}, returning=False)
    budget.log_cost(PROVIDER, EST_USD, company_id=company_id, job_type="assets", estimated=False)
    return {"ok": True, "url": url}
