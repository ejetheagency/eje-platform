# factory/workers/tsa.py
# TSA — quality inspection, the HARD surface gate. NOTHING reaches a CLIENT without passing it. This is enforced at
# EVERY client-facing surface (publish, drip, display) so an incomplete lead can never reach a client regardless of
# what happened upstream. Non-negotiable minimum: a NAMED decisor + a VERIFIED, non-bounced email. (Channel
# completeness — IG / LinkedIn / WhatsApp — is the fuller quality bar handled by gates.py; this is the floor a client
# may never see broken.)
# NON-NEGOTIABLE (operator, repeatedly): a company with NO real website OR NO email is NOT shippable. A fabricated/
# synthetic domain (e.g. "2up-moodpilates-ec", no TLD) is NOT a website.
import re
from factory.packages import db

_GENERIC = {"facebook.com", "m.facebook.com", "business.facebook.com", "instagram.com", "linkedin.com", "twitter.com",
            "x.com", "youtube.com", "tiktok.com", "wa.me", "whatsapp.com", "linktr.ee", "google.com", "sites.google.com",
            "wixsite.com", "bit.ly"}
_DOMRE = re.compile(r"^[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)*\.[a-z]{2,}$")


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
    """Client-surface: SHIPPABLE iff named decisor + email (not bounced) + a REAL website. No exceptions."""
    ld = row.get("lead_data") or {}
    name = (row.get("contact_name") or ld.get("contactName") or "").strip()
    email = (row.get("contact_email") or ld.get("contactEmail") or "").strip()
    website = ld.get("website") or (row.get("id") or "")
    return bool(name) and bool(email) and real_website(website) and not ld.get("emailBounced")


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
