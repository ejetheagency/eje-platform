# factory/workers/reverify.py
# Nightly sweep: a lead that was NAMED (has a contact + email) but never got its email verified -- e.g. Gate A
# named it on a night the verify cap (night_credit_cap) was already exhausted, so it parked on email_verified --
# is moved back to GATE_CHECK and re-queued for verify. Bounded per client so a fresh night's cap works through
# the backlog a slice at a time. Makes named-but-unverified leads reach READY on a later run, with no human/cron.
import datetime
from factory.packages import db, queue, lead_state


def reenrich_parked(client_id=None, cap=120, stale_hours=36):
    # The OTHER parked bucket: leads that parked for NO decisor found or NO email (sweep() only handles the
    # have-contact+email case). Re-queue them through the enrichment chain so the (upgraded) site_decisor gets
    # another pass -- this is how the factory recovers leads that parked before the extractor was improved, or
    # that need a second look. Guard: only leads untouched for `stale_hours` (so a fresh park isn't re-run every
    # night and a genuinely-dead lead re-runs at most once per cycle, not in a tight loop). Bounded per run.
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=stale_hours)).isoformat()
    clients = [client_id] if client_id else [c["id"] for c in db.select("clients", "select=id")]
    n = 0
    for cid in clients:
        rows = db.select("client_leads",
                         "client_id=eq.%s&state=eq.PARKED&updated_at=lt.%s&select=id,company_id,contact_id&order=updated_at.asc&limit=%d"
                         % (cid, cutoff, cap))
        for r in rows:
            if n >= cap:
                break
            missing = not r.get("contact_id")
            if not missing:
                ct = db.select("contacts", "id=eq.%s&select=email" % r["contact_id"])
                missing = not (ct and ct[0].get("email"))
            if missing:
                try:
                    lead_state.move(r["id"], "T1_ENRICHING")
                    queue.enqueue("enrich_t1", client_id=cid, company_id=r["company_id"], client_lead_id=r["id"])
                    n += 1
                except Exception:
                    pass
    return n


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
