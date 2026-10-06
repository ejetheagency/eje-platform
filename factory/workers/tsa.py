# factory/workers/tsa.py
# TSA — quality inspection, the HARD surface gate. NOTHING reaches a CLIENT without passing it. This is enforced at
# EVERY client-facing surface (publish, drip, display) so an incomplete lead can never reach a client regardless of
# what happened upstream. Non-negotiable minimum: a NAMED decisor + a VERIFIED, non-bounced email. (Channel
# completeness — IG / LinkedIn / WhatsApp — is the fuller quality bar handled by gates.py; this is the floor a client
# may never see broken.)
from factory.packages import db


def passes_contact(ct):
    """Factory-side: a contact clears TSA iff it has a decisor name + an email that isn't invalid/bounced."""
    if not ct:
        return False
    if not (ct.get("full_name") or "").strip():
        return False
    em, st = ct.get("email"), ct.get("email_status")
    if not em or st in ("invalid", "bounced"):
        return False
    return True


def passes_lead_row(row):
    """Client-surface: a `leads`-table row clears TSA iff it has a decisor name + an email and isn't flagged bounced."""
    ld = row.get("lead_data") or {}
    name = (row.get("contact_name") or ld.get("contactName") or "").strip()
    email = (row.get("contact_email") or ld.get("contactEmail") or "").strip()
    return bool(name) and bool(email) and not ld.get("emailBounced")


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
