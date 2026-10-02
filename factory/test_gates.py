# factory/test_gates.py  —  run:  python3 -m factory.test_gates
# Proves the gates worker routing: a complete lead -> READY; an incomplete lead -> re-enrich (back to T1).
# Synthetic, isolated, cleans up.
import time
from factory.packages import db, lead_state
from factory.workers import gates

PASS = True


def check(label, cond):
    global PASS
    print(("  PASS " if cond else "  FAIL ") + label)
    PASS = PASS and cond


def _mk(dedupe, name, with_contact):
    co = db.insert("companies", {"dedupe_key": dedupe, "name": name, "domain": name.lower() + ".test",
                                 "website": "https://" + name.lower() + ".test", "instagram": "ig_" + name.lower()})[0]
    contact_id = None
    if with_contact:
        contact_id = db.insert("contacts", {"company_id": co["id"], "full_name": "Jane Doe",
                                             "email": "jane@" + name.lower() + ".test", "email_status": "verified",
                                             "is_decision_maker": True})[0]["id"]
    cl = db.insert("client_leads", {"client_id": "eje", "company_id": co["id"], "contact_id": contact_id,
                                    "state": "SCORED", "score": 90})[0]
    lead_state.move(cl["id"], "GATE_CHECK")  # SCORED -> GATE_CHECK
    return co["id"], cl["id"]


def main():
    print("Gates routing test\n")
    s = str(int(time.time()))
    ids = []
    try:
        # complete lead -> should pass all gates -> READY
        co1, cl1 = _mk("TEST:gate-full-" + s, "FullCo", True); ids += [co1]
        r1 = gates._run_one(db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,contact_id,cycle_count" % cl1)[0])
        print("  full lead ->", r1)
        check("complete lead routed to READY", r1["result"] == "READY")

        # incomplete lead (no contact) -> should fail -> re-enrich
        co2, cl2 = _mk("TEST:gate-thin-" + s, "ThinCo", False); ids += [co2]
        r2 = gates._run_one(db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,contact_id,cycle_count" % cl2)[0])
        print("  thin lead ->", r2)
        check("incomplete lead routed to RE_ENRICH", r2["result"] == "RE_ENRICH")
        check("missing fields recorded", "decision_maker" in (r2.get("missing") or []))

        gr = db.select("gate_results", "client_id=eq.eje&client_lead_id=in.(%s,%s)&select=gate,passed" % (cl1, cl2))
        check("gate_results written", len(gr) >= 8)
    finally:
        for cid in ids:
            db.delete("gate_results", "client_lead_id=in.(select id from client_leads where company_id=eq.%s)" % cid) if False else None
            # delete children then company
            cls = db.select("client_leads", "company_id=eq.%s&select=id" % cid)
            for cl in cls:
                db.delete("gate_results", "client_lead_id=eq.%s" % cl["id"])
            db.delete("client_leads", "company_id=eq.%s" % cid)
            db.delete("contacts", "company_id=eq.%s" % cid)
            db.delete("companies", "id=eq.%s" % cid)
        print("\n  cleaned up")
    print("\n" + ("GATES TEST: PASS" if PASS else "GATES TEST: FAIL"))


if __name__ == "__main__":
    main()
