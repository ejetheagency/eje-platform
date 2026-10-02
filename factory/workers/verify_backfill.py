# factory/workers/verify_backfill.py
# Backfill: verify existing lead-linked contacts' emails through the factory (Gate B). Enqueues "verify"
# jobs, 2upLatam-first by lead score, bounded by the verifier credit reserve so the pool-floor keeps some.
# Credits come from provider_accounts (nothing hardcoded). Logs a budget-stop row in job_log (status=done,
# not an error) when it caps. Only lead-linked contacts are enqueued (only those can reach READY via gates).
import json, os
from factory.packages import db, queue

_TH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "thresholds.json")
_RESOLVED = ("catch_all", "catch_all_suspected", "bounced")


def _reserve():
    try:
        return int((json.load(open(_TH)).get("verify") or {}).get("reserve_credits", 50))
    except Exception:
        return 50


def _usable_credits():
    pa = db.select("provider_accounts", "provider=eq.millionverifier&select=credits_remaining")
    return float(pa[0]["credits_remaining"]) if pa and pa[0].get("credits_remaining") is not None else 0.0


def _candidates():
    # contacts with an email that is NOT yet resolved (needs verification)
    cts = db.select_all("contacts", "email=not.is.null&select=id,email,email_status,email_verified_at")
    need = set()
    for c in cts:
        if (c.get("email") or "").strip() and not c.get("email_verified_at") and (c.get("email_status") not in _RESOLVED):
            need.add(c["id"])
    # lead-linked leads whose chosen contact needs verification (only these can reach READY via gates)
    leads = db.select_all("client_leads", "contact_id=not.is.null&select=id,client_id,company_id,contact_id,score")
    cand = [l for l in leads if l.get("contact_id") in need]
    # 2upLatam first, then highest lead score first
    cand.sort(key=lambda l: (0 if l["client_id"] == "2uplatam" else 1, -(l.get("score") or 0)))
    return cand


def enqueue_backfill(client_id=None):
    reserve = _reserve()
    credits = _usable_credits()
    budget_n = max(0, int(credits) - reserve)
    cand = _candidates()
    if client_id:
        cand = [l for l in cand if l["client_id"] == client_id]
    to_run = cand[:budget_n]
    for l in to_run:
        queue.enqueue("verify", client_id=l["client_id"], company_id=l["company_id"], client_lead_id=l["id"])
    capped = len(cand) > len(to_run)
    if capped:
        db.insert("job_log", {"type": "verify_backfill_stop", "status": "done",
                              "error": "budget_stop: enqueued %d of %d needed; reserved %d credits for pool-floor"
                                       % (len(to_run), len(cand), reserve)}, returning=False)
    by_client = {}
    for l in to_run:
        by_client[l["client_id"]] = by_client.get(l["client_id"], 0) + 1
    return {"credits": int(credits), "reserve": reserve, "budget": budget_n,
            "candidates": len(cand), "enqueued": len(to_run), "capped_budget_stop": capped,
            "by_client": by_client, "enqueued_2uplatam": by_client.get("2uplatam", 0)}


if __name__ == "__main__":
    print(json.dumps(enqueue_backfill(), indent=2))
