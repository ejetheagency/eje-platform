# factory/workers/gates.py
# Quality Gates department (D5). Deterministic, free, data-presence checks (mirrors enrichment-gate.py's
# HARD blockers). Reads client_leads in GATE_CHECK, records pass/fail per gate + which fields are missing,
# and routes: all pass -> READY; fail (worth it, under max cycles) -> back to T1 with the missing list;
# fail at max cycles -> PARKED. LLM-for-ambiguous escalation (T3) is a later phase.
import json, os
from factory.packages import db, lead_state

MAX_CYCLES = 3
_TH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "thresholds.json")


def _allow_catch_all(client_id):
    # per-ICP override (clients.icp_config.allow_catch_all) else the thresholds default (false)
    rows = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
    icp = (rows[0].get("icp_config") or {}) if rows else {}
    if "allow_catch_all" in icp:
        return bool(icp["allow_catch_all"])
    try:
        return bool(json.load(open(_TH)).get("allow_catch_all_default", False))
    except Exception:
        return False


def _run_one(cl):
    co = db.select("companies", "id=eq.%s&select=name,website,domain,instagram,linkedin" % cl["company_id"])
    co = co[0] if co else {}
    ct = {}
    if cl.get("contact_id"):
        r = db.select("contacts", "id=eq.%s&select=full_name,email,email_status,email_verified_at,email_source,phone,instagram" % cl["contact_id"])
        ct = r[0] if r else {}

    allow_catch_all = _allow_catch_all(cl["client_id"])
    gates = [
        ("company_name",    bool(co.get("name"))),
        ("web_presence",    bool(co.get("website") or co.get("domain") or co.get("instagram") or co.get("linkedin"))),
        ("decision_maker",  bool(ct.get("full_name"))),
        ("email_deliverable", bool(ct.get("email")) and ct.get("email_status") not in ("invalid", "bounced")),
        # The email must be VERIFIED by the verify step (email_verified_at set). A catch_all/risky email passes
        # only if the ICP allows catch-all (config, default false). email_source alone no longer qualifies (STEP 1.5).
        ("email_verified",  bool(ct.get("email_verified_at")) or (ct.get("email_status") == "catch_all" and allow_catch_all)),
        ("contact_channel", bool(ct.get("email") or ct.get("phone") or ct.get("instagram") or co.get("instagram") or co.get("linkedin"))),
    ]
    missing = [name for name, ok in gates if not ok]

    for name, ok in gates:
        db.insert("gate_results", {
            "client_lead_id": cl["id"], "client_id": cl["client_id"], "gate": name,
            "passed": ok, "missing_fields": (missing if not ok else None),
        }, returning=False)

    if not missing:
        lead_state.move(cl["id"], "READY")
        return {"id": cl["id"], "result": "READY"}
    # Enrichment isn't incremental yet, so re-running the same pivots can't fill the gap. PARK the lead (retried
    # later when a new capability/strategy exists, per the Pivot Engine). Avoids the stuck-in-T1 loop.
    lead_state.move(cl["id"], "PARKED")
    return {"id": cl["id"], "result": "PARKED", "missing": missing}


def run_pending(client_id=None, limit=100):
    q = "state=eq.GATE_CHECK&select=id,client_id,company_id,contact_id,cycle_count&limit=%d" % limit
    if client_id:
        q += "&client_id=eq.%s" % client_id
    leads = db.select("client_leads", q)
    out = [_run_one(cl) for cl in leads]
    summary = {}
    for r in out:
        summary[r["result"]] = summary.get(r["result"], 0) + 1
    return {"processed": len(out), "summary": summary, "details": out}


if __name__ == "__main__":
    import json
    print(json.dumps(run_pending(), indent=2))
