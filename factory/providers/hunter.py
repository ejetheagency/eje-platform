# factory/providers/hunter.py
# Hunter.io domain-search: find a NAMED decision-maker + email for a company domain. D4 Tier-2.
# Returns the best decisor candidate (named, decision title, highest confidence). Needs HUNTER_API_KEY.
import os, json, urllib.request, urllib.error, urllib.parse
from factory.packages import budget

PROVIDER = "hunter"
EST_USD = budget.price("hunter")
VERIFY_COST = budget.price("hunter_verify")
DECISION = ("founder", "co-founder", "ceo", "owner", "partner", "president", "director", "head", "chief",
            "gerente", "director general", "dueño", "socio", "fundador", "producer", "productor", "managing")


def _rank(e):
    pos = (e.get("position") or "").lower()
    named = bool(e.get("first_name") and e.get("last_name"))
    is_dm = any(k in pos for k in DECISION)
    return (is_dm, named, e.get("confidence") or 0)


def find_decisor(domain, client_id=None):
    key = os.environ.get("HUNTER_API_KEY")
    if not key:
        return {"ok": False, "reason": "no HUNTER_API_KEY"}
    ok, reason = budget.can_spend(client_id, PROVIDER, EST_USD)
    if not ok:
        return {"ok": False, "reason": reason}
    url = "https://api.hunter.io/v2/domain-search?domain=%s&limit=10&api_key=%s" % (domain, key)
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            data = json.loads(r.read().decode()).get("data", {})
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": "hunter %d: %s" % (e.code, e.read().decode()[:120])}
    budget.log_cost(PROVIDER, EST_USD, client_id=client_id, job_type="contact_find", estimated=True)
    emails = data.get("emails", [])
    named = [e for e in emails if e.get("first_name") and e.get("last_name")]
    pool = named or emails
    if not pool:
        return {"ok": True, "found": False}
    best = sorted(pool, key=_rank, reverse=True)[0]
    return {"ok": True, "found": True, "email": best.get("value"),
            "first_name": best.get("first_name"), "last_name": best.get("last_name"),
            "title": best.get("position"), "confidence": best.get("confidence")}


def verify(email, client_id=None):
    """Hunter Email Verifier. Returns {ok, status, result, score, raw}. Gated by can_spend, logged to cost_ledger.
    status in valid|invalid|accept_all|webmail|disposable|unknown; result in deliverable|undeliverable|risky."""
    key = os.environ.get("HUNTER_API_KEY")
    if not key or not email:
        return {"ok": False, "reason": "no HUNTER_API_KEY or email"}
    ok, reason = budget.can_spend(client_id, PROVIDER, VERIFY_COST)
    if not ok:
        return {"ok": False, "reason": reason}
    url = "https://api.hunter.io/v2/email-verifier?email=%s&api_key=%s" % (urllib.parse.quote(email), key)
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            d = json.loads(r.read().decode()).get("data", {})
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": "hunter verify %d: %s" % (e.code, e.read().decode()[:120])}
    budget.log_cost(PROVIDER, VERIFY_COST, client_id=client_id, job_type="email_verify", estimated=True)
    return {"ok": True, "status": d.get("status"), "result": d.get("result"), "score": d.get("score"), "raw": d}
