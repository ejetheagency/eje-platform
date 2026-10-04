# factory/providers/site_decisor.py
# FREE contact pivot (Pivot Engine, pivot 1): read the company's own site and extract the NAMED decision-maker
# + email. Homepage-first extraction (2026-10-04): JSON-LD Person/Organization blocks, mailto links, and
# Cloudflare data-cfemail decoding run on the RAW html BEFORE the LLM, because many US sites hide the owner's
# email behind cfemail obfuscation or inside JSON-LD, invisible to a text-only read (this is why 34/40 US
# altavia sites failed to name a decisor). Grounded: the email must appear on the page (plaintext, mailto,
# decoded cfemail, or JSON-LD), so a cheap model cannot invent a contact.
import re, json, urllib.request
from factory.packages import db
from factory.providers import cheap_llm

PROVIDER = "site_decisor"
PAGES = ["", "/equipo", "/nosotros", "/about", "/about-us", "/team", "/our-team", "/quienes-somos",
         "/nuestro-equipo", "/contacto", "/contact", "/attorneys", "/staff"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; EJEFactory/1.0)"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MAILTO_RE = re.compile(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.I)
CF_RE = re.compile(r'data-cfemail="([0-9a-fA-F]{6,})"')
TEL_RE = re.compile(r"tel:\+?([0-9().\-\s]{7,})", re.I)
JSONLD_RE = re.compile(r'<script[^>]+application/ld\+json[^>]*>([\s\S]*?)</script>', re.I)
JUNK_EMAIL = ("example.com", "sentry", "wixpress", ".png", ".jpg", "@2x", "domain.com", "email@", "yourdomain")


def _raw(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12) as r:
            return r.read(600000).decode("utf-8", "ignore")
    except Exception:
        return ""


def _strip(html):
    html = re.sub(r"<script[\s\S]*?</script>", " ", html)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _cfdecode(hexstr):
    # Cloudflare email obfuscation: first byte is the XOR key, remaining bytes are the email XORed with it.
    try:
        b = bytes.fromhex(hexstr)
        k = b[0]
        return "".join(chr(c ^ k) for c in b[1:])
    except Exception:
        return ""


def _clean_email(e):
    el = (e or "").replace("mailto:", "").strip().lower()
    return el if ("@" in el and not any(j in el for j in JUNK_EMAIL)) else ""


def _walk_jsonld(obj, persons, org):
    if isinstance(obj, list):
        for x in obj:
            _walk_jsonld(x, persons, org)
        return
    if not isinstance(obj, dict):
        return
    t = obj.get("@type") or obj.get("type")
    types = t if isinstance(t, list) else [t]
    if "Person" in types and (obj.get("name")):
        persons.append({"name": str(obj.get("name")).strip(),
                        "role": str(obj.get("jobTitle") or "").strip(),
                        "email": _clean_email(obj.get("email"))})
    if any(x in types for x in ("Organization", "LocalBusiness", "LegalService", "Dentist", "Attorney", "ProfessionalService")):
        if _clean_email(obj.get("email")) and not org.get("email"):
            org["email"] = _clean_email(obj.get("email"))
        f = obj.get("founder") or obj.get("founders")
        if isinstance(f, dict) and f.get("name"):
            persons.append({"name": str(f["name"]).strip(), "role": "Founder", "email": _clean_email(f.get("email"))})
    for v in obj.values():
        if isinstance(v, (dict, list)):
            _walk_jsonld(v, persons, org)


def _extract(html):
    emails = set()
    for e in EMAIL_RE.findall(html):
        if _clean_email(e):
            emails.add(e.lower())
    for e in MAILTO_RE.findall(html):
        if _clean_email(e):
            emails.add(e.lower())
    for hx in CF_RE.findall(html):
        d = _clean_email(_cfdecode(hx))
        if d:
            emails.add(d)
    persons, org = [], {}
    for block in JSONLD_RE.findall(html):
        try:
            _walk_jsonld(json.loads(block.strip()), persons, org)
        except Exception:
            pass
    phones = [re.sub(r"\s+", " ", p).strip() for p in TEL_RE.findall(html)]
    return {"emails": emails, "persons": [p for p in persons if p.get("name")], "org": org, "phones": phones}


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

    all_emails, persons, org, phones, text = set(), [], {}, [], ""
    for p in PAGES:
        html = _raw(base + p)
        if not html:
            continue
        ex = _extract(html)
        all_emails |= ex["emails"]
        persons += ex["persons"]
        if ex["org"].get("email") and not org.get("email"):
            org["email"] = ex["org"]["email"]
        phones += ex["phones"]
        text += " " + _strip(html)
        if len(text) > 12000 and all_emails:
            break
    phone = phones[0] if phones else None

    # 1) JSON-LD Person carrying an email -> grounded, no LLM needed (the cheapest, strongest path).
    for per in persons:
        if per.get("name") and per.get("email"):
            return {"ok": True, "found": True, "name": per["name"], "role": per.get("role") or None,
                    "email": per["email"], "phone": phone, "via": "jsonld"}
    if not text.strip() and not all_emails:
        return {"ok": True, "found": False}

    # 2) cheap LLM picks the decisor from the team/about text; ground the email against the FULL decoded set.
    email_list = ", ".join(sorted(all_emails)[:15]) or "(ninguno)"
    prompt = ("Del sitio de la empresa '%s', identifica al DECISOR principal (dueno/fundador/CEO/socio/"
              "director/gerente general). Emails encontrados en el sitio: %s. Devolve SOLO JSON "
              "{\"name\":..,\"role\":..,\"email\":..}: el email debe ser UNO de esa lista que pertenezca al "
              "decisor, o el inbox principal si no hay uno personal. Si no hay un decisor con nombre claro, "
              "devolve {}. No inventes datos.\n\nTEXTO:\n%s" % (co.get("name"), email_list, text[:9000]))
    try:
        out = cheap_llm.generate(prompt, client_id=client_id, job_type="site_decisor")
    except Exception as e:
        # LLM down but we may still have a JSON-LD person name + a decoded email
        if persons:
            return {"ok": True, "found": True, "name": persons[0]["name"], "role": persons[0].get("role") or None,
                    "email": org.get("email") or (sorted(all_emails)[0] if all_emails else ""), "phone": phone, "via": "jsonld-name"}
        return {"ok": False, "reason": str(e)}

    s = out["text"].strip().replace("```json", "").replace("```", "")
    i, jlast = s.find("{"), s.rfind("}")
    try:
        d = json.loads(s[i:jlast + 1]) if (i >= 0 and jlast > i) else {}
    except Exception:
        d = {}
    name = (d.get("name") or "").strip()
    role = d.get("role")
    email = _clean_email(d.get("email"))
    if email and email not in all_emails:  # anti-hallucination: email must be on the page
        email = ""
    if name and not email:  # attach the best grounded email: name-matched localpart, else org inbox, else first
        first = name.split(" ")[0].lower()
        email = next((e for e in all_emails if first and len(first) > 2 and first in e.split("@")[0]), "") \
            or org.get("email") or (sorted(all_emails)[0] if all_emails else "")
    if not name or not email:
        return {"ok": True, "found": False}
    return {"ok": True, "found": True, "name": name, "role": role, "email": email, "phone": phone, "via": "llm"}
