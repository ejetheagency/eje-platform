# factory/workers/composer.py
# The Composer: turns a READY lead's VERIFIED facts into a premium, personalized dossier + first-touch pitch.
# This is the unbeatable layer. Rules: use ONLY provided facts (no hallucination), cite each claim, address the
# real decisor by name, lead with the real "why-now" signal, offer to do something, soft CTA. Premium LLM lane.
import json
from factory.packages import db
from factory.providers import cheap_llm

DEFAULT_VOICE = ("espanol neutro LATAM, calido y directo, sin guiones largos; ofrece hacer algo (un resumen, una idea), "
                 "no pide; cierre de esfuerzo cero (una pregunta que se responde en un toque)")
DEFAULT_VOICE_EN = ("direct, warm US business English, no em dashes; lead with one real fact about the business, state "
                    "the value in one line, offer to do something, end with a zero-effort capacity question")


def _extract_json(s):
    s = str(s or "").strip().replace("```json", "").replace("```", "").strip()
    i = s.find("{")
    if i < 0:
        return {}
    depth = 0
    instr = False
    esc = False
    for j in range(i, len(s)):
        c = s[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[i:j + 1])
                except Exception:
                    return {}
    return {}


def _facts(client_lead_id):
    cl = (db.select("client_leads", "id=eq.%s&select=client_id,company_id,contact_id,score" % client_lead_id) or [None])[0]
    if not cl:
        return None
    co = (db.select("companies", "id=eq.%s&select=name,website,domain,industry,country,brief,instagram,linkedin" % cl["company_id"]) or [{}])[0]
    ct = {}
    if cl.get("contact_id"):
        ct = (db.select("contacts", "id=eq.%s&select=full_name,title,email,email_source" % cl["contact_id"]) or [{}])[0]
    signals = db.select("signals", "company_id=eq.%s&select=type,detail" % cl["company_id"])
    client = (db.select("clients", "id=eq.%s&select=name,icp_config" % cl["client_id"]) or [{}])[0]
    return {"cl": cl, "co": co, "ct": ct, "signals": signals, "client": client}


def _facts_block(f):
    co, ct = f["co"], f["ct"]
    lines = ["- Empresa: %s (%s) - %s, %s" % (co.get("name"), co.get("website") or co.get("domain") or "sin web",
                                              co.get("industry") or "industria n/d", co.get("country") or "")]
    if co.get("brief"):
        lines.append("- Que hacen (de su propio sitio): " + co["brief"])
    if ct.get("full_name"):
        lines.append("- Decisor: %s, %s - email %s (verificado via %s)" % (
            ct.get("full_name"), ct.get("title") or "cargo n/d", ct.get("email") or "s/email", ct.get("email_source") or "fuente"))
    if co.get("instagram"):
        lines.append("- Instagram: @" + co["instagram"])
    if f["signals"]:
        lines.append("- Senal POR QUE AHORA: " + "; ".join("%s (%s)" % (s["type"], s.get("detail") or "") for s in f["signals"]))
    return "\n".join(lines)


def compose(client_lead_id):
    f = _facts(client_lead_id)
    if not f:
        return {"ok": False, "reason": "no lead"}
    icp = (f["client"].get("icp_config") or {})
    lang = (icp.get("language") or "es").lower()
    if lang == "en":
        voice = icp.get("voice") or DEFAULT_VOICE_EN
        decisor = f["ct"].get("full_name") or "the decision-maker"
        prompt = (
            "You are the outreach strategist for %s. Voice: %s.\n"
            "GOLDEN RULE: use ONLY the verified facts below. If a fact is not listed, do NOT mention it. NEVER invent "
            "names, numbers, awards or clients. Every claim in the dossier must rest on a listed fact. No em dashes.\n\n"
            "VERIFIED FACTS:\n%s\n\n"
            "Client ICP: %s\n\n"
            "Return ONLY valid JSON:\n"
            "{\n"
            '  "dossier": [3-4 bullets of verified, actionable intelligence about this lead],\n'
            '  "pitch": "a 4-6 line first-touch message in ENGLISH: greet %s by name, cite the real why-now signal, '
            'state the value in one line, offer to do something concrete (do not ask for much), end with a zero-effort '
            'capacity question",\n'
            '  "channel": "email|instagram|linkedin|whatsapp (choose from what we have)",\n'
            '  "next_action": "the concrete next step for the operator",\n'
            '  "citations": {"key_claim": "the verified fact that supports it"}\n'
            "}" % (f["client"].get("name") or "the client", voice, _facts_block(f), json.dumps(icp.get("icp") or "n/a"), decisor)
        )
    else:
        voice = icp.get("voice") or DEFAULT_VOICE
        decisor = f["ct"].get("full_name") or "el decisor"
        prompt = (
            "Sos el estratega de outreach de %s. Voz: %s.\n"
            "REGLA DE ORO: usa SOLO los hechos verificados de abajo. Si un dato no esta, NO lo menciones. NUNCA inventes "
            "nombres, cifras, premios ni clientes. Cada afirmacion del dossier debe apoyarse en un hecho listado.\n\n"
            "HECHOS VERIFICADOS:\n%s\n\n"
            "ICP del cliente: %s\n\n"
            "Devolve SOLO JSON valido:\n"
            "{\n"
            '  "dossier": [3-4 bullets de inteligencia verificada y accionable sobre este lead],\n'
            '  "pitch": "mensaje de primer contacto de 4-6 lineas: saluda a %s por su nombre, menciona la senal real '
            'por-que-ahora, ofrece hacer algo concreto (no pidas), cierre de esfuerzo cero",\n'
            '  "channel": "email|instagram|linkedin|whatsapp (elegi segun lo que tengamos del lead)",\n'
            '  "next_action": "el proximo paso concreto para el operador",\n'
            '  "citations": {"afirmacion_clave": "el hecho verificado que la respalda"}\n'
            "}" % (f["client"].get("name") or "el cliente", voice, _facts_block(f), json.dumps(icp.get("icp") or "n/d"), decisor)
        )
    out = cheap_llm.generate(prompt, client_id=f["cl"]["client_id"], job_type="compose", premium=True)
    parsed = _extract_json(out["text"])
    parsed["_provider"] = out["provider"]
    parsed["ok"] = bool(parsed.get("pitch"))
    return parsed


def generic_baseline(client_lead_id):
    """What ad-hoc Claude would do WITHOUT our verified facts — for the head-to-head proof."""
    f = _facts(client_lead_id)
    name = f["co"].get("name") if f else "the company"
    out = cheap_llm.generate("Write a short cold outreach email to %s." % name, job_type="baseline", premium=True)
    return out["text"]
