# factory/workers/funnel.py
# THE ONLY STATUS REPORT (operator, 2026-10-07): one funnel line per client per night, emailed with the run.
# Counts only: discovered -> enriched -> named -> email found -> verified -> channels ok -> READY -> published ->
# approved. The middle stages come from tonight's gate_results ledger (created_at >= run start); the ends come from
# the run itself (discovered/published) + a cheap snapshot (READY/approved). Plus the card-validator pass % so the
# quality bar is a number too. Read-only; never raises (an alert must not break the nightly).
from factory.packages import db
from factory.workers import card_validator


def _c(table, q):
    try:
        return db.count(table, q)
    except Exception:
        return None


def _n(v):
    return "?" if v is None else str(v)


def compute(client_id, since_iso, discovered=0, published=0):
    """Return the night's funnel counts for one client + the card-validator result over tonight's published cards."""
    base = "client_id=eq.%s" % client_id
    since = "checked_at=gte.%s" % since_iso  # gate_results stamps the gate run as checked_at (not created_at)
    gr = lambda gate, passed=None: _c("gate_results", "%s&gate=eq.%s&%s%s" % (
        base, gate, since, ("&passed=is.%s" % ("true" if passed else "false")) if passed is not None else ""))
    f = {
        "discovered": discovered,                                  # tonight (from the run's pool_floor)
        "enriched":   gr("company_name"),                          # tonight: reached the gates = was enriched
        "named":      gr("decision_maker", True),                  # tonight: passed the named-decisor gate
        "email":      gr("email_deliverable", True),               # tonight: passed email-deliverable
        "verified":   gr("email_verified", True),                  # tonight: passed email-verified (or soft)
        "channels":   gr("channels", True),                        # tonight: passed the >=2-channel bar
        "ready":      _c("client_leads", "%s&state=eq.READY" % base),   # snapshot: currently READY
        "published":  published,                                   # tonight (from publish's return)
        "approved":   _c("leads", "%s&lead_data->>approved=eq.true" % base),  # snapshot: approved cards on the app
    }
    # card-validator over tonight's published/updated cards (quality % the operator spot-checks)
    try:
        rows = db.select_all("leads", "%s&updated_at=gte.%s&select=lead_data" % (base, since_iso))
        val = card_validator.validate_batch([r.get("lead_data") or {} for r in rows])
    except Exception:
        val = {"total": 0, "passed": 0, "pct": 0, "missing_tally": {}}
    return {"funnel": f, "validator": val}


def line(client_id, res):
    f = res["funnel"]
    v = res["validator"]
    order = ["discovered", "enriched", "named", "email", "verified", "channels", "ready", "published", "approved"]
    core = " | ".join("%s %s" % (k, _n(f[k])) for k in order)
    miss = ", ".join("%s %d" % (k, n) for k, n in list(v["missing_tally"].items())[:4])
    qual = "cards valid %d%% (%d/%d)%s" % (v["pct"], v["passed"], v["total"], ("; missing: " + miss) if miss else "")
    return "%s: %s  ->  %s" % (client_id, core, qual)


def report(clients_results):
    """clients_results = {client_id: compute()-result}. Returns (subject, body) for notify()."""
    lines = [line(cid, res) for cid, res in clients_results.items()]
    total_approved = sum((res["funnel"].get("approved") or 0) for res in clients_results.values())
    subject = "nightly funnel: %d approved across %d client(s)" % (total_approved, len(clients_results))
    body = "EJE factory night funnel (counts only)\n\n" + "\n".join(lines) + \
           "\n\nStages: discovered -> enriched -> named -> email -> verified -> channels -> READY -> published -> approved"
    return subject, body
