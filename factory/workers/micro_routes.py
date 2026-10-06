# factory/workers/micro_routes.py
# MICRO-ROUTES: the small, learned heuristics that turn a known decisor NAME into a reachable EMAIL for a small
# business. The system's reason-to-exist is to TEST lanes, measure per-ICP yield, and DOUBLE DOWN on winners
# (operator, 2026-10-06). Each lane is tiny + pluggable; each run is INSTRUMENTED (attempt -> cost_ledger as
# 'route:<lane>'; a success -> enrichment_finding source=<lane>) so route_yield ranks lanes PER ICP. We add lanes
# and let the DATA pick winners, lane by lane — not a 3-step chain anyone could write.
#
# COMPLIANCE (operator's locked 'no email guessing'): a lane must FIND a real email that is then VERIFIED
# (MillionVerifier) before attach. The verified-PATTERN lane is intentionally NOT included until the operator
# lifts the lock (it would live behind icp_config.allow_email_pattern).
import json, re, unicodedata
from factory.packages import db, budget, lead_state
from factory.providers import serper, verifier
from factory.workers.promote_candidates import _hygienic, ROLE

_EMAIL = re.compile(r"[a-z0-9][a-z0-9._%+-]*@[a-z0-9.-]+\.[a-z]{2,}", re.I)


def _log_attempt(lane, client_id):
    try:  # the yield DENOMINATOR: every lane run is an attempt, even when it finds nothing
        budget.log_cost("route:" + lane, 0.0, client_id=client_id, job_type="micro_route")
    except Exception:
        pass


def _log_find(company_id, email, lane):
    try:  # the yield NUMERATOR: route_yield counts findings by source -> per-lane yield emerges
        db.insert("enrichment_findings", {"company_id": company_id, "field": "email_candidates",
                  "value": json.dumps([email]), "source": lane, "pivot_name": lane}, returning=False)
    except Exception:
        pass


def _domain(company):
    w = company.get("domain") or company.get("website") or ""
    return w.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0] if w else ""


# ---- LANE: known name -> general web search -> email found in snippets (compliant real finding) ----
def lane_search_email(company, contact, domain, client_id):
    name = (contact or {}).get("full_name")
    if not name:
        return []
    scope = domain or company.get("name") or ""
    q = '"%s" %s (email OR correo OR contacto OR mail)' % (name, scope)
    sr = serper.search(q, num=7, client_id=client_id)
    org = sr.get("results") or sr.get("organic") or []
    text = " ".join(((x.get("title") or "") + " " + (x.get("snippet") or "")) for x in org)
    first = (name.split()[0] if name else "").lower()
    cands = list(dict.fromkeys(e.lower() for e in _EMAIL.findall(text) if _hygienic(e.lower())))
    cands.sort(key=lambda e: (0 if domain and domain in e else 1,
                              0 if len(first) > 2 and first in e.split("@")[0] else 1))
    return cands


# ---- LANE: verified-PATTERN (GATED behind icp_config.allow_email_pattern — operator's no-guess lock) ----
# Generate the likely personal formats for a small biz on its OWN domain, MV-verify each, and accept ONLY a CLEAN
# deliverable (status 'valid'). A catch-all ('accept_all') is REJECTED, never attached — we do not burn the client's
# sending reputation on a maybe-wrong box. Tier-3 (experimental), kept OUT of the main SLA.
def _ascii(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def _patterns(name, domain):
    parts = [re.sub(r"[^a-z]", "", _ascii(p).lower()) for p in (name or "").split()]
    parts = [p for p in parts if len(p) > 1]
    if not parts or not domain:
        return []
    first, last = parts[0], (parts[-1] if len(parts) > 1 else "")
    pats = [first]
    if last:
        pats += [first + "." + last, first[0] + last, first + last, last + "." + first]
    return list(dict.fromkeys("%s@%s" % (p, domain) for p in pats))


def lane_pattern_verify(company, contact, domain, client_id):
    pats = _patterns((contact or {}).get("full_name"), domain)
    catch = 0
    for e in pats:
        v = verifier.verify(e, client_id=client_id)
        if not v.get("ok"):
            continue
        st = (v.get("status") or "").lower()
        if st == "valid":            # CLEAN deliverable only -> accept
            return {"email": e, "catch_all_seen": catch}
        if st == "accept_all":       # catch-all -> REJECT (risk), but note it
            catch += 1
    return {"email": None, "catch_all_seen": catch}


def measure_pattern(client_id, max_leads=8):
    """EXPERIMENT (measure-only, attaches NOTHING, ships NOTHING): run the pattern lane on stuck named-no-email
    leads and report yield (clean deliverable found) + catch-all rate (the deliverability RISK), so the operator
    can decide whether to enable it live as a flagged tier-3 EXTRA. No address is burned by a silent MV check."""
    rows = db.select_all("client_leads", "client_id=eq.%s&state=in.(PARKED,T2_ENRICHING,SCORED,GATE_CHECK)&contact_id=not.is.null&select=id,company_id,contact_id" % client_id)
    checked = clean = catchall = nohit = 0
    ex = []
    for r in rows:
        if checked >= max_leads:
            break
        ct = (db.select("contacts", "id=eq.%s&select=full_name,email" % r["contact_id"]) or [{}])[0]
        if not ct.get("full_name") or ct.get("email"):
            continue
        co = (db.select("companies", "id=eq.%s&select=id,name,domain,website" % r["company_id"]) or [{}])[0]
        domain = _domain(co)
        if not domain:
            continue
        checked += 1
        res = lane_pattern_verify(co, ct, domain, client_id)
        if res["email"]:
            clean += 1
            if len(ex) < 6:
                ex.append((ct["full_name"], res["email"]))
        elif res["catch_all_seen"] > 0:
            catchall += 1
        else:
            nohit += 1
    return {"checked": checked, "clean_deliverable": clean, "catchall_domains": catchall,
            "no_hit": nohit, "examples": ex}


LANES = [("search_email", lane_search_email)]  # live lanes; pattern lane is gated/experimental (measure first)


def find_email(company, contact, client_id, icp):
    domain = _domain(company)
    for lane, fn in LANES:
        _log_attempt(lane, client_id)
        try:
            cands = fn(company, contact, domain, client_id) or []
        except Exception:
            cands = []
        for e in cands:
            v = verifier.verify(e, client_id=client_id)
            if v.get("ok") and ((v.get("result") or "").lower() == "deliverable" or (v.get("status") or "").lower() == "valid"):
                _log_find(company["id"], e, lane)
                return {"email": e, "lane": lane, "tier": 2 if e.split("@")[0] in ROLE else 1}
    return None


def sweep(client_id, max_leads=12, apply=False):
    """NAMED-decisor-but-no-email leads: actively FIND + verify + attach an email via the micro-route lanes.
    Instrumented per lane (route_yield shows which lane wins for THIS ICP). Bounded per run."""
    try:  # FD: don't spend lane effort on a paused (idle non-paying demo) client
        from factory.workers import client_status
        if not client_status.spend_allowed(client_id):
            return {"checked": 0, "found": 0, "by_lane": {}, "skipped": "spend paused"}
    except Exception:
        pass
    icp = ((db.select("clients", "id=eq.%s&select=icp_config" % client_id) or [{}])[0].get("icp_config") or {})
    out = {"checked": 0, "found": 0, "by_lane": {}}
    rows = db.select_all("client_leads",
                         "client_id=eq.%s&state=in.(PARKED,T2_ENRICHING,SCORED,GATE_CHECK)&contact_id=not.is.null&select=id,company_id,contact_id,state" % client_id)
    for r in rows:
        if out["checked"] >= max_leads:
            break
        ct = (db.select("contacts", "id=eq.%s&select=full_name,email" % r["contact_id"]) or [{}])[0]
        if not ct.get("full_name") or ct.get("email"):
            continue
        out["checked"] += 1
        if not apply:
            continue
        co = (db.select("companies", "id=eq.%s&select=id,name,domain,website" % r["company_id"]) or [{}])[0]
        res = find_email(co, ct, client_id, icp)
        if res:
            db.update("contacts", "id=eq.%s" % r["contact_id"],
                      {"email": res["email"], "email_status": "verified", "email_source": "micro_" + res["lane"]})
            try:
                if r["state"] in ("PARKED", "T2_ENRICHING", "SCORED"):
                    lead_state.move(r["id"], "GATE_CHECK", reason="email via micro-route %s (tier %d)" % (res["lane"], res["tier"]))
            except Exception:
                pass
            out["found"] += 1
            out["by_lane"][res["lane"]] = out["by_lane"].get(res["lane"], 0) + 1
    return out


if __name__ == "__main__":
    import sys
    print(sweep(sys.argv[1] if len(sys.argv) > 1 else "2uplatam", apply=("--apply" in sys.argv)))
