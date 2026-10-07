# factory/workers/tsa.py
# TSA — quality inspection, the HARD surface gate. NOTHING reaches a CLIENT without passing it. This is enforced at
# EVERY client-facing surface (publish, drip, display) so an incomplete lead can never reach a client regardless of
# what happened upstream. Non-negotiable minimum: a NAMED decisor + a VERIFIED, non-bounced email. (Channel
# completeness — IG / LinkedIn / WhatsApp — is the fuller quality bar handled by gates.py; this is the floor a client
# may never see broken.)
# NON-NEGOTIABLE (operator): a lead ships ONLY with a NAMED decisor + a VERIFIED, non-bounced email. A website is
# NOT required — a genuinely good lead with no site is usable. What is forbidden is FABRICATING one: a synthetic
# slug (e.g. "2up-moodpilates-ec", no TLD) is NOT a website, is never stored as one, and never renders as a link.
# real_domain/real_website below exist to decide whether a website LINK may be shown, not to gate shippability.
import re
from factory.packages import db

_GENERIC = {"facebook.com", "m.facebook.com", "business.facebook.com", "instagram.com", "linkedin.com", "twitter.com",
            "x.com", "youtube.com", "tiktok.com", "wa.me", "whatsapp.com", "linktr.ee", "google.com", "sites.google.com",
            "wixsite.com", "bit.ly"}
_DOMRE = re.compile(r"^[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)*\.[a-z]{2,}$")

# Per-client ICP exception (operator, 2026-10-06): clients here may ship a genuinely good lead with NO website.
# DEFAULT (every client NOT in this set) still requires a REAL website. A website is still never FABRICATED for anyone.
# ICP tightens day by day — this is the knob.
NO_WEBSITE_OK = {"2uplatam"}


def real_domain(d):
    """A REAL website domain: has a valid TLD, no spaces, not a synthetic '2up-' slug, not a social/link host."""
    d = (d or "").lower().strip().replace("www.", "")
    if not d or d.startswith("2up-") or " " in d or d in _GENERIC:
        return False
    return _DOMRE.match(d) is not None


def real_website(url):
    d = (url or "").lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    return real_domain(d)


def passes_contact(ct):
    """Factory-side: a contact clears TSA iff it has a decisor name + an email that isn't invalid/bounced.
    (Website is checked separately against the company — see real_domain, enforced in publish.)"""
    if not ct:
        return False
    if not (ct.get("full_name") or "").strip():
        return False
    em, st = ct.get("email"), ct.get("email_status")
    if not em or st in ("invalid", "bounced"):
        return False
    return True


def passes_lead_row(row):
    """Client-surface: SHIPPABLE iff named decisor + email (not bounced). Website is OPTIONAL (a good no-site lead
    ships); it is only never FABRICATED. ICP tightening (e.g. require a site for some sectors) comes later, config-driven."""
    ld = row.get("lead_data") or {}
    name = (row.get("contact_name") or ld.get("contactName") or "").strip()
    email = (row.get("contact_email") or ld.get("contactEmail") or "").strip()
    if not (name and email) or ld.get("emailBounced"):
        return False
    if row.get("client_id") in NO_WEBSITE_OK:  # ICP exception: website optional for these clients
        return True
    return real_website(ld.get("website") or (row.get("id") or ""))


def channels(ct, company=None):
    """Count the REACHABLE channels on a card (multi-channel doctrine). email(verified/found) + instagram +
    linkedin + phone/whatsapp. Returns the set of channel names present."""
    ct = ct or {}; company = company or {}
    chans = set()
    if ct.get("email") and ct.get("email_status") not in ("invalid", "bounced"):
        chans.add("email")
    if ct.get("instagram") or company.get("instagram"):
        chans.add("instagram")
    if ct.get("linkedin_url") or company.get("linkedin"):
        chans.add("linkedin")
    if ct.get("phone"):
        chans.add("phone")  # phone == WhatsApp for LatAm small biz
    return chans


def channels_ok(ct, company, icp_config=None):
    """Multi-channel READY gate (operator standard): a card needs >= min_channels (default 2), and every channel in
    the client's required_channels (e.g. EJE requires 'instagram'). Config-driven per ICP; email is always implied."""
    icp = icp_config or {}
    have = channels(ct, company)
    min_ch = int(icp.get("min_channels", 2))
    required = set(icp.get("required_channels") or [])
    if required and not required.issubset(have):
        return False, "missing required channel(s): %s" % ",".join(sorted(required - have))
    if len(have) < min_ch:
        return False, "only %d channel(s) (<%d): %s" % (len(have), min_ch, ",".join(sorted(have)))
    return True, "ok (%s)" % ",".join(sorted(have))


def enforce_ready_invariant(client_id=None):
    """Operator rule: a shippable (READY) card with NO verified email must NOT exist. It either goes BACK to the
    factory (PARKED -> re-enrich, when there is a named decisor to find an email for) or to the TRASH (DISCARDED,
    when there is no decisor = dead). Keeps the factory-side READY state honest so a no-email card can never leak."""
    from factory.packages import lead_state
    q = ("client_id=eq.%s&" % client_id if client_id else "") + "state=eq.READY&select=id,contact_id"
    recirc = trashed = 0
    for r in db.select_all("client_leads", q):
        ct = (db.select("contacts", "id=eq.%s&select=full_name,email,email_status" % r["contact_id"]) or [{}])[0] if r.get("contact_id") else {}
        if passes_contact(ct):
            continue
        if (ct.get("full_name") or "").strip():
            lead_state.move(r["id"], "PARKED", reason="invariant: READY without verified email -> back to factory")
            recirc += 1
        else:
            lead_state.move(r["id"], "DISCARDED", reason="invariant: READY without decisor+email -> trash")
            trashed += 1
    return {"client_id": client_id or "ALL", "recirculated": recirc, "trashed": trashed}


def clean_surface(client_id):
    """Scrub the client-facing `leads` table: DELETE pure junk (no decisor AND no email), HOLD the partially-complete
    (future-date so they never show/release until finished) — so the client view only ever contains TSA-passing leads."""
    rows = db.select_all("leads", "client_id=eq.%s&select=id,contact_name,contact_email,lead_data" % client_id)
    removed = held = 0
    for r in rows:
        if passes_lead_row(r):
            continue
        ld = r.get("lead_data") or {}
        name = (r.get("contact_name") or ld.get("contactName") or "").strip()
        email = (r.get("contact_email") or ld.get("contactEmail") or "").strip()
        if not name and not email:
            db.delete("leads", "id=eq.%s&client_id=eq.%s" % (r["id"], client_id))
            removed += 1
        else:
            ld["tsa_held"] = True
            ld["source_date"] = "2099-01-01"
            db.update("leads", "id=eq.%s&client_id=eq.%s" % (r["id"], client_id),
                      {"source_date": "2099-01-01", "lead_data": ld})
            held += 1
    return {"client_id": client_id, "removed_junk": removed, "held_incomplete": held}
