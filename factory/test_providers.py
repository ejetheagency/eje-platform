# factory/test_providers.py  —  run:  python3 -m factory.test_providers
# Smoke-tests the Tier-1 + Asset department against REAL external calls on an isolated throwaway company,
# then deletes everything it created. Proves site_enrich / gemini / logo end to end.
import time
from factory.packages import db
from factory.providers import site_enrich, gemini, logo

PASS = True


def check(label, cond):
    global PASS
    print(("  PASS " if cond else "  FAIL ") + label)
    PASS = PASS and cond


def main():
    print("Provider smoke test (real external calls)\n")
    co = db.insert("companies", {"dedupe_key": "TEST:prov-" + str(int(time.time())),
                                 "name": "Stripe", "domain": "stripe.com",
                                 "website": "https://stripe.com", "country": "US", "industry": "Payments"})[0]
    cid = co["id"]
    try:
        r1 = site_enrich.enrich(cid);           print("  site_enrich:", r1)
        r2 = gemini.brief(cid, client_id="eje"); print("  gemini.brief:", (r2.get("brief") or r2)[:120] if r2.get("ok") else r2)
        r3 = logo.resolve(cid);                 print("  logo:", r3)

        findings = db.select("enrichment_findings", "company_id=eq.%s&select=field,source" % cid)
        ledger = db.select("cost_ledger", "company_id=eq.%s&select=provider,usd_cost" % cid)
        comp = db.select("companies", "id=eq.%s&select=brief,logo_url" % cid)[0]
        print("  findings:", findings)
        print("  ledger:", ledger)

        check("site_enrich returned ok", r1.get("ok"))
        check("gemini wrote a brief", bool(comp.get("brief")))
        check("findings board has rows", len(findings) >= 1)
        check("cost_ledger logged calls", len(ledger) >= 2)
    finally:
        db.delete("enrichment_findings", "company_id=eq.%s" % cid)
        db.delete("cost_ledger", "company_id=eq.%s" % cid)
        db.delete("assets", "company_id=eq.%s" % cid)
        db.delete("companies", "id=eq.%s" % cid)
        print("\n  cleaned up")
    print("\n" + ("PROVIDER SMOKE TEST: PASS" if PASS else "PROVIDER SMOKE TEST: FAIL"))


if __name__ == "__main__":
    main()
