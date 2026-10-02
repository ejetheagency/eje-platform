# factory/providers/stub.py
# A no-op provider adapter that models the real contract (can_spend -> do work -> write finding -> log cost)
# WITHOUT any external call. Used by the Phase-1 acceptance test. Real adapters (gemini, groq, serper,
# google_places, brandfetch, icypeas, hunter, apollo ...) follow this exact shape, one file each.
from factory.packages import budget, db

PROVIDER = "stub_enricher"
EST_USD = 0.001


def enrich(company_id, client_id):
    ok, reason = budget.can_spend(client_id, PROVIDER, EST_USD)
    if not ok:
        return {"ok": False, "reason": reason}
    # "do the work" -> write to the shared findings board
    db.insert("enrichment_findings", {
        "company_id": company_id, "field": "demo_field", "value": "hello-from-phase1",
        "source": PROVIDER, "confidence": 0.9, "cost_usd": EST_USD,
    }, returning=False)
    budget.log_cost(PROVIDER, EST_USD, client_id=client_id, company_id=company_id,
                    job_type="enrich_t1", estimated=True)
    return {"ok": True, "cost_usd": EST_USD}
