# factory/providers/gemini.py
# Tier-1 cheap LLM (uses the existing GEMINI_API_KEY). Writes a short factual brief for a company.
# Mirrors api/_lib/llm.js (gemini-flash-lite, temp 0). Every call is gated by can_spend + logged.
import os, json, urllib.request
from factory.packages import db, budget  # importing db also loads .env into os.environ

MODEL = "gemini-flash-lite-latest"
PROVIDER = "gemini"
EST_USD = 0.0002  # ~cost of one flash-lite call; refined by the ledger over time
_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _gen(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("no GEMINI_API_KEY")
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}}).encode()
    req = urllib.request.Request("%s/models/%s:generateContent?key=%s" % (_BASE, MODEL, key),
                                 data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        j = json.loads(r.read().decode())
    return j["candidates"][0]["content"]["parts"][0]["text"].strip()


def brief(company_id, client_id=None):
    ok, reason = budget.can_spend(client_id, PROVIDER, EST_USD)
    if not ok:
        return {"ok": False, "reason": reason}
    rows = db.select("companies", "id=eq.%s&select=name,domain,country,industry,website,instagram" % company_id)
    if not rows:
        return {"ok": False, "reason": "no company"}
    co = rows[0]
    prompt = ("Escribe un brief factual de 1-2 frases, en espanol neutro, sin guiones largos, sobre esta empresa "
              "para un vendedor que la va a contactar. Solo hechos que puedas inferir de los datos; si no sabes algo, "
              "no lo inventes.\nEmpresa: %s\nWeb: %s\nPais: %s\nIndustria: %s\nInstagram: %s" % (
                  co.get("name"), co.get("website") or co.get("domain"), co.get("country"),
                  co.get("industry"), co.get("instagram")))
    text = _gen(prompt)
    db.update("companies", "id=eq.%s" % company_id, {"brief": text})
    db.insert("enrichment_findings", {"company_id": company_id, "field": "brief", "value": text,
                                      "source": PROVIDER, "confidence": 0.6, "cost_usd": EST_USD}, returning=False)
    budget.log_cost(PROVIDER, EST_USD, client_id=client_id, company_id=company_id, job_type="enrich_t1", estimated=True)
    return {"ok": True, "brief": text}
