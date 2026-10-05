# factory/workers/publish.py
# Bridge: factory output (client_leads READY + companies/contacts + composed) -> the legacy `leads` table that
# app.html reads for each client workspace. WITHOUT this, new factory leads never reach the app: reports.build only
# precomputes the `reports` table, which no client view consumes. This publishes each READY lead as a contact card.
# Idempotent + non-destructive: upsert by (client_id, id=domain). NEW cards get source_date=report_date + status
# 'none'; EXISTING rows keep the operator's status + source_date, only lead_data/score/contact are refreshed.
# run_nightly scopes this to access=='full' clients so legacy surfaces (2uplatam) and EJE's own pool are untouched.
import datetime
from factory.packages import db


def _today():
    return datetime.date.today().isoformat()


def _pitch_text(comp):
    p = comp.get("pitch") if isinstance(comp, dict) else None
    if isinstance(p, dict):
        return p.get("body") or p.get("text") or p.get("message") or ""
    return p or ""


def publish(client_id, report_date=None):
    report_date = report_date or _today()
    rows = db.select_all("client_leads",
                         "client_id=eq.%s&state=eq.READY&select=id,company_id,contact_id,score,composed" % client_id)
    existing = {r["id"]: r for r in db.select_all("leads", "client_id=eq.%s&select=id,status,source_date" % client_id)}
    geo = ((db.select("clients", "id=eq.%s&select=icp_config" % client_id) or [{}])[0].get("icp_config") or {}).get("geo") or ""
    published = 0
    added = 0
    for cl in rows:
        co = (db.select("companies",
                        "id=eq.%s&select=name,domain,website,instagram,linkedin,brief,logo_url,country,industry" % cl["company_id"]) or [{}])[0]
        dom = (co.get("domain") or "").lower().strip()
        if not dom:
            continue
        ct = {}
        if cl.get("contact_id"):
            ct = (db.select("contacts", "id=eq.%s&select=full_name,title,email" % cl["contact_id"]) or [{}])[0]
        sigs = db.select("signals", "company_id=eq.%s&select=type&limit=5" % cl["company_id"])
        comp = cl.get("composed") or {}
        prev = existing.get(dom)
        sd = (prev or {}).get("source_date") or report_date
        status = (prev or {}).get("status") or "none"
        ld = {
            "_key": dom, "companyName": co.get("name"), "contactName": ct.get("full_name") or "",
            "contactEmail": ct.get("email") or "", "contactTitle": ct.get("title") or "",
            "country": co.get("country") or geo, "website": co.get("website") or ("https://" + dom),
            "industry": co.get("industry") or "", "instagramHandle": co.get("instagram") or "",
            "instagramKind": "profile" if co.get("instagram") else "", "instagramFollowers": 0,
            "contactLinkedIn": co.get("linkedin") or "",
            "pitchEmailES": _pitch_text(comp), "companyBrief": co.get("brief") or "",
            "whyICP": "", "companyEmail": None, "score": cl.get("score") or 0,
            "source_date": sd, "whyNow": [s["type"] for s in (sigs or [])],
            "additionalContacts": [], "_verifiedCredits": [],
        }
        base = {"company": co.get("name") or dom, "contact_name": ct.get("full_name") or None,
                "contact_email": ct.get("email") or None, "score": int(cl.get("score") or 0),
                "lead_data": ld, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        if prev:
            db.update("leads", "id=eq.%s&client_id=eq.%s" % (dom, client_id), base)
        else:
            row = dict(base)
            row.update({"id": dom, "client_id": client_id, "status": status, "source_date": sd})
            db.insert("leads", row, returning=False)
            added += 1
        published += 1
    return {"client_id": client_id, "published": published, "added": added}


def publish_full_access(report_date=None, only=None):
    """Publish for every access=='full' client (the client workspaces the app surfaces from the factory)."""
    fulls = [c["id"] for c in db.select("clients", "select=id,icp_config")
             if (c.get("icp_config") or {}).get("access") == "full"]
    if only:
        fulls = [c for c in fulls if c == only]
    return {cid: publish(cid, report_date=report_date) for cid in fulls}
