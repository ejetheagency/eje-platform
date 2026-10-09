# factory/workers/deliveries.py
# THE DELIVERED LEDGER (client_deliveries). A contact is delivered to a client ONCE, EVER
# (unique client_id + contact_key). The single source of truth for every client-facing count
# (Decisores, leads shown, contacted). Backend/service_role only (RLS). contact_key = lowercased email
# (the stable contact identity in the app-facing leads). release/publish must never schedule a key already here.
import datetime
from factory.packages import db


def _ckey(ld, row=None):
    return ((ld.get("contactEmail") or (row or {}).get("contact_email") or "")).strip().lower()


def _shippable(ld):
    return bool((ld.get("contactName") or ld.get("decisor")) and ld.get("contactEmail") and not ld.get("emailBounced"))


def delivered_leads(client_id, today=None):
    """Leads actually delivered to the client = approved AND source_date <= today AND a real contact."""
    today = today or datetime.date.today().isoformat()
    rows = db.select_all("leads", "client_id=eq.%s&select=id,contact_email,source_date,lead_data" % client_id)
    return [r for r in rows if (r.get("lead_data") or {}).get("approved")
            and (r.get("source_date") or "") <= today and _shippable(r.get("lead_data") or {})]


def backfill(client_id, today=None):
    """Seed the ledger from the client's real delivered reports. Dedup by contact, keep the FIRST report_date.
    Idempotent (reseeds the client's rows)."""
    rows = delivered_leads(client_id, today)
    first = {}
    for r in sorted(rows, key=lambda x: (x.get("source_date") or "")):
        k = _ckey(r.get("lead_data") or {}, r)
        if k and k not in first:
            first[k] = {"client_id": client_id, "contact_key": k, "lead_id": r["id"], "report_date": r.get("source_date")}
    db.delete("client_deliveries", "client_id=eq.%s" % client_id)   # idempotent reseed
    for row in first.values():
        db.insert("client_deliveries", row, returning=False)
    return {"client_id": client_id, "delivered_rows": len(rows), "ledger": len(first), "collapsed": len(rows) - len(first)}


def delivered_keys(client_id):
    """Set of contact_keys already delivered to this client (for release/publish dedup)."""
    return {r["contact_key"] for r in db.select_all("client_deliveries", "client_id=eq.%s&select=contact_key" % client_id)}


def count(client_id):
    """The authoritative client-facing count (Decisores = distinct delivered contacts)."""
    return db.count("client_deliveries", "client_id=eq.%s" % client_id)


def record(client_id, contact_key, lead_id, report_date):
    """Record a new delivery. Returns False if the contact was already delivered (unique constraint)."""
    try:
        db.insert("client_deliveries", {"client_id": client_id, "contact_key": (contact_key or "").strip().lower(),
                                         "lead_id": lead_id, "report_date": report_date}, returning=False)
        return True
    except Exception:
        return False


def sync(client_id, today=None):
    """Record any newly-delivered contact not yet in the ledger (keeps the ledger current each night). Idempotent."""
    have = delivered_keys(client_id)
    n = 0
    for r in delivered_leads(client_id, today):
        k = _ckey(r.get("lead_data") or {}, r)
        if k and k not in have:
            if record(client_id, k, r["id"], r.get("source_date")):
                have.add(k); n += 1
    return {"client_id": client_id, "recorded": n}


def sync_all():
    """Record new deliveries for every client that has a ledger history (run in the nightly after release/publish)."""
    cids = {r["client_id"] for r in db.select_all("client_deliveries", "select=client_id")}
    return {c: sync(c) for c in cids}


if __name__ == "__main__":
    import sys
    print(backfill(sys.argv[1] if len(sys.argv) > 1 else "2uplatam"))
