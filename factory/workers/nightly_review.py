# factory/workers/nightly_review.py
# THE MACHINE REPORTS ITSELF (operator 2026-10-09, queue item 0b; PLAN principle 6 is what reads this).
#
# At the end of every nightly run, the FULL golden suite runs per client and the result goes in the FIRST lines of
# the funnel email, next to the health numbers the operator decides on: run status, providers, and per client the
# cards shipped for the next business day, the lowest fit in that report, how many days the pool still covers, the
# cost tonight against the nightly ceiling, and golden X/Y with the NAME of any FAIL.
#
# WHY the first lines: the operator's morning check is 10 minutes. If everything is green there is no dev session
# that day; if something is red, that one thing is the day's only job. That decision has to be readable at the top
# of one email, without opening the app or running anything by hand.
#
# Any FAIL (or a dead run) ALSO sends a separate alert email, because the funnel email arrives every night and a
# nightly email is easy to stop reading. An alert only arrives when something is actually wrong.
#
# HONESTY RULES, deliberate:
#   - A client with no golden suite is reported as "no golden suite", never as 0/0 PASS or as green.
#   - A rule that THROWS is a FAIL (golden.run does that), and a suite that cannot run at all says ERROR.
#   - A missing number prints "?" instead of 0. A zero we did not measure is a lie that reads as healthy.
#
#   python3 -m factory.workers.nightly_review              # print the block for every client that has a suite
#   python3 -m factory.workers.nightly_review 2uplatam
import datetime
from factory.packages import db, budget

# Clients that HAVE a golden suite today. 2uplatam's suite is client-parameterized, so its staging clone shares it.
# A client absent from here gets "no golden suite" in the email: visible, not silently green.
SUITES = {
    "2uplatam": "factory.checks.golden_2uplatam",
    "2uplatam_staging": "factory.checks.golden_2uplatam",
}


def golden_for(client_id):
    """Run one client's full golden suite. Returns {available, total, passed, failed:[(name, detail)], error}."""
    mod_path = SUITES.get(client_id)
    if not mod_path:
        return {"available": False, "total": 0, "passed": 0, "failed": [], "error": None}
    try:
        mod = __import__(mod_path, fromlist=["run"])
        results = mod.run(client_id=client_id, echo=False)
    except Exception as e:
        return {"available": True, "total": 0, "passed": 0, "failed": [], "error": str(e)[:160]}
    failed = [(name, detail) for name, ok, detail in results if not ok]
    return {"available": True, "total": len(results), "passed": len(results) - len(failed),
            "failed": failed, "error": None}


def _num(v, fmt="%s"):
    """A number we did not measure prints '?', never 0."""
    return "?" if v is None else (fmt % v)


def client_health(client_id, release=None, funnel_results=None, golden=None):
    """One client's morning numbers + its golden verdict. Pure assembly over what the run already computed."""
    rel = ((release or {}).get(client_id) or {}) if isinstance(release, dict) else {}
    fr = ((funnel_results or {}).get(client_id) or {}) if isinstance(funnel_results, dict) else {}
    f = (fr.get("funnel") or {}) if isinstance(fr, dict) else {}
    g = golden if golden is not None else golden_for(client_id)

    cap = budget.daily_cap() or None
    spend = f.get("spend_tonight_usd")
    if g["error"]:
        gtxt = "golden ERROR (%s)" % g["error"]
    elif not g["available"]:
        gtxt = "golden: no suite for this client"
    elif g["failed"]:
        gtxt = "golden %d/%d, FAIL: %s" % (g["passed"], g["total"], "; ".join(n for n, _ in g["failed"]))
    else:
        gtxt = "golden %d/%d all green" % (g["passed"], g["total"])

    if rel.get("error"):
        rep = "next report: ERROR %s" % rel["error"]
    elif rel.get("locked"):
        rep = "next report %s: LOCKED, %s cards, reviewed and final" % (
            rel.get("target_date") or "?", _num(rel.get("shipped")))
    else:
        rep = "next report %s: %s/%s cards, lowest fit %s, pool covers %s days%s" % (
            rel.get("target_date") or "?", _num(rel.get("shipped")), _num(rel.get("target_size")),
            _num(rel.get("lowest_fit")), _num(rel.get("days_covered"), "%.1f"),
            "  <-- SHORT" if rel.get("short") else "")
    cost = "cost tonight $%s / ceiling $%s" % (_num(spend, "%.4f"), _num(cap, "%.2f"))

    # THE MIX IS YELLOW, NEVER RED (operator 2026-10-09). The university minimum changes the mix, never the bar:
    # if fewer than the minimum clear the fit floor, the gate fills the day with the best remaining by fit, so the
    # report is still 20 cards and still nothing under the floor. A thin mix is worth SEEING (it means university
    # discovery is behind) but it is not a fault: nothing is broken, nothing shipped that should not have, and it
    # must never trigger the alert email or cost the operator a dev session.
    yellow = None
    try:
        from factory.workers import release as _rel
        min_uni = _rel.min_universities(client_id)
    except Exception:
        min_uni = 0
    uni_txt = ""
    if min_uni:
        n = rel.get("universities")
        uni_txt = " | universities %s/%d" % (_num(n), min_uni)
        if n is not None and n < min_uni:
            yellow = "%s: universities %d/%d (mix below the minimum; filled to size by fit, nothing under the " \
                     "floor). University discovery is behind, not the report." % (client_id, n, min_uni)
            uni_txt += " YELLOW"

    lines = ["  %s: %s%s" % (client_id, rep, uni_txt), "    %s | %s" % (cost, gtxt)]
    if yellow:
        lines.append("    yellow: " + yellow.split(": ", 1)[1])
    return {"client_id": client_id, "golden": g, "lines": lines, "yellow": yellow,
            "red": bool(g["error"] or g["failed"] or rel.get("error"))}


def review(release=None, funnel_results=None, fatal=None, preflight_line=None, clients=None):
    """The block that opens the funnel email, plus whether a separate alert is owed.
    Returns {lines, alert_subject, alert_body, red}. Never raises: a broken review must not cost the email."""
    if clients is None:
        pool = set(SUITES) - {"2uplatam_staging"}          # staging is a clone, not a client to report on
        for src in (release, funnel_results):
            if isinstance(src, dict):
                pool |= {c for c in src.keys() if c != "2uplatam_staging"}
        clients = sorted(pool)

    status = "RUN DIED at %s: %s" % (fatal.get("step"), fatal.get("error")) if fatal else "run OK"
    lines = ["NIGHTLY REVIEW (read these lines; green = no dev session today)",
             "  status: " + status,
             "  providers: " + (preflight_line or "(no preflight line)")]
    reds, yellows, per_client = [], [], []
    for cid in clients:
        try:
            h = client_health(cid, release=release, funnel_results=funnel_results)
        except Exception as e:
            h = {"client_id": cid, "lines": ["  %s: review ERROR %s" % (cid, str(e)[:120])], "red": True,
                 "yellow": None,
                 "golden": {"failed": [], "error": str(e)[:120], "available": True, "total": 0, "passed": 0}}
        per_client.append(h)
        lines += h["lines"]
        if h["red"]:
            reds.append(h)
        if h.get("yellow"):
            yellows.append(h["yellow"])

    red = bool(fatal or reds)
    alert_subject = alert_body = None
    if red:
        bits = []
        if fatal:
            bits.append("RUN DIED at %s" % fatal.get("step"))
        for h in reds:
            g = h["golden"]
            if g.get("error"):
                bits.append("%s golden ERROR" % h["client_id"])
            elif g.get("failed"):
                bits.append("%s %d/%d" % (h["client_id"], g["passed"], g["total"]))
        alert_subject = "ALERT: " + ", ".join(bits or ["something is red"])
        detail = ["Something is red. Per PLAN principle 6, this is the day's only job.", "", "status: " + status, ""]
        for h in reds:
            detail += ["  " + l.strip() for l in h["lines"]]   # the lines already name the client
            for name, why in (h["golden"].get("failed") or []):
                detail.append("  FAIL %s: %s" % (name, why))
            if h["golden"].get("error"):
                detail.append("  golden could not run: %s" % h["golden"]["error"])
            detail.append("")
        alert_body = "\n".join(detail)
    return {"lines": lines, "alert_subject": alert_subject, "alert_body": alert_body, "red": red,
            "yellow": yellows}       # yellow is informational: it never sets `red` and never sends an alert


if __name__ == "__main__":
    import sys, json
    from factory.workers import release as _rel
    only = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
    # dry preview: assemble (no --apply) so the numbers are tonight's real ones without writing anything
    rel = _rel.assemble_all(only=only, apply=False)
    r = review(release=rel, funnel_results=None, fatal=None,
               preflight_line="(preview, preflight not run)", clients=[only] if only else None)
    print("\n".join(r["lines"]))
    if r["alert_subject"]:
        print("\n--- ALERT WOULD BE SENT ---\n" + r["alert_subject"] + "\n\n" + r["alert_body"])
