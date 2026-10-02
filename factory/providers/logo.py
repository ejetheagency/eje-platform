# factory/providers/logo.py
# Asset worker (D7), $0, no key. Resolves a logo URL via unavatar (free) by domain and stores it in
# assets + companies.logo_url. The app's render-time quality gate (<40px dropped -> premium monogram)
# stays as the final fallback, so nothing ever shows a broken image. Brandfetch (better) can be added
# as a second source once a key is provided — same contract, one more file.
import urllib.request
from factory.packages import db, budget

PROVIDER = "logo"
EST_USD = 0.0


def _ok_image(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; EJEFactory/1.0)"})
        with urllib.request.urlopen(req, timeout=12) as r:
            ct = r.headers.get("Content-Type", "")
            return r.status == 200 and ct.startswith("image")
    except Exception:
        return False


def resolve(company_id):
    rows = db.select("companies", "id=eq.%s&select=domain,website,logo_url" % company_id)
    if not rows:
        return {"ok": False, "reason": "no company"}
    co = rows[0]
    if co.get("logo_url"):
        return {"ok": True, "reason": "already has logo", "url": co["logo_url"]}
    dom = co.get("domain")
    if not dom and co.get("website"):
        dom = co["website"].replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    if not dom:
        return {"ok": False, "reason": "no domain"}
    url = "https://unavatar.io/%s?fallback=false" % dom
    if not _ok_image(url):
        return {"ok": False, "reason": "no logo resolved (monogram fallback stays)"}
    db.update("companies", "id=eq.%s" % company_id, {"logo_url": url})
    db.insert("assets", {"company_id": company_id, "kind": "logo", "url": url, "source": "unavatar"}, returning=False)
    budget.log_cost(PROVIDER, EST_USD, company_id=company_id, job_type="assets", estimated=False)
    return {"ok": True, "url": url}
