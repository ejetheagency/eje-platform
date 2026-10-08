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
    # NET-NEW tonight (operator, 2026-10-08, corrected after Night 1): the 3-night gate counts ONLY auto_approved_tonight.
    # We key on the IMMUTABLE created_at column, not approvedAt — publish.py re-stamps approvedAt=now on existing approved
    # cards every run, which inflated Night 1 to 50 when only 15 were real. publish.py auto-approves ONLY brand-new cards
    # (prev is None), so "created tonight AND approvedBy=auto" is exactly the true net-new. The hand-staged buffer is
    # reported separately as CONTEXT and never counts toward the gate.
    auto_tonight = _c("leads", "%s&lead_data->>approvedBy=eq.auto&created_at=gte.%s" % (base, since_iso))
    miner_tonight = _c("leads", "%s&lead_data->>source=eq.agent_miner&updated_at=gte.%s" % (base, since_iso))
    buffer_approved = _c("leads", "%s&lead_data->>approved=eq.true" % base)  # whole-pool snapshot — CONTEXT only
    f = {
        "discovered": discovered,                                  # tonight (from the run's pool_floor)
        "enriched":   gr("company_name"),                          # tonight: reached the gates = was enriched
        "named":      gr("decision_maker", True),                  # tonight: passed the named-decisor gate
        "email":      gr("email_deliverable", True),               # tonight: passed email-deliverable
        "verified":   gr("email_verified", True),                  # tonight: passed email-verified (or soft)
        "channels":   gr("channels", True),                        # tonight: passed the >=2-channel bar
        "ready":      _c("client_leads", "%s&state=eq.READY" % base),   # snapshot: currently READY
        "published":  published,                                   # tonight (from publish's return)
        "auto_approved_tonight": auto_tonight,    # NET-NEW: the ONLY number the 3-night gate counts
        "miner_staged_tonight":  miner_tonight,   # NET-NEW: staged (approved=false), judged by hand tomorrow
        "buffer_approved":       buffer_approved, # CONTEXT ONLY: hand-staged pool, NEVER counts toward the gate
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
    order = ["discovered", "enriched", "named", "email", "verified", "channels", "ready", "published"]
    core = " | ".join("%s %s" % (k, _n(f[k])) for k in order)
    net = "auto-approved tonight %s | miner staged tonight %s | (buffer approved %s — NOT counted)" % (
        _n(f.get("auto_approved_tonight")), _n(f.get("miner_staged_tonight")), _n(f.get("buffer_approved")))
    miss = ", ".join("%s %d" % (k, n) for k, n in list(v["missing_tally"].items())[:4])
    qual = "cards valid %d%% (%d/%d)%s" % (v["pct"], v["passed"], v["total"], ("; missing: " + miss) if miss else "")
    return "%s:\n  funnel: %s\n  NET-NEW: %s\n  quality: %s" % (client_id, core, net, qual)


def report(clients_results, preflight_line=None, spend_trace=None, fatal=None):
    """clients_results = {client_id: compute()-result}. Returns (subject, body) for notify().
    preflight_line = the first-line pre-flight string; spend_trace = list of per-step spend strings;
    fatal = {"step","error"} if the run crashed (the email still goes out — silence is never an outcome)."""
    lines = [line(cid, res) for cid, res in clients_results.items()]
    total_auto = sum((res["funnel"].get("auto_approved_tonight") or 0) for res in clients_results.values())
    gate = "PASS" if total_auto > 0 else "FAIL"
    head = []
    if preflight_line:
        head.append(preflight_line)
    head.append("GATE (auto-approved tonight > 0): %s  —  %d auto-approved across %d client(s)" % (
        gate, total_auto, len(clients_results)))
    if fatal:
        subject = "NIGHTLY CRASHED at %s — gate %s (%d auto-approved)" % (fatal.get("step"), gate, total_auto)
        head.insert(0, "RUN DIED at %s: %s" % (fatal.get("step"), fatal.get("error")))
    else:
        subject = "nightly: %d auto-approved tonight — gate %s" % (total_auto, gate)
    parts = ["EJE factory night funnel (NET-NEW only; buffer shown for context, NOT counted)", ""]
    parts += head + [""] + lines
    if spend_trace:
        parts += ["", "spend trace (cumulative USD today, per step):"] + list(spend_trace)
    parts += ["",
              "Stages: discovered -> enriched -> named -> email -> verified -> channels -> READY -> published",
              "Gate = auto-approved tonight (approvedBy=auto, approvedAt >= run start), three nights in a row.",
              "Miner stays STAGED (approved=false) — judged by hand; it never counts toward the gate."]
    return subject, "\n".join(parts)
