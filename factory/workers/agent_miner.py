# factory/workers/agent_miner.py
# COMPETENT MINER (the fix for the 0-vs-30 competence gap). Replicates what the subagents did — multi-route research
# with the factory's OWN tools: Serper (search) + raw fetch + cheap LLM (judgment) + deterministic extractors.
# Per business: find the real site -> extract email (gmail/contacto) + WhatsApp (wa.me) + IG (regex) -> find the OWNER
# (site text via cheap LLM, else press-search). Returns a candidate card; the normal gates (MV-verify/dedup/country)
# run downstream. This is the agent-driven worker the rigid provider-chain pipeline was missing.
import re, ssl, json, urllib.request
from factory.providers import serper, cheap_llm

_CTX = ssl.create_default_context(); _CTX.check_hostname = False; _CTX.verify_mode = ssl.CERT_NONE
_UA = {"User-Agent": "Mozilla/5.0 (compatible; EJEFactory/1.0)"}
_EMAIL = re.compile(r'[a-z0-9][a-z0-9._%+-]*@[a-z0-9.-]+\.[a-z]{2,}', re.I)
_WA = re.compile(r'(?:wa\.me/|api\.whatsapp\.com/send\?phone=|whatsapp://send\?phone=)(\+?\d[\d]{6,15})', re.I)
_IG = re.compile(r'instagram\.com/([A-Za-z0-9_.]{2,30})', re.I)
_JUNK = ("sentry", "wixpress", "example.com", "ejemplo.com", "ejemplo.", "dominio.com", "domain.com", "tucorreo",
         "youremail", "your-email", "email@email", "correo@correo", "nombre@", "@2x", ".png", ".jpg", "@sentry")
_SOCIAL = ("facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "youtube.com", "tiktok.com", "wikipedia.org", "google.")


def _fetch(url):
    u = url if url.startswith("http") else "https://" + url
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers=_UA), timeout=12, context=_CTX).read(400000).decode("utf-8", "ignore")
    except Exception:
        return ""


def _emails(html):
    out = []
    for e in _EMAIL.findall(html or ""):
        e = e.lower()
        if not any(j in e for j in _JUNK) and e not in out:
            out.append(e)
    return out[:6]


def _discover_emails(site, query, city, client_id):
    """Reach the business's own contacto pages, then a targeted search. Returns real (non-placeholder) emails."""
    found = []
    if site:
        base = re.sub(r'/+$', '', site if site.startswith("http") else "https://" + site)
        for path in ("", "/contacto", "/contactanos", "/contactenos", "/contact", "/nosotros"):
            for e in _emails(_fetch(base + path)):
                if e not in found:
                    found.append(e)
            if found:
                break
    if not found:  # email not on-site -> targeted search (snippets + top business page)
        sr = serper.search('"%s" %s (correo OR email OR contacto)' % (query, city), num=6, client_id=client_id)
        rs = (sr.get("results") or [])
        snips = " ".join(((r.get("title") or "") + " " + (r.get("snippet") or "")) for r in rs)
        found += [e for e in _emails(snips) if e not in found]
        for r in rs[:3]:
            if found:
                break
            link = r.get("link") or ""
            if link and not any(s in link for s in _SOCIAL):
                found += [e for e in _emails(_fetch(link)) if e not in found]
    return found[:6]


def _owner_from_text(company, text, client_id):
    prompt = ("From this web text about the business \"%s\", extract the OWNER/FOUNDER's full name and role ONLY if a "
              "specific real person is clearly named as owner/founder/dueño/dueña/fundador/a/CEO. Do NOT invent. "
              'JSON only: {"name":"<full name or empty>","role":"<role or empty>"}.\n%s') % (company, (text or "")[:3000])
    try:
        out = cheap_llm.generate(prompt, client_id=client_id, job_type="agent_owner", judge=True)
        t = out.get("text") or ""
        s, e = t.find("{"), t.rfind("}")
        d = json.loads(t[s:e + 1]) if s >= 0 and e > s else {}
        nm = (d.get("name") or "").strip()
        return {"name": nm, "role": (d.get("role") or "").strip()} if nm and len(nm.split()) >= 2 else {}
    except Exception:
        return {}


def mine_business(query, city, client_id, known_site=None):
    """Research ONE business end to end -> candidate card. query = business name or 'sector ciudad'."""
    site = known_site
    if not site:
        sr = serper.search('%s %s' % (query, city), num=6, client_id=client_id)
        for r in (sr.get("results") or []):
            link = r.get("link") or ""
            if link and not any(s in link for s in _SOCIAL):
                site = link; break
    card = {"query": query, "city": city, "website": site or "", "decisor_name": "", "decisor_role": "",
            "emails_found": [], "instagram": "", "whatsapp": "", "sources": []}
    html = _fetch(site) if site else ""
    if html:
        card["emails_found"] = _emails(html)
        wa = _WA.findall(html)
        if wa:
            card["whatsapp"] = wa[0] if wa[0].startswith("+") else "+" + wa[0]
        ig = _IG.findall(html)
        ig = [h for h in ig if h.lower() not in ("p", "reel", "explore", "accounts")]
        if ig:
            card["instagram"] = "@" + ig[0]
        own = _owner_from_text(query, re.sub(r'<[^>]+>', ' ', html), client_id)
        if own:
            card.update({"decisor_name": own["name"], "decisor_role": own.get("role", "")}); card["sources"].append("site")
    # owner not on site -> press search
    if not card["decisor_name"]:
        sr = serper.search('"%s" %s (fundadora OR fundador OR dueña OR dueño OR propietaria OR CEO)' % (query, city), num=7, client_id=client_id)
        snips = " ".join(((r.get("title") or "") + " " + (r.get("snippet") or "")) for r in (sr.get("results") or [])[:7])
        own = _owner_from_text(query, snips, client_id)
        if own:
            card.update({"decisor_name": own["name"], "decisor_role": own.get("role", "")}); card["sources"].append("press")
    if not card["emails_found"]:  # on-site extraction empty -> contacto pages + targeted search
        em = _discover_emails(site, query, city, client_id)
        if em:
            card["emails_found"] = em; card["sources"].append("email_discovery")
    return card


def mine_vein(sector, city, client_id, want=8):
    """Discover businesses in a vein and research each -> candidate cards (the competent discovery+enrich in one)."""
    sr = serper.search('%s %s' % (sector, city), num=min(want * 2, 20), client_id=client_id)
    sites, seen = [], set()
    for r in (sr.get("results") or []):
        link = r.get("link") or ""
        host = re.sub(r'^https?://(www\.)?', '', link).split("/")[0]
        if link and host and host not in seen and not any(s in link for s in _SOCIAL):
            seen.add(host); sites.append((r.get("title") or host, link))
        if len(sites) >= want:
            break
    cards = []
    for title, link in sites:
        c = mine_business(re.split(r'[|\-–—:]', title)[0].strip(), city, client_id, known_site=link)
        cards.append(c)
    return cards


if __name__ == "__main__":
    import sys
    sector = sys.argv[1] if len(sys.argv) > 1 else "cosmetica natural"
    city = sys.argv[2] if len(sys.argv) > 2 else "Ecuador"
    cards = mine_vein(sector, city, "2uplatam", want=6)
    complete = [c for c in cards if c["decisor_name"] and c["emails_found"]]
    print("vein '%s %s': %d businesses -> %d with owner+email (%d%%)" % (
        sector, city, len(cards), len(complete), round(100 * len(complete) / len(cards)) if cards else 0))
    for c in cards:
        flag = "OK" if (c["decisor_name"] and c["emails_found"]) else "--"
        print("  [%s] %-28s | owner=%-22s | email=%s | wa=%s | ig=%s" % (
            flag, (c["query"] or "")[:28], (c["decisor_name"] or "-")[:22], (c["emails_found"] or ["-"])[0], c["whatsapp"] or "-", c["instagram"] or "-"))
