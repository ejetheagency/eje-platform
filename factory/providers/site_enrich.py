# factory/providers/site_enrich.py
# Tier-1, $0, no key. Fetches a company's own site (homepage + common contact subpages) and regex-extracts
# email / instagram / linkedin / phone, writing each to the shared findings board. Deterministic, free.
import re, urllib.request
from factory.packages import db, budget

PROVIDER = "site_enrich"
EST_USD = 0.0
PAGES = ["", "/contact", "/contacto", "/about", "/nosotros", "/equipo", "/team", "/quienes-somos"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; EJEFactory/1.0)"}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IG_RE = re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,30})")
LI_RE = re.compile(r"linkedin\.com/(company|in)/[A-Za-z0-9_\-./%]+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
JUNK_EMAIL = ("example.com", "sentry", "wixpress", ".png", ".jpg", "@2x", "domain.com")
JUNK_IG = ("p", "reel", "explore", "accounts", "tv", "stories")


def _fetch(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read(600000).decode("utf-8", "ignore")
    except Exception:
        return ""


def enrich(company_id):
    rows = db.select("companies", "id=eq.%s&select=domain,website,name,instagram" % company_id)
    if not rows:
        return {"ok": False, "reason": "no company"}
    co = rows[0]
    base = (co.get("website") or (("https://" + co["domain"]) if co.get("domain") else "")).rstrip("/")
    if not base:
        return {"ok": False, "reason": "no website/domain"}
    if not base.startswith("http"):
        base = "https://" + base

    emails, igs, lis, phones = set(), set(), set(), set()
    for p in PAGES:
        html = _fetch(base + p)
        if not html:
            continue
        for e in EMAIL_RE.findall(html):
            el = e.lower()
            if not any(j in el for j in JUNK_EMAIL):
                emails.add(el)
        for h in IG_RE.findall(html):
            if h.lower() not in JUNK_IG:
                igs.add(h)
        m = LI_RE.search(html)
        if m:
            lis.add(m.group(0))
        if p in ("", "/contact", "/contacto"):
            for ph in PHONE_RE.findall(html)[:3]:
                phones.add(re.sub(r"\s+", " ", ph).strip())

    found = {}
    if emails:
        found["email_candidates"] = sorted(emails)[:8]
    if igs:
        found["instagram"] = sorted(igs, key=len)[0]
    if lis:
        found["linkedin"] = sorted(lis)[0]
    if phones:
        found["phone_candidates"] = sorted(phones)[:3]

    for field, value in found.items():
        db.insert("enrichment_findings", {
            "company_id": company_id, "field": field, "value": value,
            "source": PROVIDER, "confidence": 0.7, "cost_usd": 0,
        }, returning=False)
    if found.get("instagram") and not co.get("instagram"):
        db.update("companies", "id=eq.%s" % company_id, {"instagram": found["instagram"]})
    budget.log_cost(PROVIDER, EST_USD, company_id=company_id, job_type="enrich_t1", estimated=False)
    return {"ok": True, "found": list(found.keys())}
