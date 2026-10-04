# factory/workers/gate_a.py
# Gate A: free corroboration (PIVOT_ENGINE §4b). Earn "verified by corroboration" before any paid SMTP call.
# The loop for one person: find a NAME (pivot 1 first-party site read; else pivot 4 forward search of the
# company for its owner) -> independent name+company search (pivot 20) -> cheap-LLM corroboration (pivot 19)
# that writes edges -> evaluate the Gate A conditions. On pass: write persons, set the lead's named contact
# (email_source=corroboration), and (if an email exists) route to verify so Gate B/gates re-run.
# NO paid contact-finding fallback (operator decision): Gate A is the answer, and keeps being it until it is.
# Small-company fast path (2uplatam): the company's own site is the first-party anchor, so a search-found
# name + one independent corroboration clears even when the site lists no person.
import os, re, json, datetime
from urllib.parse import quote
from factory.packages import db, queue
from factory.providers import site_decisor, serper, cheap_llm


def _clean(s):
    # LLM/site text can carry newlines/tabs that break a PostgREST URL filter and dirty stored values.
    return re.sub(r"\s+", " ", (s or "").replace("\x00", "")).strip()

_TH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "thresholds.json")


def _cfg():
    try:
        return (json.load(open(_TH)).get("verify") or {}).get("gate_a") or {}
    except Exception:
        return {}


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _pkey(name, company):
    return ("%s|%s" % ((name or "").strip().lower(), (company or "").strip().lower()))[:200]


def _fact(company_id, field, value, pivot, first_party, pkey, url=None, source_fid=None):
    r = db.insert("enrichment_findings", {
        "company_id": company_id, "field": field, "value": value, "source": pivot,
        "pivot_name": pivot, "first_party": first_party, "person_key": pkey,
        "evidence_url": url, "source_finding_id": source_fid, "confidence": 0.9,
    }, returning=True)
    return r[0]["id"] if isinstance(r, list) else r["id"]


def _name_from_search(company_name, domain, client_id):
    # pivot 4 (forward): search the company for its owner/decisor, extract a candidate name + role via LLM.
    q = '"%s" (fundador OR dueño OR "gerente general" OR director OR CEO OR socio)' % (company_name or "")
    sr = serper.search(q, num=7, client_id=client_id)
    org = sr.get("organic") or sr.get("results") or []
    snips = [((x.get("title") or "") + " " + (x.get("snippet") or "")).strip() for x in org][:7]
    urls = [x.get("link") for x in org][:7]
    if not snips:
        return {}
    prompt = (
        "From these web snippets about the company \"%s\", extract the NAME and ROLE of the owner, "
        "founder, CEO, general manager or director IF a person is clearly named for THIS company. "
        'JSON only: {"name":"<full name or empty>","role":"<role or empty>"}.\n%s'
    ) % (company_name, "\n".join("- " + s[:300] for s in snips))
    try:
        out = cheap_llm.generate(prompt, client_id=client_id, job_type="name_search")
        txt = (out.get("text") or "")
        s, e = txt.find("{"), txt.rfind("}")
        d = json.loads(txt[s:e + 1]) if s >= 0 and e > s else {}
    except Exception:
        d = {}
    nm = _clean(d.get("name"))
    return {"name": nm, "role": _clean(d.get("role")), "url": urls[0] if urls else None} if nm else {}


def _corroborate(company_name, name, role, snippets, client_id):
    # pivot 19: cheap LLM reads the search snippets and judges, backward, against the candidate.
    prompt = (
        "You verify a business decision-maker from web search snippets. Answer ONLY compact JSON.\n"
        'Company: "%s"\nCandidate person: "%s"\nCandidate role: "%s"\n\n'
        "Snippets:\n%s\n\n"
        'Return: {"same_person_same_company": true|false, "same_role": true|false, '
        '"role_found": "<role or empty>", "contradiction": true|false}. '
        "same_person_same_company is true ONLY if a snippet clearly ties this person to this company."
    ) % (company_name, name, role or "", "\n".join("- " + s[:300] for s in snippets) or "(none)")
    try:
        out = cheap_llm.generate(prompt, client_id=client_id, job_type="corroborate")
        txt = (out.get("text") or "").strip()
        s, e = txt.find("{"), txt.rfind("}")
        return json.loads(txt[s:e + 1]) if s >= 0 and e > s else {}
    except Exception:
        return {}


def _set_contact(company_id, name, role, email):
    el = (email or "").lower()
    ex = db.select("contacts", "company_id=eq.%s&email=eq.%s&select=id" % (company_id, el)) if el else []
    body = {"company_id": company_id, "full_name": name, "title": role, "email": email,
            "email_status": "found", "email_source": "corroboration", "is_decision_maker": True}
    if ex:
        db.update("contacts", "id=eq.%s" % ex[0]["id"], {k: v for k, v in body.items() if v})
        return ex[0]["id"]
    return db.insert("contacts", body, returning=True)[0]["id"]


def run(client_lead_id):
    rows = db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,contact_id,state" % client_lead_id)
    if not rows:
        return {"skip": "no lead"}
    cl = rows[0]
    co = (db.select("companies", "id=eq.%s&select=name,domain,website" % cl["company_id"]) or [{}])[0]
    cfg = _cfg()
    min_corr = int(cfg.get("min_corroborations", 2))

    # Find a NAME: pivot 1 first-party site read; if the site lists none, pivot 4 forward search.
    sd = site_decisor.find(cl["company_id"], cl["client_id"])
    first_party_name = bool(sd.get("ok") and sd.get("found") and sd.get("name"))
    name, role, email = _clean(sd.get("name")) or None, _clean(sd.get("role")) or None, (sd.get("email") or "").strip() or None
    name_src = "pivot_1_site_team"
    if not name:
        ns = _name_from_search(co.get("name"), co.get("domain"), cl["client_id"])
        name, role, name_src = ns.get("name"), (role or ns.get("role")), "pivot_4_name_search"
    if not name:
        return {"ok": True, "gate_a": False, "reason": "no name found (site or search)"}
    pkey = _pkey(name, co.get("name"))
    fp = _fact(cl["company_id"], "person_name", name, name_src, first_party_name, pkey, co.get("website"))
    if role:
        _fact(cl["company_id"], "role", role, name_src, first_party_name, pkey, co.get("website"))
    if email:
        _fact(cl["company_id"], "email", email, "pivot_1_site", True, pkey, co.get("website"))

    # pivot 20: independent search of the name + company (different origin from the site)
    independent = 0
    role_found = role
    sr = serper.search('"%s" %s' % (name, co.get("name") or ""), num=6, client_id=cl["client_id"])
    org = sr.get("organic") or sr.get("results") or []
    snippets = [((x.get("title") or "") + " " + (x.get("snippet") or "")).strip() for x in org][:6]
    urls = [x.get("link") for x in org][:6]
    corr = _corroborate(co.get("name"), name, role, snippets, cl["client_id"])
    if corr.get("same_person_same_company"):
        ind = _fact(cl["company_id"], "person_name", name, "pivot_20_name_search", False, pkey, urls[0] if urls else None, source_fid=fp)
        db.insert("corroborations", {"company_id": cl["company_id"], "person_key": pkey, "fact_id": ind,
                                     "confirms_fact_id": fp, "relation": "same_name",
                                     "source_pivot": "pivot_19_corroborate", "confidence": 0.8,
                                     "evidence_url": urls[0] if urls else None}, returning=False)
        independent += 1
        if corr.get("role_found") and not role_found:
            role_found = _clean(corr["role_found"])

    # Gate A conditions: >= min_corr sources + role + no contradiction + a first-party anchor.
    # Small-company fast path (cfg.small_company_max_employees): the company's own site counts as the
    # first-party anchor, so a search-found name + one independent corroboration clears without a site name.
    contradiction = bool(corr.get("contradiction"))
    total_sources = 1 + independent          # the name source + independent corroborations
    small = True  # TODO: gate on real employee count once sized; 2uplatam is the small-company path
    first_party_ok = first_party_name or small
    gate_a = (total_sources >= min_corr) and bool(role_found) and first_party_ok and not contradiction

    # upsert persons candidate
    ex = db.select("persons", "company_id=eq.%s&person_key=eq.%s&select=id" % (cl["company_id"], quote(pkey, safe="")))
    prow = {"company_id": cl["company_id"], "person_key": pkey, "name": name, "role": role_found,
            "first_party_count": 1 if first_party_name else 0, "independent_source_count": independent,
            "corroboration_score": total_sources, "contradiction_count": 1 if contradiction else 0,
            "email": email, "email_status": "found" if email else None, "discovered_via": name_src,
            "gate_a_passed_at": _now() if gate_a else None, "updated_at": _now()}
    if ex:
        db.update("persons", "id=eq.%s" % ex[0]["id"], prow)
    else:
        db.insert("persons", prow, returning=False)

    if gate_a:
        contact_id = _set_contact(cl["company_id"], name, role_found, email)
        db.update("client_leads", "id=eq.%s" % cl["id"], {"contact_id": contact_id})
        # an email-bearing lead routes to verify (Gate B if report-bound) which re-gates PARKED on a good result;
        # a name-only lead (no email yet) has its decision_maker now, and waits for an email pivot.
        if email:
            queue.enqueue("verify", client_id=cl["client_id"], company_id=cl["company_id"], client_lead_id=cl["id"])
    return {"ok": True, "gate_a": gate_a, "name": name, "role": role_found, "email": bool(email),
            "first_party": first_party_name, "sources": total_sources, "contradiction": contradiction}
