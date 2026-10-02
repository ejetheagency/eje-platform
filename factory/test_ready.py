# factory/test_ready.py  —  run:  python3 -m factory.test_ready
# Live full cycle to READY (needs HUNTER_API_KEY + GEMINI). Uses a THROWAWAY company with a real domain so
# Hunter finds a real decisor. Proves: DISCOVERED -> enrich -> Tier-2 (contact-find) -> gates -> READY.
# Cleanup deletes EVERYTHING by the throwaway company_id (the pool is never touched).
import time
from factory.packages import db, queue
from factory.workers import runner

PASS = True


def check(label, cond):
    global PASS
    print(("  PASS " if cond else "  FAIL ") + label)
    PASS = PASS and cond


def main():
    print("Live READY cycle\n")
    co = db.insert("companies", {"dedupe_key": "TEST:ready-" + str(int(time.time())), "name": "CBRA Films",
                                 "domain": "cbrafilms.com", "website": "https://cbrafilms.com",
                                 "country": "CL", "industry": "Film production"})[0]
    cl = db.insert("client_leads", {"client_id": "eje", "company_id": co["id"], "state": "DISCOVERED", "score": 0})[0]
    print("seeded DISCOVERED lead for cbrafilms.com\n")
    try:
        queue.enqueue("enrich_t1", client_id="eje", company_id=co["id"], client_lead_id=cl["id"])
        done = runner.drain()
        print("  pipeline:", [(d["type"], d["ok"]) for d in done])
        final = db.select("client_leads", "id=eq.%s&select=state,contact_id,score" % cl["id"])[0]
        contact = None
        if final.get("contact_id"):
            contact = (db.select("contacts", "id=eq.%s&select=full_name,title,email,email_source" % final["contact_id"]) or [None])[0]
        print("  final state:", final["state"], "| score:", final["score"])
        print("  decisor found:", contact)
        gates = db.select("gate_results", "client_lead_id=eq.%s&select=gate,passed" % cl["id"])
        check("pipeline ran enrich -> tier2 -> gates", {d["type"] for d in done} >= {"enrich_t1", "tier2", "gates"})
        check("lead reached READY", final["state"] == "READY")
        check("named decisor + email found via Tier-2", bool(contact and contact.get("email") and contact.get("full_name")))
        check("all gates passed", gates and all(g["passed"] for g in gates))
    finally:
        for tbl in ("gate_results",):
            db.delete(tbl, "client_lead_id=eq.%s" % cl["id"])
        db.delete("client_leads", "id=eq.%s" % cl["id"])
        for tbl in ("contacts", "enrichment_findings", "signals", "assets", "cost_ledger", "job_log"):
            db.delete(tbl, "company_id=eq.%s" % co["id"])
        db.delete("companies", "id=eq.%s" % co["id"])
        print("\n  cleaned up (by company_id; pool untouched)")
    print("\n" + ("READY CYCLE: PASS" if PASS else "READY CYCLE: FAIL"))


if __name__ == "__main__":
    main()
