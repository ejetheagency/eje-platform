# factory/workers/gates.py
# Quality Gates department (D5). Deterministic, free, data-presence checks (mirrors enrichment-gate.py's
# HARD blockers). Reads client_leads in GATE_CHECK, records pass/fail per gate + which fields are missing,
# and routes: all pass -> READY; fail (worth it, under max cycles) -> back to T1 with the missing list;
# fail at max cycles -> PARKED. LLM-for-ambiguous escalation (T3) is a later phase.
import json, os
from factory.packages import db, lead_state
from factory.workers import tsa

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


def _soft_ok(cl, ct):
    # VERIFIED_SOFT (PIVOT_ENGINE 4b): a catch-all email is acceptable when its identity is CORROBORATED,
    # either by Gate A (a persons row with gate_a_passed_at) or because a human/operator published it for this
    # person (operator_seed / corroboration source). Such a lead is usable in reports WITH a soft flag, so we
    # do not hold Codex-style catch-all contacts on deliverability alone.
    if (ct.get("email_source") or "") in ("operator_seed", "corroboration"):
        return True
    rows = db.select("persons", "company_id=eq.%s&gate_a_passed_at=not.is.null&select=id&limit=1" % cl["company_id"])
    return bool(rows)


def _channels_cfg(client_id):
    # icp_config.channels = {min: 2, required: ["instagram"]}. Default: 2 channels minimum + Instagram required
    # (the EJE/productora standard: no IG, never ships). An ICP where IG does not apply sets required: [].
    rows = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
    ch = ((rows[0].get("icp_config") or {}) if rows else {}).get("channels") or {}
    return int(ch.get("min", 2)), list(ch.get("required", ["instagram"]))


def _run_one(cl):
    co = db.select("companies", "id=eq.%s&select=name,website,domain,instagram,linkedin" % cl["company_id"])
    co = co[0] if co else {}
    ct = {}
    if cl.get("contact_id"):
        r = db.select("contacts", "id=eq.%s&select=full_name,email,email_status,email_verified_at,email_source,phone,instagram,linkedin_url" % cl["contact_id"])
        ct = r[0] if r else {}

    allow_catch_all = _allow_catch_all(cl["client_id"])
    soft = ct.get("email_status") in ("catch_all", "catch_all_suspected") and (allow_catch_all or _soft_ok(cl, ct))
    # channel bar: count the distinct outreach channels present (website is NOT a channel).
    chans = set()
    if ct.get("email") and ct.get("email_status") not in ("invalid", "bounced"):
        chans.add("email")
    if ct.get("phone"):
        chans.add("phone")
    if ct.get("instagram") or co.get("instagram"):
        chans.add("instagram")
    if ct.get("linkedin_url") or co.get("linkedin"):
        chans.add("linkedin")
    min_ch, req_ch = _channels_cfg(cl["client_id"])
    gates = [
        ("company_name",    bool(co.get("name"))),
        ("real_website",    tsa.real_website(co.get("website") or "") or tsa.real_domain(co.get("domain") or "")),
        ("decision_maker",  bool(ct.get("full_name"))),
        ("email_deliverable", bool(ct.get("email")) and ct.get("email_status") not in ("invalid", "bounced")),
        # VERIFIED (email_verified_at) or VERIFIED_SOFT (catch-all whose identity is corroborated) or ICP allows catch-all.
        ("email_verified",  bool(ct.get("email_verified_at")) or soft),
        # Channel bar: >= min distinct channels AND every required channel present (default: 2 + Instagram).
        ("channels",        len(chans) >= min_ch and all(r in chans for r in req_ch)),
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
