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


def quality_score(company, signals, fit_hit, cfg=None):
    # The COMPANY axis only (doctrine 0b): is this a target worth pursuing? Deliberately EXCLUDES contact
    # completeness (email/name/phone/channels) — those are the READY question, not the stay-in-the-circle question.
    # Used by the junk gate: a lead leaves via the "proven-useless" door ONLY when this is near zero (no ICP fit,
    # no why-now signal, no web presence, no brief) — i.e. we have no positive evidence it's good. A great company
    # with an un-mined contact scores HIGH here and must never be discarded for data we haven't mined yet.
    cfg = cfg or _cfg()
    w = cfg["weights"]
    q = 0
    if fit_hit:
        q += w["fit"]
    q += min(len(signals or []), 3) * w["signal"]
    if company.get("website") or company.get("domain"):
        q += 8  # real web presence = a positive quality signal (TSA enforces real-vs-fake per ICP downstream)
    # NOTE: brief is deliberately EXCLUDED — every enriched lead gets one, so it carries zero discriminating
    # signal (verified: 183/183 discarded 2uplatam leads had a brief). The real target-quality signals that VARY
    # are ICP fit, why-now signals, and web presence. Add stronger ones (dead-site detector, off-ICP classifier,
    # IG-follower count) here as they come online.
    return q


def score_and_route(client_lead_id):
    cfg = _cfg()
    rows = db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,contact_id,state" % client_lead_id)
    if not rows:
        return {"skip": "no lead"}
    cl = rows[0]
    co = (db.select("companies", "id=eq.%s&select=name,industry,brief,instagram,linkedin,domain,website" % cl["company_id"]) or [{}])[0]
    ct = {}
    if cl.get("contact_id"):
        ct = (db.select("contacts", "id=eq.%s&select=full_name,email,phone" % cl["contact_id"]) or [{}])[0]
    sigs = db.select("signals", "company_id=eq.%s&select=type" % cl["company_id"])
    sc = score(co, ct, sigs, _fit(co, cl["client_id"]), cfg)
    db.update("client_leads", "id=eq.%s" % cl["id"], {"score": sc})
    if cl["state"] != "SCORED":
        return {"score": sc, "route": "noop", "state": cl["state"]}
    # Routing is TWO axes (doctrine 0b): stay-vs-discard is the QUALITY question; the rest is the completeness
    # question. We decide stay-vs-discard FIRST, and cheaply, so junk never burns Tier-2 (paid) capacity.
    q = quality_score(co, sigs, _fit(co, cl["client_id"]), cfg)
    jf = cfg.get("junk_floor", 8)
    # (1) JUNK GATE — the sanctioned early leak. Only fires when there is NO positive evidence the company is good
    #     (q below floor) AND we don't already hold a usable contact (if we paid to find one, don't waste it).
    #     Records a cause. A high-quality company is unreachable here: fit/signal/brief/presence each clear the floor.
    if q < jf and not (ct.get("email") and ct.get("full_name")):
        lead_state.move(cl["id"], "DISCARDED",
                        reason="junk: quality=%d<%d (no fit/signal/presence/brief) — early-killed, no Tier-2 spend" % (q, jf))
        return {"score": sc, "quality": q, "route": "DISCARDED"}
    # quality-OK from here on: the lead STAYS in the circle. Route by what it needs next.
    # (2) already have a named decisor email -> straight to the gates.
    if ct.get("email") and ct.get("full_name"):
        lead_state.move(cl["id"], "GATE_CHECK")
        return {"score": sc, "quality": q, "route": "GATE_CHECK"}
    # (3) mineable (has a domain/site) + worth it (quality-OK) -> spend Tier-2 to find the contact.
    if co.get("domain") or co.get("website"):
        lead_state.move(cl["id"], "T2_ENRICHING")
        return {"score": sc, "quality": q, "route": "T2_ENRICHING"}
    # (4) quality-OK but no site to mine -> keep circulating via the gates (which PARK it for a later alt-channel
    #     pass); NEVER discard a good company for an un-mined contact.
    lead_state.move(cl["id"], "GATE_CHECK")
    return {"score": sc, "quality": q, "route": "GATE_CHECK"}
