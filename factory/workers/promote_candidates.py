# factory/workers/promote_candidates.py
# Fix for the "found-but-dropped" email leak (Library finding #1): the factory scrapes REAL addresses into
# enrichment_findings (field=email_candidates) but never verifies/attaches them, so leads park "no email" while
# their email sits on file (366 found vs 50 promoted). This verifies a lead's own found candidates (MillionVerifier,
# night_credit_cap-gated) and attaches the first DELIVERABLE one to the NAMED decisor -> the lead reaches READY.
# Honest: real found addresses, verified before use, NO guessing. Requires a decisor (contact_id) so we never ship
# an email without a person. Prefers a candidate whose localpart matches the decisor's name; else a role inbox
# (info/contacto/hola...), which the ICP doctrine allows for the email field.
import os, json, re, datetime
from factory.packages import db, queue, lead_state
from factory.providers import verifier

ROLE = {"info", "contacto", "contact", "hola", "hello", "ventas", "sales", "admin", "soporte", "support",
        "gerencia", "administracion", "recepcion", "contacto1", "comercial"}

# Candidate hygiene: never spend a (scarce, capped) verify credit on a malformed or placeholder address.
# Scrapes pick up template junk like "usuario@dominio.com" / "your@email.com" and broken tokens; filter them out.
_EMAIL_RE = re.compile(r"^[a-z0-9][a-z0-9._%+-]*@([a-z0-9](-?[a-z0-9]+)*\.)+[a-z]{2,}$")
_PLACEHOLDER_DOMAINS = {"dominio.com", "domain.com", "example.com", "ejemplo.com", "email.com", "correo.com",
                        "test.com", "mail.com", "yourdomain.com", "sudominio.com", "tudominio.com", "empresa.com"}
_PLACEHOLDER_LOCAL = {"usuario", "user", "nombre", "name", "tucorreo", "tuemail", "ejemplo", "example", "test",
                      "email", "correo", "your", "sample"}


def _hygienic(e):
    if not _EMAIL_RE.match(e):
        return False
    lp, dom = e.split("@", 1)
    return dom not in _PLACEHOLDER_DOMAINS and lp not in _PLACEHOLDER_LOCAL


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _ncap_reached(reserve=0):
    # Recovery (promoting an ALREADY-FOUND email) is higher-ROI than verifying a brand-new lead, so it gets a
    # reserved credit slice the general new-lead drain can't touch: its ceiling = night_credit_cap + recovery_reserve.
    thp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "thresholds.json")
    try:
        vcfg = (json.load(open(thp)).get("verify") or {})
        ncap = int(vcfg.get("night_credit_cap", 100))
        reserve = reserve if reserve else int(vcfg.get("recovery_reserve", 0))
    except Exception:
        ncap = 100
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return db.count("cost_ledger", "created_at=gte.%s&provider=in.(millionverifier,hunter)" % day) >= (ncap + reserve)


def _candidates(company_id):
    out = []
    for f in db.select("enrichment_findings", "company_id=eq.%s&field=eq.email_candidates&select=value" % company_id):
        v = f.get("value")
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                v = [v]
        if isinstance(v, list):
            out += [str(x).strip().lower() for x in v if "@" in str(x)]
        elif isinstance(v, str) and "@" in v:
            out.append(v.strip().lower())
    seen, r = set(), []
    for e in out:
        if e not in seen and _hygienic(e):  # drop malformed/placeholder before they cost a verify credit
            seen.add(e)
            r.append(e)
    return r


def _rank(cands, full_name):
    toks = [t for t in re.split(r"[^a-z]+", (full_name or "").lower()) if len(t) > 1]

    def score(e):
        lp = e.split("@")[0]
        if toks and any(t in lp for t in toks):
            return 0          # personal (matches the decisor) first
        if lp in ROLE:
            return 2          # role inbox last (allowed, but prefer personal)
        return 1
    return sorted(cands, key=score)


def promote(client_lead_id, apply=False, max_verify=3):
    cl = db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,contact_id,state" % client_lead_id)
    if not cl:
        return {"skip": "no lead"}
    cl = cl[0]
    if not cl.get("contact_id"):
        return {"skip": "no decisor"}
    ct = (db.select("contacts", "id=eq.%s&select=full_name,email" % cl["contact_id"]) or [{}])[0]
    if ct.get("email"):
        return {"skip": "has email"}
    cands = _rank(_candidates(cl["company_id"]), ct.get("full_name"))
    if not cands:
        return {"skip": "no candidates"}
    if not apply:
        return {"recoverable": True, "candidates": cands[:max_verify]}
    for e in cands[:max_verify]:
        if _ncap_reached():
            return {"skip": "night_credit_cap"}
        v = verifier.verify(e, client_id=cl["client_id"])
        if not v.get("ok"):
            continue
        st, res = (v.get("status") or "").lower(), (v.get("result") or "").lower()
        if res == "deliverable" or st == "valid":
            db.update("contacts", "id=eq.%s" % cl["contact_id"],
                      {"email": e, "email_status": "verified", "email_verified_at": _now(), "email_source": "promoted_candidate"})
            try:
                if cl["state"] in ("PARKED", "T2_ENRICHING", "SCORED"):
                    lead_state.move(cl["id"], "GATE_CHECK")
            except Exception:
                pass
            queue.enqueue("verify", client_id=cl["client_id"], company_id=cl["company_id"], client_lead_id=cl["id"])
            return {"promoted": e}
    return {"not_deliverable": True, "tried": min(len(cands), max_verify)}


def sweep(client_id=None, max_leads=15, apply=False):
    """Promote found candidates for parked-with-decisor-no-email leads. Bounded (max_leads processed per run)."""
    clients = [client_id] if client_id else [c["id"] for c in db.select("clients", "select=id")]
    out = {"checked": 0, "recoverable": 0, "promoted": 0}
    for cid in clients:
        rows = db.select_all("client_leads",
                             "client_id=eq.%s&state=eq.PARKED&contact_id=not.is.null&select=id&limit=500" % cid)
        for r in rows:
            if out["checked"] >= max_leads:
                break
            res = promote(r["id"], apply=apply)
            if res.get("skip") in ("no candidates", "no decisor", "has email"):
                continue
            out["checked"] += 1
            if res.get("recoverable") or res.get("promoted"):
                out["recoverable"] += 1
            if res.get("promoted"):
                out["promoted"] += 1
    return out
