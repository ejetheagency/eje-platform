# factory/providers/apollo.py
# Apollo people search by org domain -> named decision-maker. D4 Tier-2. Email is often masked on free plans
# (email_not_unlocked@...), so tier2 pairs a name from Apollo with a Prospeo email lookup. Needs APOLLO_API_KEY.
import os, json, urllib.request, urllib.error
from factory.packages import budget

PROVIDER = "apollo"
EST_USD = 0.02
SENIORITY = ["owner", "founder", "c_suite", "partner", "vp", "head", "director"]


def find_decisor(domain, client_id=None):
    key = os.environ.get("APOLLO_API_KEY")
    if not key:
        return {"ok": False, "reason": "no APOLLO_API_KEY"}
    ok, reason = budget.can_spend(client_id, PROVIDER, EST_USD)
    if not ok:
        return {"ok": False, "reason": reason}
    body = json.dumps({"q_organization_domains": domain, "person_seniorities": SENIORITY, "per_page": 5}).encode()
    req = urllib.request.Request("https://api.apollo.io/v1/mixed_people/search", data=body, method="POST",
                                 headers={"X-Api-Key": key, "Content-Type": "application/json", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            j = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": "apollo %d: %s" % (e.code, e.read().decode()[:120])}
    budget.log_cost(PROVIDER, EST_USD, client_id=client_id, job_type="contact_find", estimated=True)
    people = j.get("people") or []
    if not people:
        return {"ok": True, "found": False}
    p = people[0]
    return {"ok": True, "found": True, "first_name": p.get("first_name"), "last_name": p.get("last_name"),
            "title": p.get("title"), "email": p.get("email")}
