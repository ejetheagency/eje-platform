# factory/test_phase1.py
# Phase-1 acceptance test (ENRICHMENT_MASTER_PLAN §12): "a test job moves a lead through states and logs a cost."
# Run from the repo root:  python3 -m factory.test_phase1
# Creates a throwaway company + client_lead, moves it DISCOVERED -> DELIVERED through the state machine,
# runs the stub provider via can_spend() + logs a cost, verifies, checks an invalid transition is rejected,
# then DELETES everything it created. Uses the service key (bypasses RLS).
import time
from factory.packages import db, lead_state, budget
from factory.providers import stub

CLIENT = "eje"
stamp = str(int(time.time()))
PASS = True


def check(label, cond):
    global PASS
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        PASS = False


def main():
    print("Phase-1 acceptance test\n")
    co = db.insert("companies", {"dedupe_key": "TEST:phase1-" + stamp, "name": "Phase1 Test Co", "country": "CL"})[0]
    cl = db.insert("client_leads", {"client_id": CLIENT, "company_id": co["id"], "state": "DISCOVERED", "score": 90})[0]
    print("created company=%s client_lead=%s state=%s\n" % (co["id"][:8], cl["id"][:8], cl["state"]))

    try:
        # 1. budget gate allows a near-free call
        ok, reason = budget.can_spend(CLIENT, stub.PROVIDER, stub.EST_USD)
        check("can_spend() allows the enrichment call (%s)" % reason, ok)

        # 2. walk the lifecycle
        lead_state.move(cl["id"], "T1_ENRICHING");  print("  -> T1_ENRICHING")
        r = stub.enrich(co["id"], CLIENT);          print("  enrich:", r)
        check("provider enriched + returned ok", r.get("ok"))
        for to in ["SCORED", "GATE_CHECK", "READY", "DELIVERED"]:
            lead_state.move(cl["id"], to);          print("  ->", to)
        final = db.select("client_leads", "id=eq.%s&select=state,delivered_at" % cl["id"])[0]
        check("final state is DELIVERED", final["state"] == "DELIVERED")
        check("delivered_at stamped", bool(final.get("delivered_at")))

        # 3. the cost was logged + a finding was written
        ledger = db.select("cost_ledger", "company_id=eq.%s&select=provider,usd_cost,job_type" % co["id"])
        findings = db.select("enrichment_findings", "company_id=eq.%s&select=field,source" % co["id"])
        print("  ledger:", ledger)
        print("  findings:", findings)
        check("a cost was logged to cost_ledger", len(ledger) == 1 and float(ledger[0]["usd_cost"]) > 0)
        check("a finding was written to the board", len(findings) == 1)

        # 4. invalid transition is rejected
        try:
            lead_state.move(cl["id"], "DISCOVERED")  # DELIVERED -> DISCOVERED is illegal
            check("invalid transition rejected", False)
        except lead_state.InvalidTransition:
            check("invalid transition rejected", True)
    finally:
        # 5. cleanup (always)
        db.delete("cost_ledger", "company_id=eq.%s" % co["id"])
        db.delete("enrichment_findings", "company_id=eq.%s" % co["id"])
        db.delete("client_leads", "id=eq.%s" % cl["id"])
        db.delete("companies", "id=eq.%s" % co["id"])
        print("\n  cleaned up test rows")

    print("\n" + ("PHASE 1 ACCEPTANCE: PASS" if PASS else "PHASE 1 ACCEPTANCE: FAIL"))
    return 0 if PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
