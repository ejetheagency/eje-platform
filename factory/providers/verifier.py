# factory/providers/verifier.py
# Verifier interface (STEP 1.5 design A). verify(email) tries SMTP-verifier vendors in the order of
# config verify.provider_order, skipping any vendor we already know is out of credits. Each adapter
# normalizes to the same {ok, status, result, score, raw} vocab and records its remaining credits in
# provider_accounts, so the ledger is no longer blind to the real vendor wall. Hunter is secondary:
# only reached if MillionVerifier is unavailable, and only works when its own quota is left.
import os, json
from factory.providers import millionverifier, hunter

_TH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "thresholds.json")
ADAPTERS = {"millionverifier": millionverifier, "hunter": hunter}


def _order():
    try:
        v = (json.load(open(_TH)).get("verify") or {})
        return v.get("provider_order") or ["millionverifier", "hunter"]
    except Exception:
        return ["millionverifier", "hunter"]


def verify(email, client_id=None):
    last = None
    for name in _order():
        ad = ADAPTERS.get(name)
        if not ad:
            continue
        q = getattr(ad, "quota_remaining", lambda: None)()  # skip vendors known to be out of credits
        if q is not None and q <= 0:
            last = "%s quota exhausted" % name
            continue
        r = ad.verify(email, client_id=client_id)
        if r.get("ok"):
            r["provider"] = name
            return r
        last = r.get("reason")
    return {"ok": False, "reason": last or "no verifier available"}
