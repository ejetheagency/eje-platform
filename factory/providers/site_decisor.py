# factory/providers/site_decisor.py
# FREE contact pivot (Pivot Engine): a cheap LLM reads the company's own team/about/contact pages and extracts
# the NAMED decision-maker (owner/founder/CEO/director) + email. Runs BEFORE paid Hunter. Grounded: the email
# must literally appear on the page (anti-hallucination), so a cheap model can't invent a contact.
import re, json, urllib.request
from factory.packages import db
from factory.providers import cheap_llm

PROVIDER = "site_decisor"
PAGES = ["/equipo", "/nosotros", "/about", "/about-us", "/team", "/quienes-somos", "/nuestro-equipo", "/contacto", "/contact", ""]
UA = {"User-Agent": "Mozilla/5.0 (compatible; EJEFactory/1.0)"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _text(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12) as r:
            html = r.read(400000).decode("utf-8", "ignore")
    except Exception:
        return ""
    html = re.sub(r"<script[\s\S]*?</script>", " ", html)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def find(company_id, client_id=None):
    rows = db.select("companies", "id=eq.%s&select=domain,website,name" % company_id)
    if not rows:
        return {"ok": False, "reason": "no company"}
    co = rows[0]
    base = (co.get("website") or (("https://" + co["domain"]) if co.get("domain") else "")).rstrip("/")
    if not base:
        return {"ok": False, "reason": "no site"}
    if not base.startswith("http"):
        base = "https://" + base

    text = ""
    for p in PAGES:
        t = _text(base + p)
        if t:
            text += " " + t
        if len(text) > 12000:
            break
    if not text.strip():
        return {"ok": True, "found": False}

    emails_on_page = set(e.lower() for e in EMAIL_RE.findall(text))
    prompt = ("Del texto del sitio de la empresa '%s', extrae al DECISOR principal (dueno/fundador/CEO/director/"
              "gerente general). Devolve SOLO JSON: {\"name\":..,\"role\":..,\"email\":..}. Usa SOLO datos que "
              "aparezcan literalmente en el texto; si no hay un decisor con nombre claro, devolve {}. No inventes.\n\n"
              "TEXTO:\n%s" % (co.get("name"), text[:9000]))
    try:
        out = cheap_llm.generate(prompt, client_id=client_id, job_type="site_decisor")
    except Exception as e:
        return {"ok": False, "reason": str(e)}

    s = out["text"].strip().replace("```json", "").replace("```", "")
    i, jlast = s.find("{"), s.rfind("}")
    try:
        d = json.loads(s[i:jlast + 1]) if (i >= 0 and jlast > i) else {}
    except Exception:
        d = {}
    name = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip().lower()
    if email and email not in emails_on_page:  # anti-hallucination: email must be on the page
        email = ""
    if not name or not email:
        return {"ok": True, "found": False}
    return {"ok": True, "found": True, "name": name, "role": d.get("role"), "email": email}
