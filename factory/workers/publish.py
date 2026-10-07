# factory/workers/publish.py
# Bridge: factory output (client_leads READY + companies/contacts + composed) -> the legacy `leads` table that
# app.html reads for each client workspace. WITHOUT this, new factory leads never reach the app: reports.build only
# precomputes the `reports` table, which no client view consumes. This publishes each READY lead as a contact card.
# Idempotent + non-destructive: upsert by (client_id, id=domain). NEW cards get source_date=report_date + status
# 'none'; EXISTING rows keep the operator's status + source_date, only lead_data/score/contact are refreshed.
# run_nightly scopes this to access=='full' clients so legacy surfaces (2uplatam) and EJE's own pool are untouched.
import datetime
from factory.packages import db
try:
    from factory.workers import scoring, tsa, fit
except Exception:
    scoring = None

# A "company" whose only web presence is a social page gets a junk domain; never key an app lead by these.
GENERIC_DOMAINS = {"facebook.com", "m.facebook.com", "business.facebook.com", "instagram.com", "linkedin.com",
                   "twitter.com", "x.com", "youtube.com", "tiktok.com", "wa.me", "whatsapp.com", "linktr.ee",
                   "google.com", "sites.google.com", "wixsite.com", "bit.ly"}


def _today():
    return datetime.date.today().isoformat()


def _pitch_text(comp):
    p = comp.get("pitch") if isinstance(comp, dict) else None
    if isinstance(p, dict):
        return p.get("body") or p.get("text") or p.get("message") or ""
    return p or ""


def _merge(tpl, co, ct, sender=""):
    # TEMPLATE FLOOR: fill the client's first-touch template with merge fields. Guarantees a non-empty pitch so a
    # card is NEVER blank, even when the AI composer produced nothing. The composed pitch always wins when present.
    # Tokens: {first} decisor first name, {decisor} full name, {company} target, {industry}, {sender} the client's
    # person, {brands} similar brands (AI fills; floor degrades to "la tuya" so the sentence still reads right).
    first = ((ct.get("full_name") or "").split() or [""])[0]
    return (str(tpl or "").replace("{first}", first or "ahí").replace("{company}", co.get("name") or "tu marca")
            .replace("{decisor}", ct.get("full_name") or first or "").replace("{industry}", co.get("industry") or "")
            .replace("{sender}", sender or "el equipo").replace("{brands}", "la tuya"))


def publish(client_id, report_date=None):
    report_date = report_date or _today()
    rows = db.select_all("client_leads",
                         "client_id=eq.%s&state=eq.READY&select=id,company_id,contact_id,score,composed" % client_id)
    existing = {r["id"]: r for r in db.select_all("leads", "client_id=eq.%s&select=id,status,source_date" % client_id)}
    ic = ((db.select("clients", "id=eq.%s&select=icp_config" % client_id) or [{}])[0].get("icp_config") or {})
    geo = ic.get("geo") or ""
    tpl = ic.get("outreach_first_touch") or ""
    sender = ic.get("sender_name") or ""
    ig_t = ic.get("outreach_ig") or ""
    fu_t = ic.get("outreach_email_followup") or ""
    li_t = ic.get("outreach_linkedin") or ""
    published = 0
    added = 0
    skipped = 0
    for cl in rows:
        co = (db.select("companies",
                        "id=eq.%s&select=name,domain,website,instagram,linkedin,brief,logo_url,country,industry" % cl["company_id"]) or [{}])[0]
        dom = (co.get("domain") or "").lower().strip()
        if not dom or dom in GENERIC_DOMAINS:  # no key / shared social host -> cannot key a lead row
            continue
        if client_id not in tsa.NO_WEBSITE_OK and tsa and not tsa.real_domain(dom):  # default: real website required
            skipped += 1
            continue
        ct = {}
        if cl.get("contact_id"):
            ct = (db.select("contacts", "id=eq.%s&select=full_name,title,email,phone,instagram,linkedin_url" % cl["contact_id"]) or [{}])[0]
        sigs = db.select("signals", "company_id=eq.%s&select=type&limit=5" % cl["company_id"])
        if not tsa.passes_contact(ct):  # TSA: never publish a lead without a named decisor + non-bounced email
            skipped += 1
            continue
        chan_ok, _chan_why = tsa.channels_ok(ct, co, ic)  # MULTI-CHANNEL gate: >= min_channels + required (per ICP)
        if not chan_ok:
            skipped += 1
            continue
        comp = cl.get("composed") or {}
        # RE-SCORE on CURRENT enrichment (the stored client_lead.score is the stale pre-enrichment value;
        # a READY lead with email+decisor+brief+IG should read ~60-72 "fit", not its early 10-20).
        try:
            fscore = int(fit.fit_score(co, ct, sigs, ic))
        except Exception:
            fscore = int(cl.get("score") or 0)
        prev = existing.get(dom)
        sd = (prev or {}).get("source_date") or report_date
        status = (prev or {}).get("status") or "none"
        ld = {
            "_key": dom, "companyName": co.get("name"), "contactName": ct.get("full_name") or "",
            "contactEmail": ct.get("email") or "", "contactTitle": ct.get("title") or "",
            "country": co.get("country") or geo, "website": (co.get("website") if (tsa and tsa.real_website(co.get("website") or "")) else ""),  # REAL website or EMPTY — never fabricate from a synthetic domain
            "industry": co.get("industry") or "", "instagramHandle": co.get("instagram") or "",
            "instagramKind": "profile" if co.get("instagram") else "", "instagramFollowers": 0,
            "contactLinkedIn": ct.get("linkedin_url") or co.get("linkedin") or "",
            "whatsapp": ct.get("phone") or "",  # WhatsApp micro-route (wa.me/tel regex) — the deep channel
            "pitchEmailES": _pitch_text(comp) or _merge(tpl, co, ct, sender), "sectorTemplate": tpl, "sender": sender,
            "instagramDM": _merge(ig_t, co, ct, sender), "followupEmail": _merge(fu_t, co, ct, sender), "linkedinDM": _merge(li_t, co, ct, sender),
            "companyBrief": co.get("brief") or "",
            "whyICP": "", "companyEmail": None, "score": fscore,
            "source_date": sd, "whyNow": [s["type"] for s in (sigs or [])],
            "additionalContacts": [], "_verifiedCredits": [],
        }
        base = {"company": co.get("name") or dom, "contact_name": ct.get("full_name") or None,
                "contact_email": ct.get("email") or None, "score": fscore,
                "lead_data": ld, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        if prev:
            db.update("leads", "id=eq.%s&client_id=eq.%s" % (dom, client_id), base)
        else:
            row = dict(base)
            row.update({"id": dom, "client_id": client_id, "status": status, "source_date": sd})
            try:
                db.insert("leads", row, returning=False)
                added += 1
            except Exception:  # domain already a lead (possibly under another client; leads.id is global) -> update-or-skip
                updated = db.update("leads", "id=eq.%s&client_id=eq.%s" % (dom, client_id), base)
                if not updated:
                    skipped += 1
                    continue
        published += 1
    return {"client_id": client_id, "published": published, "added": added, "skipped": skipped}


def publish_full_access(report_date=None, only=None):
    """Publish for every access=='full' client (the client workspaces the app surfaces from the factory)."""
    fulls = [c["id"] for c in db.select("clients", "select=id,icp_config")
             if (c.get("icp_config") or {}).get("access") == "full"]
    if only:
        fulls = [c for c in fulls if c == only]
    return {cid: publish(cid, report_date=report_date) for cid in fulls}
