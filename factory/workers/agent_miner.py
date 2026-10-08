# factory/workers/agent_miner.py
# COMPETENT MINER (the fix for the 0-vs-30 competence gap). Replicates what the subagents did — multi-route research
# with the factory's OWN tools: Serper (search) + raw fetch + cheap LLM (judgment) + deterministic extractors.
# Per business: find the real site -> extract email (gmail/contacto) + WhatsApp (wa.me) + IG (regex) -> find the OWNER
# (site text via cheap LLM, else press-search). Returns a candidate card; the normal gates (MV-verify/dedup/country)
# run downstream. This is the agent-driven worker the rigid provider-chain pipeline was missing.
import re, ssl, json, time, urllib.request
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
# Institutional / aggregator / non-business domains -> hard reject BEFORE the ICP-fit judge (a university thesis
# repository, a govt site, or a marketplace is never a 1-3 employee owner-led company, no matter the page text).
_NONBIZ = (".edu", ".gob", ".gov", "repositorio", "universidad", "biblioteca", "wikipedia", "mercadolibre",
           "paginasamarillas", "amarillas.", "directorio", "guiatelefonica", ".mil", "scielo", "dspace")


def _is_nonbiz(dom):
    d = (dom or "").lower()
    return any(t in d for t in _NONBIZ)


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


def _owner_from_text(company, text, client_id, roles=None):
    roles = roles or "owner/founder/dueño/dueña/fundador/CEO/gerente general/gerente financiero/CFO/director"
    prompt = ("From this web text about the business \"%s\", extract the DECISION-MAKER's full name and role ONLY if a "
              "specific real person is clearly named in one of these roles: %s. Prefer owner/founder; a general "
              "manager or CFO also counts. Do NOT invent, do NOT return an IT/systems person. "
              'JSON only: {"name":"<full name or empty>","role":"<role or empty>"}.\n%s') % (company, roles, (text or "")[:3000])
    try:
        out = cheap_llm.generate(prompt, client_id=client_id, job_type="agent_owner", judge=True)
        t = out.get("text") or ""
        s, e = t.find("{"), t.rfind("}")
        d = json.loads(t[s:e + 1]) if s >= 0 and e > s else {}
        nm = (d.get("name") or "").strip()
        return {"name": nm, "role": (d.get("role") or "").strip()} if nm and len(nm.split()) >= 2 else {}
    except Exception:
        return {}


def mine_business(query, city, client_id, known_site=None, roles=None):
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
        own = _owner_from_text(query, re.sub(r'<[^>]+>', ' ', html), client_id, roles=roles)
        if own:
            card.update({"decisor_name": own["name"], "decisor_role": own.get("role", "")}); card["sources"].append("site")
    # owner not on site -> press search
    if not card["decisor_name"]:
        sr = serper.search('"%s" %s (fundadora OR fundador OR dueña OR dueño OR propietaria OR CEO)' % (query, city), num=7, client_id=client_id)
        snips = " ".join(((r.get("title") or "") + " " + (r.get("snippet") or "")) for r in (sr.get("results") or [])[:7])
        own = _owner_from_text(query, snips, client_id, roles=roles)
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
              'DESCARTA SIEMPRE (no es empresa comercial pequena con dueno): universidad, biblioteca, repositorio '
              'o tesis academica, entidad de gobierno, ONG/fundacion, marketplace, directorio o guia, medio de '
              'prensa, o cualquier institucion. Debe ser un NEGOCIO con dueno/a que vende un producto o servicio.\n'
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


def mine_report(client_id, n=20, city="Ecuador", queries=None, log=None, per_query_cap=3, max_examine=150, deadline_ts=None):
    """FULLY-ENRICHED, ICP-ALIGNED batch: loop the client's ICP queries -> mine -> gate (named decisor + MV-valid
    email + >=2 channels + ICP-fit) -> dedup -> accumulate n. per_query_cap spreads the batch across sectors
    (VARIETY) instead of over-concentrating on one vein. Returns the finished cards + a per-stage tally.
    deadline_ts (epoch secs, operator 2026-10-08): hard wall-clock stop checked between veins and between cards so
    the miner can never overrun the night; it returns partial work with tally['stopped']='deadline'."""
    c = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
    icp_cfg = (c[0].get("icp_config") or {}) if c else {}
    queries = queries or icp_cfg.get("discovery_queries") or []
    roles = icp_cfg.get("decisor")
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
            if deadline_ts and time.time() > deadline_ts:  # wall-clock wall: stop between veins
                _log("deadline reached — stopping run (%d/%d so far)" % (len(out), n))
                tally["stopped"] = "deadline"
                return {"cards": out, "tally": tally}
            kept_here = 0
            _log("vein (p%d): %s" % (_pass, q))
            for card in mine_vein(q, city, client_id, want=8, roles=roles):
                if len(out) >= n or kept_here >= cap:
                    break
                if deadline_ts and time.time() > deadline_ts:  # wall-clock wall: stop mid-vein too
                    _log("deadline reached mid-vein — stopping run (%d/%d so far)" % (len(out), n))
                    tally["stopped"] = "deadline"
                    return {"cards": out, "tally": tally}
                if tally["mined"] >= max_examine:          # hard per-run ceiling (cost guardrail) — stop even if short
                    _log("max_examine %d reached — stopping run" % max_examine)
                    return {"cards": out, "tally": tally}
                tally["mined"] += 1
                dom = _domain(card.get("website"))
                if not dom or dom in seen:
                    tally["dup"] += 1; continue
                if _is_nonbiz(dom):                       # institutional/aggregator domain -> never a small business
                    tally["off_icp"] += 1; continue
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


def mine_vein(sector, city, client_id, want=8, roles=None):
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
        c = mine_business(re.split(r'[|\-–—:]', title)[0].strip(), city, client_id, known_site=link, roles=roles)
        cards.append(c)
    return cards


def _merge(tpl, card):
    out = tpl or ""
    for k, v in (("{nombre}", (card.get("decisor_name") or "").split(" ")[0]), ("{empresa}", card.get("query") or ""),
                 ("{name}", (card.get("decisor_name") or "").split(" ")[0]), ("{company}", card.get("query") or "")):
        out = out.replace(k, v)
    return out


def publish_batch(client_id, cards, report_date, approved=False):
    """Write fully-enriched mined cards into the `leads` table in the app's shape. approved=False => STAGED
    (pending the operator's gate / not on Hoy); approved=True => live on Hoy. Idempotent upsert by domain."""
    try:
        from factory.workers import tsa
    except Exception:
        tsa = None
    c = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
    ic = (c[0].get("icp_config") or {}) if c else {}
    geo = ic.get("geo") or ""
    ft = ic.get("outreach_first_touch") or ""
    sender = ic.get("sender_name") or ""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    existing = {r["id"]: r for r in db.select_all("leads", "client_id=eq.%s&select=id,status,source_date" % client_id)}
    n = 0
    for card in cards:
        dom = card.get("_domain") or _domain(card.get("website"))
        if not dom:
            continue
        if not (card.get("decisor_name") or "").strip():   # LOCKED RULE: never publish a card without a named decisor
            continue
        site = card.get("website") or ""
        real = site if (not tsa or tsa.real_website(site)) else ""
        ld = {
            "_key": dom, "companyName": card.get("query") or dom, "contactName": card.get("decisor_name") or "",
            "contactEmail": card.get("email_verified") or "", "contactTitle": card.get("decisor_role") or "",
            "country": geo, "website": real, "instagramHandle": card.get("instagram") or "",
            "instagramKind": "profile" if card.get("instagram") else "", "instagramFollowers": 0,
            "contactLinkedIn": card.get("linkedin") or "", "whatsapp": card.get("whatsapp") or "",
            "pitchEmailES": _merge(ft, card), "sender": sender, "whyICP": card.get("icp_reason") or "",
            "companyEmail": None, "score": 0, "source_date": report_date, "additionalContacts": [],
            "_verifiedCredits": [card.get("email_verified")] if card.get("email_verified") else [],
            "approved": bool(approved), "approvedBy": "miner-haiku" if approved else None,
            "approvedAt": now if approved else None, "source": "agent_miner",
        }
        base = {"company": card.get("query") or dom, "contact_name": card.get("decisor_name") or None,
                "contact_email": card.get("email_verified") or None, "lead_data": ld, "updated_at": now}
        if dom in existing:
            db.update("leads", "id=eq.%s&client_id=eq.%s" % (dom, client_id), base)
        else:
            row = dict(base); row.update({"id": dom, "client_id": client_id, "status": "none", "source_date": report_date})
            try:
                db.insert("leads", row, returning=False)
            except Exception:
                db.update("leads", "id=eq.%s&client_id=eq.%s" % (dom, client_id), base)
        n += 1
    return {"client_id": client_id, "published": n, "report_date": report_date, "approved": approved}


def mine_and_publish(client_id, n, report_date, approved=False, publish=True, deadline_ts=None):
    """One call for the nightly: mine n fully-enriched ICP-aligned cards and (optionally) publish them STAGED.
    deadline_ts = hard wall-clock stop (epoch secs) passed through to mine_report."""
    res = mine_report(client_id, n=n, deadline_ts=deadline_ts)
    out = {"tally": res["tally"], "cards": len(res["cards"]), "stopped": res["tally"].get("stopped")}
    if publish and res["cards"]:
        out["publish"] = publish_batch(client_id, res["cards"], report_date, approved=approved)
    return out


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
