# factory/test_e2e.py  —  run:  python3 -m factory.test_e2e
# Capstone: a lead flows through the ENTIRE factory via the queue, autonomously.
# scheduler.tick() -> enqueue enrich_t1 -> runner drains -> enrich (site+gemini+logo) -> SCORED
#  -> enqueue gates -> GATE_CHECK -> gates pass -> READY. Isolated, cleans up.
import time
from factory.packages import db, queue
from factory.workers import scheduler, runner

PASS = True


def check(label, cond):
    global PASS
    print(("  PASS " if cond else "  FAIL ") + label)
    PASS = PASS and cond


def main():
    print("End-to-end factory test (queue-driven)\n")
    s = str(int(time.time()))
    co = db.insert("companies", {"dedupe_key": "TEST:e2e-" + s, "name": "Stripe", "domain": "stripe.com",
                                 "website": "https://stripe.com", "country": "US", "industry": "Payments"})[0]
    ct = db.insert("contacts", {"company_id": co["id"], "full_name": "Pat Collison",
                                "email": "pat@stripe.com", "email_status": "verified", "is_decision_maker": True})[0]
    cl = db.insert("client_leads", {"client_id": "eje", "company_id": co["id"], "contact_id": ct["id"],
                                    "state": "DISCOVERED", "score": 92})[0]
    print("seeded DISCOVERED lead", cl["id"][:8])
    try:
        t = scheduler.tick(client_id="eje")
        print("  scheduler.tick:", t)
        check("scheduler enqueued at least one enrich job", t["enqueued_enrich_t1"] >= 1)
        done = runner.drain()  # processes enrich_t1 (which chains a gates job) then gates
        print("  drained %d jobs:" % len(done), [(d["type"], d["ok"]) for d in done])

        final = db.select("client_leads", "id=eq.%s&select=state" % cl["id"])[0]["state"]
        findings = db.select("enrichment_findings", "company_id=eq.%s&select=field" % co["id"])
        gates_rows = db.select("gate_results", "client_lead_id=eq.%s&select=gate,passed" % cl["id"])
        ledger = db.select("cost_ledger", "company_id=eq.%s&select=provider" % co["id"])
        print("  final state:", final)
        print("  findings:", [f["field"] for f in findings])
        print("  gates:", [(g["gate"], g["passed"]) for g in gates_rows])
        check("lead reached READY via the queue", final == "READY")
        check("enrichment wrote findings", len(findings) >= 1)
        check("gates all passed", gates_rows and all(g["passed"] for g in gates_rows))
        check("costs logged", len(ledger) >= 1)
    finally:
        db.delete("gate_results", "client_lead_id=eq.%s" % cl["id"])
        db.delete("enrichment_findings", "company_id=eq.%s" % co["id"])
        db.delete("cost_ledger", "company_id=eq.%s" % co["id"])
        db.delete("assets", "company_id=eq.%s" % co["id"])
        db.delete("job_log", "company_id=eq.%s" % co["id"])
        db.delete("client_leads", "id=eq.%s" % cl["id"])
        db.delete("contacts", "company_id=eq.%s" % co["id"])
        db.delete("companies", "id=eq.%s" % co["id"])
        print("\n  cleaned up")
    print("\n" + ("E2E FACTORY TEST: PASS" if PASS else "E2E FACTORY TEST: FAIL"))


if __name__ == "__main__":
    main()
