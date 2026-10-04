# factory/workers/reverify.py
# Nightly sweep: a lead that was NAMED (has a contact + email) but never got its email verified -- e.g. Gate A
# named it on a night the verify cap (night_credit_cap) was already exhausted, so it parked on email_verified --
# is moved back to GATE_CHECK and re-queued for verify. Bounded per client so a fresh night's cap works through
# the backlog a slice at a time. Makes named-but-unverified leads reach READY on a later run, with no human/cron.
from factory.packages import db, queue, lead_state


def sweep(client_id=None, cap=80):
    clients = [client_id] if client_id else [c["id"] for c in db.select("clients", "select=id")]
    n = 0
    for cid in clients:
        rows = db.select("client_leads",
                         "client_id=eq.%s&state=eq.PARKED&contact_id=not.is.null&select=id,company_id,contact_id&limit=%d" % (cid, cap))
        for r in rows:
            if n >= cap:
                break
            ct = db.select("contacts", "id=eq.%s&select=email,email_verified_at" % r["contact_id"])
            if ct and ct[0].get("email") and not ct[0].get("email_verified_at"):
                try:
                    lead_state.move(r["id"], "GATE_CHECK")
                    queue.enqueue("verify", client_id=cid, company_id=r["company_id"], client_lead_id=r["id"])
                    n += 1
                except Exception:
                    pass
    return n
