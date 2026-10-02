# factory/workers/scoring.py
# Scores a lead by data completeness + "why-now" signals + ICP fit, then routes out of SCORED:
#   below discard_floor -> DISCARDED;  else -> GATE_CHECK.
# (Tier-2 escalation for high-value-but-missing-contact leads activates once paid contact providers have keys.)
import os, json
from factory.packages import db, lead_state

_TH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "thresholds.json")


def _cfg():
    with open(_TH) as f:
        return json.load(f)


def _fit(company, client_id):
    rows = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
    icp = (rows[0].get("icp_config") or {}) if rows else {}
    hay = (str(icp.get("icp") or "") + " " + json.dumps(icp.get("signals") or "")).lower()
    comp = ((company.get("industry") or "") + " " + (company.get("name") or "")).lower()
    toks = [t for t in comp.replace("/", " ").split() if len(t) > 4]
    return any(t in hay for t in toks)


def score(company, contact, signals, fit_hit, cfg=None):
    cfg = cfg or _cfg()
    w = cfg["weights"]
    s = 0
    if contact and contact.get("email"):
        s += w["email"]
    if contact and contact.get("full_name"):
        s += w["decision_maker"]
    if company.get("brief"):
        s += w["brief"]
    if company.get("instagram"):
        s += w["instagram"]
    if company.get("linkedin"):
        s += w["linkedin"]
    if contact and contact.get("phone"):
        s += w["phone"]
    s += min(len(signals or []), 3) * w["signal"]
    if fit_hit:
        s += w["fit"]
    return min(s, 100)


def score_and_route(client_lead_id):
    cfg = _cfg()
    rows = db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,contact_id,state" % client_lead_id)
    if not rows:
        return {"skip": "no lead"}
    cl = rows[0]
    co = (db.select("companies", "id=eq.%s&select=name,industry,brief,instagram,linkedin" % cl["company_id"]) or [{}])[0]
    ct = {}
    if cl.get("contact_id"):
        ct = (db.select("contacts", "id=eq.%s&select=full_name,email,phone" % cl["contact_id"]) or [{}])[0]
    sigs = db.select("signals", "company_id=eq.%s&select=type" % cl["company_id"])
    sc = score(co, ct, sigs, _fit(co, cl["client_id"]), cfg)
    db.update("client_leads", "id=eq.%s" % cl["id"], {"score": sc})
    if cl["state"] != "SCORED":
        return {"score": sc, "route": "noop", "state": cl["state"]}
    if sc < cfg["discard_floor"]:
        lead_state.move(cl["id"], "DISCARDED")
        return {"score": sc, "route": "DISCARDED"}
    lead_state.move(cl["id"], "GATE_CHECK")
    return {"score": sc, "route": "GATE_CHECK"}
