# factory/workers/client_status.py
# FD input (doctrine: the governor accounts for COMMERCIAL + ENGAGEMENT variables, not just dollars).
# Every client carries two axes the Financial Department must weigh before spending a credit on it:
#   1. commercial_status: 'paying' | 'demo' | 'internal'   (from clients.icp_config.commercial_status)
#   2. engagement: is the client actually ACTIONING the leads we hand them (working the cards)?
# An idle non-paying demo must never burn a paying client's scarce enrichment/verify budget. We don't delete
# such a client (the door stays open for a future sell) — FD just stops spending on it (spend_policy='paused').
#
# The actioning signal: leads.status advancing past 'none'/'new' (the client worked the card). Non-EJE clients
# send via their own channels, so this status transition is the one durable engagement signal we have for them.
from factory.packages import db

_IDLE_SET = {"none", "new", "", None}        # a card the client has NOT yet worked
_PAYING = {"paying"}


def _actioning(client_id):
    rows = db.select_all("leads", "client_id=eq.%s&select=status" % client_id)
    total = len(rows)
    actioned = sum(1 for r in rows if (r.get("status") or "").lower() not in _IDLE_SET)
    return {"app_leads": total, "actioned": actioned,
            "actioned_pct": round(100 * actioned / total, 1) if total else 0.0}


def status(client_id):
    crow = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
    icp = (crow[0].get("icp_config") or {}) if crow else {}
    commercial = (icp.get("commercial_status") or "demo").lower()
    policy = (icp.get("spend_policy") or ("full" if commercial in _PAYING else "limited")).lower()
    eng = _actioning(client_id)
    # recommendation: an idle demo (barely actioning) should be paused; a paying client is never auto-paused.
    idle_demo = commercial not in _PAYING and eng["app_leads"] >= 10 and eng["actioned"] <= 1
    recommend = "paused" if idle_demo else policy
    return {"client_id": client_id, "commercial_status": commercial, "spend_policy": policy,
            "paying": commercial in _PAYING, "engagement": eng,
            "idle_demo": idle_demo, "recommended_policy": recommend}


def all_status():
    return [status(c["id"]) for c in db.select("clients", "select=id")]


def spend_allowed(client_id):
    """FD hook: False when this client's policy is 'paused' (idle demo / operator-stopped). Paying clients always True."""
    if not client_id:
        return True
    s = status(client_id)
    if s["paying"]:
        return True
    return s["spend_policy"] != "paused"


if __name__ == "__main__":
    import json
    print(json.dumps(all_status(), indent=2))
