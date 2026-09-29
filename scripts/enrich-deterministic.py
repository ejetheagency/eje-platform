#!/usr/bin/env python3
# scripts/enrich-deterministic.py
#
# COST GOVERNOR, stage 1: DETERMINISTIC enrichment. Most enrichment is EXTRACTION, not thinking.
# This pulls email / Instagram / LinkedIn / phone off a company's own site with regex + HTML
# parsing, ZERO LLM calls. It fixes the common "no channel / no email" holds for free. Only the
# messy, ambiguous cases fall through to the cheap-LLM lane (a later, cheap step), never Opus.
#
#   python3 scripts/enrich-deterministic.py https://example.com     # enrich one site (print)
#   python3 scripts/enrich-deterministic.py --held                   # try to fix all HELD eje leads
#   python3 scripts/enrich-deterministic.py --held --apply           # write the found channels/email
#
# Real-world win: a held lead with no IG/LinkedIn often has them right in its footer.

import sys, re, json, urllib.request, urllib.parse, ssl

SB="https://ogdsuztzhmnnjolilsuo.supabase.co"
KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZHN1enR6aG1ubmpvbGlsc3VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMDI0MDMsImV4cCI6MjA5MTc3ODQwM30.9iKhJJWd_zg6WfdxTR9ojK4DVLR3e-bLdPXY-0uDp7Q"
H={"apikey":KEY,"Authorization":"Bearer "+KEY}
APPLY="--apply" in sys.argv
UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
CTX=ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
SUBPAGES=["","/contact","/contacto","/contacto/","/about","/nosotros","/equipo","/team","/quienes-somos","/info"]
EMAIL_RE=re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
IG_RE=re.compile(r"instagram\.com/([A-Za-z0-9_.]+)")
LI_RE=re.compile(r"linkedin\.com/(?:in|company)/([A-Za-z0-9_%\-]+)")
BAD_EMAIL=re.compile(r"\.(png|jpg|jpeg|gif|webp|svg)$", re.I)
IG_SKIP={"p","reel","explore","accounts","tv","stories"}

def sb_get(q): return json.load(urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/"+q,headers=H)))
def sb_patch(q,b): urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/"+q,data=json.dumps(b).encode(),headers={**H,"Content-Type":"application/json","Prefer":"return=minimal"},method="PATCH"))

def fetch(url, timeout=12):
    try:
        r=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=timeout,context=CTX)
        return r.read(600000).decode("utf-8","ignore")
    except Exception:
        return ""

def enrich(site):
    if not site.startswith("http"): site="https://"+site
    base=site.rstrip("/")
    emails=set(); igs=set(); lis=set()
    for sp in SUBPAGES:
        html=fetch(base+sp)
        if not html: continue
        for e in EMAIL_RE.findall(html):
            if not BAD_EMAIL.search(e) and "sentry" not in e and "example" not in e: emails.add(e.lower())
        for h in IG_RE.findall(html):
            if h.lower() not in IG_SKIP and len(h)>1: igs.add(h)
        for h in LI_RE.findall(html):
            if h.lower() not in ("company",): lis.add(h)
    # prefer a role/company email that matches the domain
    dom=urllib.parse.urlparse(base).netloc.replace("www.","")
    email=next((e for e in emails if e.endswith("@"+dom)), (sorted(emails)[0] if emails else None))
    ig=sorted(igs, key=len)[0] if igs else None
    li=sorted(lis, key=len)[0] if lis else None
    return {"email":email,"instagram":ig,"linkedin":("https://www.linkedin.com/company/"+li) if li else None,
            "all_emails":sorted(emails)[:5],"all_ig":sorted(igs)[:5]}

def main():
    args=[a for a in sys.argv[1:] if not a.startswith("--")]
    if "--held" in sys.argv:
        leads=sb_get("leads?client_id=eq.eje&select=id,company,lead_data&limit=1000")
        held=[l for l in leads if not ((l.get('lead_data') or {}).get('instagramHandle') or (l.get('lead_data') or {}).get('contactLinkedIn'))]
        print(f"deterministic enrichment on {len(held)} channel-less lead(s) (no LLM):\n")
        for l in held:
            ld=l.get("lead_data") or {}; site=ld.get("website") or ("https://"+l["id"])
            r=enrich(site)
            found=[]
            if r["instagram"]: found.append("IG @"+r["instagram"])
            if r["linkedin"]: found.append("LinkedIn")
            if r["email"] and not ld.get("contactEmail"): found.append("email "+r["email"])
            print(f"  {l['company'][:24]:24} {site[:34]:34} -> {', '.join(found) if found else 'nothing found'}")
            if APPLY and (r["instagram"] or r["linkedin"]):
                if r["instagram"]: ld["instagramHandle"]=r["instagram"]
                if r["linkedin"] and not ld.get("contactLinkedIn"): ld["contactLinkedIn"]=r["linkedin"]
                sb_patch(f"leads?id=eq.{urllib.parse.quote(l['id'])}&client_id=eq.eje",{"lead_data":ld})
        print("\n(add --apply to write the found channels; email needs a verify pass before use)")
    elif args:
        print(json.dumps(enrich(args[0]), indent=2, ensure_ascii=False))
    else:
        print("usage: enrich-deterministic.py <url> | --held [--apply]")

if __name__=="__main__":
    main()
