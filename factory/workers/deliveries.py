# factory/workers/deliveries.py
# THE DELIVERED LEDGER (client_deliveries). A contact is delivered to a client ONCE, EVER
# (unique client_id + contact_key). The single source of truth for every client-facing count
# (Decisores, leads shown, contacted). Backend/service_role only (RLS). contact_key = lowercased email
# (the stable contact identity in the app-facing leads). release/publish must never schedule a key already here.
import datetime, json, os
from factory.packages import db

BACKUP_DIR = os.path.expanduser("~/claude/eje-leads/report-backups")

# What counts as "the client ACTED on this card". Every table the app writes when Fernando does something
# (copied/sent a message, completed a step, moved a status, or pulled the lead into Seguimiento) plus the
# outreach engagement log. (table, the column holding the lead identity). tracked_leads is keyed by CONTACT,
# not lead_id, so it is read separately below.
ACTIVITY_TABLES = (("messages_sent", "lead_id"), ("sent_actuals", "lead_id"), ("actions", "lead_id"),
                   ("status_history", "lead_id"), ("engagement_events", "client_lead_id"))


def _ckey(ld, row=None):
    return ((ld.get("contactEmail") or (row or {}).get("contact_email") or "")).strip().lower()


def _shippable(ld):
    return bool((ld.get("contactName") or ld.get("decisor")) and ld.get("contactEmail") and not ld.get("emailBounced"))


def delivered_leads(client_id, today=None):
    """Leads actually delivered to the client = approved AND a real contact AND a REPORT DATE that has arrived.
    The non-empty source_date test is not decoration: a pooled card has source_date NULL, and "" <= today is
    TRUE in string order, so without it the whole invisible pool reads as delivered and the nightly sync()
    writes it into the ledger (which is what the client's Decisores count shows). Pool is not delivered."""
    today = today or datetime.date.today().isoformat()
    rows = db.select_all("leads", "client_id=eq.%s&select=id,contact_email,source_date,lead_data" % client_id)
    return [r for r in rows if (r.get("lead_data") or {}).get("approved")
            and (r.get("source_date") or "") and (r.get("source_date") or "") <= today
            and _shippable(r.get("lead_data") or {})]


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


def touched(client_id):
    """What the client has ACTUALLY acted on: {'lead_ids', 'contact_keys'}. Read-only.
    RAISES if any source table cannot be read. A swallowed error here would read as "nobody acted on anything",
    and that is the input that decides whether a delivery may be revoked: it must fail loudly, never quietly."""
    lead_ids, keys = set(), set()
    for table, col in ACTIVITY_TABLES:
        rows = db.select_all(table, "client_id=eq.%s&select=%s" % (client_id, col))
        lead_ids |= {r[col] for r in rows if r.get(col)}
    for r in db.select_all("tracked_leads", "client_id=eq.%s&select=contact_email" % client_id):
        if r.get("contact_email"):
            keys.add(r["contact_email"].strip().lower())
    return {"lead_ids": lead_ids, "contact_keys": keys}


def is_actioned(row, t):
    """Did the client act on THIS card? Any activity row, Seguimiento entry, or a status off 'none'."""
    return bool(row["id"] in t["lead_ids"]
                or (_ckey(row.get("lead_data") or {}, row) and _ckey(row.get("lead_data") or {}, row) in t["contact_keys"])
                or (row.get("status") or "none") not in ("none", ""))


def backup_ledger(client_id, ts=None):
    """Snapshot a client's ledger rows before any revoke, so removing a delivery is reversible like every other
    write to a paying client's report (CLAUDE.md hard rule)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    rows = db.select_all("client_deliveries", "client_id=eq.%s&select=*" % client_id)
    stamp = ts or datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(BACKUP_DIR, "ledger-%s-%s.json" % (client_id, stamp))
    json.dump(rows, open(path, "w"), ensure_ascii=False, indent=1)
    return {"path": path, "rows": len(rows)}


def revoke(client_id, contact_key, lead_id, reason):
    """Remove ONE delivery from the ledger and append the reason to the audit log. Only ever called for a card
    the client never acted on (release.undeliver checks that); a delivery he used is not revocable."""
    key = (contact_key or "").strip().lower()
    rows = db.delete("client_deliveries", "client_id=eq.%s&contact_key=eq.%s" % (client_id, key))
    os.makedirs(BACKUP_DIR, exist_ok=True)
    with open(os.path.join(BACKUP_DIR, "undelivered.jsonl"), "a") as f:
        f.write(json.dumps({"at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "client_id": client_id,
                            "contact_key": key, "lead_id": lead_id, "reason": reason,
                            "ledger_rows_removed": rows}, ensure_ascii=False) + "\n")
    return len(rows or [])


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
