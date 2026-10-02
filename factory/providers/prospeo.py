# factory/providers/prospeo.py
# Prospeo email-finder: name + domain -> verified email. D4 Tier-2 (pairs with Apollo's name). Needs PROSPEO_API_KEY.
import os, json, urllib.request, urllib.error
from factory.packages import budget

PROVIDER = "prospeo"
EST_USD = 0.02


def find_email(first_name, last_name, domain, client_id=None):
    key = os.environ.get("PROSPEO_API_KEY")
    if not key:
        return {"ok": False, "reason": "no PROSPEO_API_KEY"}
    ok, reason = budget.can_spend(client_id, PROVIDER, EST_USD)
    if not ok:
        return {"ok": False, "reason": reason}
    body = json.dumps({"first_name": first_name, "last_name": last_name, "company": domain}).encode()
    req = urllib.request.Request("https://api.prospeo.io/email-finder", data=body, method="POST",
                                 headers={"X-KEY": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            j = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": "prospeo %d: %s" % (e.code, e.read().decode()[:120])}
    budget.log_cost(PROVIDER, EST_USD, client_id=client_id, job_type="contact_find", estimated=True)
    resp = j.get("response") or {}
    return {"ok": True, "email": resp.get("email"), "status": resp.get("email_status")}
