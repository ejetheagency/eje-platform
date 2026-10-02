# factory/workers/tier2.py
# Tier-2 contact finding (D4). Finds a NAMED decision-maker + email for a company and creates a contact,
# so the lead can pass gates -> READY. Cascade (cheapest/best first): Hunter domain-search now;
# Apollo + Prospeo chain in as fallbacks. Moves T2_ENRICHING -> GATE_CHECK.
from factory.packages import db, lead_state
from factory.providers import hunter

try:
    from factory.providers import apollo
except Exception:
    apollo = None
try:
    from factory.providers import prospeo
except Exception:
    prospeo = None


def _domain(co):
    d = co.get("domain")
    if not d and co.get("website"):
        d = co["website"].replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    return d


def _upsert_contact(company_id, name, first, title, email, source):
    el = (email or "").lower()
    ex = db.select("contacts", "company_id=eq.%s&email=eq.%s&select=id" % (company_id, el)) if el else []
    if ex:
        return ex[0]["id"]
    return db.insert("contacts", {"company_id": company_id, "full_name": name, "first_name": first,
                                  "title": title, "email": email, "email_status": "verified",
                                  "email_source": source, "is_decision_maker": True})[0]["id"]


def find_contact(company_id, client_id=None):
    rows = db.select("companies", "id=eq.%s&select=domain,website,name" % company_id)
    if not rows:
        return {"ok": False, "reason": "no company"}
    # REUSE (stop-on-success / enrich-once): if a verified decisor contact already exists for this company
    # (from any prior run or ANY client), use it — no paid lookup. This is what makes repeat companies cost $0.
    cached = db.select("contacts", "company_id=eq.%s&is_decision_maker=eq.true&email=not.is.null&select=id,full_name,email&limit=1" % company_id)
    if cached:
        c = cached[0]
        return {"ok": True, "found": True, "contact_id": c["id"], "email": c["email"], "name": c.get("full_name"), "via": "cached"}
    dom = _domain(rows[0])
    if not dom:
        return {"ok": False, "reason": "no domain"}

    # 1) Hunter: name + email in one call
    r = hunter.find_decisor(dom, client_id)
    if r.get("ok") and r.get("found") and r.get("email"):
        name = ((r.get("first_name") or "") + " " + (r.get("last_name") or "")).strip()
        cid = _upsert_contact(company_id, name, r.get("first_name"), r.get("title"), r["email"], "hunter")
        return {"ok": True, "found": True, "contact_id": cid, "email": r["email"], "name": name, "via": "hunter"}

    # 2) Apollo (name, maybe email) -> Prospeo (email for that name) as fallback
    if apollo:
        a = apollo.find_decisor(dom, client_id)
        if a.get("ok") and a.get("found"):
            email, source = a.get("email"), "apollo"
            if (not email or "email_not_unlocked" in str(email)) and prospeo and a.get("first_name"):
                p = prospeo.find_email(a["first_name"], a.get("last_name") or "", dom, client_id)
                if p.get("ok") and p.get("email"):
                    email, source = p["email"], "prospeo"
            if email and "email_not_unlocked" not in str(email):
                name = ((a.get("first_name") or "") + " " + (a.get("last_name") or "")).strip()
                cid = _upsert_contact(company_id, name, a.get("first_name"), a.get("title"), email, source)
                return {"ok": True, "found": True, "contact_id": cid, "email": email, "name": name, "via": source}

    return {"ok": True, "found": False}


def run(client_lead_id):
    rows = db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,state" % client_lead_id)
    if not rows:
        return {"skip": "no lead"}
    cl = rows[0]
    r = find_contact(cl["company_id"], cl["client_id"])
    if r.get("contact_id"):
        db.update("client_leads", "id=eq.%s" % cl["id"], {"contact_id": r["contact_id"]})
    if cl["state"] == "T2_ENRICHING":
        lead_state.move(cl["id"], "GATE_CHECK")
    return r
