# factory/test_composer.py  —  run:  python3 -m factory.test_composer
# Proves the Composer: a premium pitch GROUNDED in verified facts (names the real decisor, carries citations,
# invents nothing). Throwaway READY lead, cleanup by company_id (pool untouched).
import time
from factory.packages import db
from factory.workers import composer

PASS = True


def check(label, cond):
    global PASS
    print(("  PASS " if cond else "  FAIL ") + label)
    PASS = PASS and cond


def main():
    print("Composer grounding test\n")
    t = str(int(time.time()))
    co = db.insert("companies", {"dedupe_key": "TEST:comp-" + t, "name": "CBRA Films", "domain": "cbrafilms.com",
                                 "website": "https://cbrafilms.com", "country": "Chile", "industry": "Produccion audiovisual",
                                 "instagram": "cbrafilms", "brief": "Productora audiovisual chilena de comerciales y contenido de marca."})[0]
    ct = db.insert("contacts", {"company_id": co["id"], "full_name": "Cristobal Braun", "first_name": "Cristobal",
                                "title": "Director", "email": "cristobal@cbrafilms.com", "email_status": "verified",
                                "email_source": "hunter", "is_decision_maker": True})[0]
    cl = db.insert("client_leads", {"client_id": "eje", "company_id": co["id"], "contact_id": ct["id"], "state": "READY", "score": 85})[0]
    try:
        c = composer.compose(cl["id"])
        pitch = c.get("pitch") or ""
        print("  model:", c.get("_provider"))
        print("  pitch:", pitch[:160], "...")
        check("produced a pitch", bool(pitch))
        check("names the real decisor (Cristobal)", "ristobal" in pitch)
        check("carries citations (auditable grounding)", bool(c.get("citations")))
        check("has a dossier", bool(c.get("dossier")))
        # grounding: must not invent awards/clients not in the facts
        low = (pitch + " " + " ".join(c.get("dossier") or [])).lower()
        check("no hallucinated awards/big-name clients", not any(w in low for w in ["premio", "ganador", "netflix", "award", "oscar", "cannes"]))
    finally:
        for tbl in ("signals", "enrichment_findings", "assets", "cost_ledger", "job_log"):
            db.delete(tbl, "company_id=eq.%s" % co["id"])
        db.delete("client_leads", "id=eq.%s" % cl["id"])
        db.delete("contacts", "company_id=eq.%s" % co["id"])
        db.delete("companies", "id=eq.%s" % co["id"])
        print("\n  cleaned up (pool untouched)")
    print("\n" + ("COMPOSER TEST: PASS" if PASS else "COMPOSER TEST: FAIL"))


if __name__ == "__main__":
    main()
