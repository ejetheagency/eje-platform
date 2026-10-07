# factory/workers/agent_miner.py
# COMPETENT MINER (the fix for the 0-vs-30 competence gap). Replicates what the subagents did — multi-route research
# with the factory's OWN tools: Serper (search) + raw fetch + cheap LLM (judgment) + deterministic extractors.
# Per business: find the real site -> extract email (gmail/contacto) + WhatsApp (wa.me) + IG (regex) -> find the OWNER
# (site text via cheap LLM, else press-search). Returns a candidate card; the normal gates (MV-verify/dedup/country)
# run downstream. This is the agent-driven worker the rigid provider-chain pipeline was missing.
import re, ssl, json, urllib.request
from factory.providers import serper, cheap_llm, millionverifier
from factory.packages import db

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
    card["_sitetext"] = re.sub(r'<[^>]+>', ' ', html)[:3000] if html else ""
    return card


def _domain(url):
    return re.sub(r'^https?://(www\.)?', '', url or '').split("/")[0].lower()


def icp_fit(company, text, icp_cfg, client_id):
    """Haiku judgment: does this business MATCH the ICP nuances (small, growth-vision) and dodge the disqualifiers?"""
    icp = icp_cfg.get("icp", "")
    disq = "; ".join(icp_cfg.get("disqualifiers", []))
    prompt = ('Eres un filtro de ICP estricto. ICP objetivo: %s\nDESCARTA si aplica cualquiera: %s\n'
              'Del texto del negocio "%s", decide si CALZA. Solo JSON: {"fit":true/false,"reason":"<=12 palabras"}.\n%s'
              % (icp, disq, company, (text or "")[:2500]))
    try:
        out = cheap_llm.generate(prompt, client_id=client_id, job_type="icp_fit", judge=True)
        t = out.get("text") or ""
        s, e = t.find("{"), t.rfind("}")
        d = json.loads(t[s:e + 1]) if s >= 0 and e > s else {}
        return bool(d.get("fit")), (d.get("reason") or "")[:120]
    except Exception:
        return False, "icp_fit_error"


def verify_email(emails, client_id):
    """MV-verify; accept ONLY status 'valid' (deliverable). Catch-all / invalid are rejected (playbook)."""
    for e in emails:
        try:
            v = millionverifier.verify(e, client_id=client_id)
            if v.get("ok") and v.get("status") == "valid":
                return e
        except Exception:
            continue
    return ""


def lane_linkedin(name, company, client_id):
    """Cheap 3rd-channel: find the decisor's personal LinkedIn (confirm-or-empty)."""
    if not name:
        return ""
    try:
        sr = serper.search('%s %s linkedin' % (name, company), num=4, client_id=client_id)
        for r in (sr.get("results") or []):
            link = r.get("link") or ""
            if "linkedin.com/in/" in link:
                return link.split("?")[0]
    except Exception:
        pass
    return ""


def mine_report(client_id, n=20, city="Ecuador", queries=None, log=None, per_query_cap=3):
    """FULLY-ENRICHED, ICP-ALIGNED batch: loop the client's ICP queries -> mine -> gate (named decisor + MV-valid
    email + >=2 channels + ICP-fit) -> dedup -> accumulate n. per_query_cap spreads the batch across sectors
    (VARIETY) instead of over-concentrating on one vein. Returns the finished cards + a per-stage tally."""
    c = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
    icp_cfg = (c[0].get("icp_config") or {}) if c else {}
    queries = queries or icp_cfg.get("discovery_queries") or []
    seen = set(x["id"] for x in db.select_all("leads", "client_id=eq.%s&select=id" % client_id))
    tally = {"mined": 0, "no_decisor": 0, "no_valid_email": 0, "thin_channels": 0, "off_icp": 0, "dup": 0, "kept": 0}
    out = []

    def _log(m):
        if log:
            log(m)
    # two passes over the queries: first pass capped per-query for variety, second pass fills any remainder
    for _pass in (1, 2):
        cap = per_query_cap if _pass == 1 else n
        for q in queries:
            if len(out) >= n:
                break
            kept_here = 0
            _log("vein (p%d): %s" % (_pass, q))
            for card in mine_vein(q, city, client_id, want=8):
                if len(out) >= n or kept_here >= cap:
                    break
                tally["mined"] += 1
                dom = _domain(card.get("website"))
                if not dom or dom in seen:
                    tally["dup"] += 1; continue
                if not card.get("decisor_name"):
                    tally["no_decisor"] += 1; continue
                if not card.get("emails_found"):
                    tally["no_valid_email"] += 1; continue
                email = verify_email(card["emails_found"], client_id)
                if not email:
                    tally["no_valid_email"] += 1; continue
                li = lane_linkedin(card["decisor_name"], card.get("query", ""), client_id)
                ch = 1 + (1 if card.get("instagram") else 0) + (1 if card.get("whatsapp") else 0) + (1 if li else 0)
                if ch < 2:
                    tally["thin_channels"] += 1; continue
                fit, reason = icp_fit(card.get("query", ""), card.get("_sitetext", ""), icp_cfg, client_id)
                if not fit:
                    tally["off_icp"] += 1; continue
                seen.add(dom)
                card.update({"email_verified": email, "linkedin": li, "channels": ch, "icp_reason": reason, "_domain": dom})
                out.append(card); tally["kept"] += 1; kept_here += 1
                _log("  KEPT %d/%d: %s | %s | %s | ch=%d" % (len(out), n, card["decisor_name"], email, dom, ch))
    return {"cards": out, "tally": tally}


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
