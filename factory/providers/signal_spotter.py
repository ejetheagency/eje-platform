# factory/providers/signal_spotter.py
# Signal Spotter v1 (D1.5), $0, no key. Finds "why-now" reasons from the company's OWN site: hiring
# (careers page with job language) and expansion (new-location language). These are what make someone
# reply. Writes to the `signals` table. v2 adds Serper/Places/press once keys exist (same contract).
import re, urllib.request, datetime
from factory.packages import db, budget

PROVIDER = "signal_spotter"
UA = {"User-Agent": "Mozilla/5.0 (compatible; EJEFactory/1.0)"}
CAREERS = ["/careers", "/jobs", "/empleo", "/trabaja-con-nosotros", "/vacantes", "/unete", "/work-with-us"]
NEWS = ["/news", "/blog", "/prensa", "/novedades", "/noticias"]
HIRING = ("we're hiring", "we are hiring", "estamos contratando", "job opening", "vacante", "postula",
          "apply now", "join our team", "unete al equipo", "open positions", "únete")
EXPANSION = ("new location", "nueva sede", "now open", "proxima apertura", "próxima apertura",
             "grand opening", "expanding", "nueva sucursal", "we just opened", "abrimos")


def _fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12) as r:
            return r.read(400000).decode("utf-8", "ignore").lower()
    except Exception:
        return ""


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def spot(company_id):
    rows = db.select("companies", "id=eq.%s&select=domain,website,name" % company_id)
    if not rows:
        return {"ok": False, "reason": "no company"}
    co = rows[0]
    base = (co.get("website") or (("https://" + co["domain"]) if co.get("domain") else "")).rstrip("/")
    if not base:
        return {"ok": False, "reason": "no website/domain"}
    if not base.startswith("http"):
        base = "https://" + base

    signals = []
    # hiring: a reachable careers page OR hiring language on the homepage
    home = _fetch(base)
    careers_hit = False
    for p in CAREERS:
        body = _fetch(base + p)
        if body and any(k in body for k in HIRING):
            careers_hit = True
            break
    if careers_hit or any(k in home for k in HIRING):
        signals.append(("hiring", "hiring language on site/careers page", 0.7))
    if any(k in home for k in EXPANSION):
        signals.append(("new_location", "expansion/new-location language on site", 0.6))

    for stype, detail, strength in signals:
        db.insert("signals", {"company_id": company_id, "type": stype, "detail": detail,
                              "strength": strength, "source": PROVIDER, "detected_at": _now()}, returning=False)
    budget.log_cost(PROVIDER, 0, company_id=company_id, job_type="signals", estimated=False)
    return {"ok": True, "signals": [s[0] for s in signals]}
