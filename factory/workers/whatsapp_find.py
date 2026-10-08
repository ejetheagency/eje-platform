# factory/workers/whatsapp_find.py
# WHATSAPP micro-route (proven 2026-10-07, see docs/MULTICHANNEL_ENRICHMENT_PLAYBOOK.md). DETERMINISTIC, no LLM:
# fetch the site's raw HTML and extract the number behind the WhatsApp button. Priority = wa.me / api.whatsapp /
# whatsapp:// link (UNAMBIGUOUS = it IS the business's WhatsApp, ~100% precision); fallback = tel: href with a valid
# LatAm mobile format. NEVER loose-regex phones from page text (false positives from analytics IDs/prices).
import re, ssl, urllib.request, json, datetime
from factory.packages import db

_CTX = ssl.create_default_context(); _CTX.check_hostname = False; _CTX.verify_mode = ssl.CERT_NONE
_UA = {"User-Agent": "Mozilla/5.0 (compatible; EJEFactory/1.0)"}
_WA = re.compile(r'(?:wa\.me/|api\.whatsapp\.com/send\?phone=|whatsapp://send\?phone=|wa\.link/|web\.whatsapp\.com/send\?phone=)(\+?\d[\d]{6,15})', re.I)
_TEL = re.compile(r'tel:(\+?\d[\d\s().-]{6,16}\d)')
# valid LatAm mobile (after stripping non-digits, keep leading +): EC +5939…, MX +521…, CL +569…, CO +573…
_VALID = re.compile(r'^\+?(?:593\d{8,9}|52\d{10}|521\d{10}|56\d{9}|569\d{8}|57\d{10}|573\d{9})$')


def _norm(n):
    return re.sub(r'[^\d+]', '', n or '')


def _fetch(url):
    if not url or 'instagram.com' in url or 'facebook.com' in url:
        return ''
    u = url if url.startswith('http') else 'https://' + url
    for path in ('', '/contacto', '/contact', '/contacto/'):
        try:
            req = urllib.request.Request(u.rstrip('/') + path, headers=_UA)
            return urllib.request.urlopen(req, timeout=12, context=_CTX).read(400000).decode('utf-8', 'ignore')
        except Exception:
            continue
    return ''


def find(website):
    """Return {'whatsapp': '+<digits>', 'via': 'wa.me-link'|'tel:', 'confidence': 'high'|'medium'} or {}."""
    html = _fetch(website)
    if not html:
        return {}
    wa = _WA.findall(html)
    if wa:
        num = _norm(wa[0])
        return {"whatsapp": num if num.startswith('+') else '+' + num, "via": "wa.me-link", "confidence": "high"}
    tel = _TEL.findall(html)
    for t in tel:
        num = _norm(t)
        if _VALID.match(num):
            return {"whatsapp": num if num.startswith('+') else '+' + num, "via": "tel:", "confidence": "medium"}
    return {}


def _company_website(cid):
    r = db.select("companies", "id=eq.%s&select=website,domain" % cid)
    if not r:
        return None
    return r[0].get("website") or r[0].get("domain")


def sweep(client_id=None, limit=60, apply=False):
    """REAL measurement/enrichment: run the WhatsApp micro-route over this client's shippable leads' companies.
    apply=True also writes the number to the contact (phone) + logs an enrichment_finding. Returns actual yield."""
    # Pre-gate states included (2026-10-07): find WhatsApp BEFORE the channel gate so it can clear the bar, not only
    # on already-READY leads. contact_id must exist (we write the number to the contact's phone).
    q = ("client_id=eq.%s&" % client_id if client_id else "") + "state=in.(SCORED,T2_ENRICHING,GATE_CHECK,PARKED,READY,DELIVERED)&contact_id=not.is.null&select=id,company_id,contact_id&limit=%d" % limit
    rows = db.select_all("client_leads", q)
    out = {"checked": 0, "found": 0, "by_via": {}, "examples": []}
    for r in rows:
        site = _company_website(r["company_id"])
        if not site:
            continue
        out["checked"] += 1
        res = find(site)
        if not res:
            continue
        out["found"] += 1
        out["by_via"][res["via"]] = out["by_via"].get(res["via"], 0) + 1
        if len(out["examples"]) < 8:
            out["examples"].append((site[:40], res["whatsapp"], res["via"]))
        if apply:
            try:
                ct = (db.select("contacts", "id=eq.%s&select=phone" % r["contact_id"]) or [{}])[0]
                if not ct.get("phone"):
                    db.update("contacts", "id=eq.%s" % r["contact_id"], {"phone": res["whatsapp"]})
                db.insert("enrichment_findings", {"company_id": r["company_id"], "field": "whatsapp",
                          "value": res["whatsapp"], "source": "whatsapp_" + res["via"], "pivot_name": "whatsapp_find"}, returning=False)
            except Exception:
                pass
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(sweep(sys.argv[1] if len(sys.argv) > 1 else None, apply=("--apply" in sys.argv)), indent=2, ensure_ascii=False))
