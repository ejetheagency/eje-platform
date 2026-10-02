# factory/providers/millionverifier.py
# MillionVerifier SMTP email verifier (STEP 1.5, the primary verifier). verify(email) returns a NORMALIZED
# {ok, status, result, score, raw, credits_remaining} in the same status/result vocab Hunter uses, so the
# verify worker's mapping is unchanged. Gated by can_spend, priced millionverifier_verify, logged to
# cost_ledger. Records the vendor's remaining credits in provider_accounts on every call.
import os, json, urllib.request, urllib.error, urllib.parse
from factory.packages import budget, db

PROVIDER = "millionverifier"
VERIFY_COST = budget.price("millionverifier_verify")

# MillionVerifier `result` -> (status, result) in the common vocab the verify worker maps on.
_MAP = {
    "ok":         ("valid", "deliverable"),
    "catch_all":  ("accept_all", "risky"),
    "disposable": ("disposable", "undeliverable"),
    "invalid":    ("invalid", "undeliverable"),
    "unknown":    ("unknown", ""),
    "error":      ("unknown", ""),
}


def _store_credits(n):
    if n is None:
        return
    try:
        db.update("provider_accounts", "provider=eq.%s" % PROVIDER, {"credits_remaining": n})
    except Exception:
        pass


def quota_remaining():
    rows = db.select("provider_accounts", "provider=eq.%s&select=credits_remaining" % PROVIDER)
    return rows[0]["credits_remaining"] if rows else None


def verify(email, client_id=None):
    key = os.environ.get("MILLIONVERIFIER_API_KEY")
    if not key or not email:
        return {"ok": False, "reason": "no MILLIONVERIFIER_API_KEY or email"}
    ok, reason = budget.can_spend(client_id, PROVIDER, VERIFY_COST)
    if not ok:
        return {"ok": False, "reason": reason}
    url = "https://api.millionverifier.com/api/v3/?api=%s&email=%s&timeout=15" % (key, urllib.parse.quote(email))
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": "millionverifier %d: %s" % (e.code, e.read().decode()[:120])}
    credits = d.get("credits")
    _store_credits(credits)
    err = d.get("error")
    if err and str(err).strip():
        q = {"ok": False, "reason": "millionverifier error: %s" % err, "credits_remaining": credits}
        if "credit" in str(err).lower():
            q["quota_exhausted"] = True
        return q
    budget.log_cost(PROVIDER, VERIFY_COST, client_id=client_id, job_type="email_verify", estimated=True)
    mv = (d.get("result") or "").lower()
    status, result = _MAP.get(mv, ("unknown", ""))
    return {"ok": True, "status": status, "result": result, "score": d.get("resultcode"),
            "raw": d, "credits_remaining": credits}
