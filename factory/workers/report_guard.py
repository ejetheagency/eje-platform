# factory/workers/report_guard.py
# HARD RULE (operator 2026-10-08): NEVER write to a paying client's report without (1) a fresh BACKUP and
# (2) a DEDUP check against the client's existing pool. A paying client's report (e.g. 2uplatam / Fernando) is
# PRODUCTION, not a workspace. Always: backup(client) -> dedup(client, candidates) -> write ONLY dedup['new'].
import os, json, datetime, re
from factory.packages import db

BACKUP_DIR = os.path.expanduser("~/claude/eje-leads/report-backups")


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _root(d):
    return (d or "").lower().replace("www.", "").split("/")[0]


def backup(client_id, ts=None):
    """Snapshot ALL of a client's leads to a timestamped JSON so any write is reversible. Returns {path, rows}."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    rows = db.select_all("leads", "client_id=eq.%s&select=id,company,contact_name,contact_email,status,source_date,lead_data,updated_at" % client_id)
    stamp = ts or datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(BACKUP_DIR, "%s-%s.json" % (client_id, stamp))
    json.dump(rows, open(path, "w"), ensure_ascii=False, indent=1)
    return {"path": path, "rows": len(rows)}


def dedup(client_id, candidates):
    """candidates = [{'domain','email','company'}]. Returns {'new', 'dup', 'pool'} checked against the client's
    existing pool by domain-root, exact email, and normalized company name. Write ONLY the 'new' ones."""
    rows = db.select_all("leads", "client_id=eq.%s&select=id,company,contact_email" % client_id)
    domains = {_root(r["id"]) for r in rows}
    emails = {(r.get("contact_email") or "").lower() for r in rows if r.get("contact_email")}
    names = {_norm(r.get("company")) for r in rows if r.get("company")}
    new, dup = [], []
    for c in candidates:
        d = _root(c.get("domain") or "")
        e = (c.get("email") or "").lower()
        n = _norm(c.get("company"))
        if d and d in domains:
            dup.append({"cand": c, "why": "domain %s already in pool" % d})
        elif e and e in emails:
            dup.append({"cand": c, "why": "email %s already in pool" % e})
        elif n and n in names:
            dup.append({"cand": c, "why": "company name already in pool"})
        else:
            new.append(c)
    return {"new": new, "dup": dup, "pool": len(rows)}


if __name__ == "__main__":
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else "2uplatam"
    b = backup(cid)
    print("backup:", b["path"], "(%d rows)" % b["rows"])
