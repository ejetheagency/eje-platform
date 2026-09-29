#!/usr/bin/env python3
# scripts/deepen-briefs.py
#
# COST GOVERNOR in action: fix the gate's "thin brief" soft-flag with the CHEAP lane.
# For each EJE lead with a thin companyBrief, fetch the site (deterministic, $0), then ask the
# cheap model (via llm_router -> Gemini flash-lite, ~free) to write a factual 2-3 sentence brief.
# Premium models are never touched. Every call is cached + metered in the router ledger.
#
#   python3 scripts/deepen-briefs.py --limit 3           # DRY: show generated briefs for 3 leads
#   python3 scripts/deepen-briefs.py --limit 20 --apply   # write richer briefs for 20 leads

import os, sys, re, json, ssl, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_router import route

SB="https://ogdsuztzhmnnjolilsuo.supabase.co"
KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZHN1enR6aG1ubmpvbGlsc3VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMDI0MDMsImV4cCI6MjA5MTc3ODQwM30.9iKhJJWd_zg6WfdxTR9ojK4DVLR3e-bLdPXY-0uDp7Q"
H={"apikey":KEY,"Authorization":"Bearer "+KEY}
APPLY="--apply" in sys.argv
LIMIT=3
if "--limit" in sys.argv:
    _i=sys.argv.index("--limit")
    if _i+1<len(sys.argv):
        try: LIMIT=int(sys.argv[_i+1])
        except Exception: pass
UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
CTX=ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE

def sb_get(q): return json.load(urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/"+q,headers=H)))
def sb_patch(q,b): urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/"+q,data=json.dumps(b).encode(),headers={**H,"Content-Type":"application/json","Prefer":"return=minimal"},method="PATCH"))

def site_text(url):
    if not url.startswith("http"): url="https://"+url
    try:
        html=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=12,context=CTX).read(400000).decode("utf-8","ignore")
    except Exception: return ""
    html=re.sub(r"<script.*?</script>|<style.*?</style>","",html,flags=re.S|re.I)
    txt=re.sub(r"<[^>]+>"," ",html); txt=re.sub(r"\s+"," ",txt)
    return txt[:4000]

def main():
    leads=sb_get("leads?client_id=eq.eje&select=id,company,lead_data&limit=1000")
    thin=[l for l in leads if len(((l.get('lead_data') or {}).get('companyBrief') or '').strip())<120]
    print(f"{len(thin)} thin-brief leads. {'writing' if APPLY else 'previewing'} {min(LIMIT,len(thin))} via cheap lane (Gemini flash-lite)\n")
    for l in thin[:LIMIT]:
        ld=l.get("lead_data") or {}; site=ld.get("website") or ("https://"+l["id"])
        txt=site_text(site)
        if not txt: print(f"  {l['company']}: site unreachable, skip"); continue
        prompt=(f"Texto del sitio de la empresa '{l['company']}'. Escribe un brief FACTUAL de 2 a 3 frases en "
                f"espanol neutral, sin marketing, sin guiones largos: que hace, donde esta, y clientes o "
                f"especialidades notables si aparecen. Solo el brief.\n\nTEXTO:\n{txt}")
        try:
            brief=route(prompt, tier="cheap", client="eje").strip()
        except Exception as e:
            print(f"  {l['company']}: LLM error {str(e)[:60]}"); continue
        print(f"  {l['company']}:\n    {brief[:240]}\n")
        if APPLY:
            ld["companyBrief"]=brief
            sb_patch(f"leads?id=eq.{urllib.parse.quote(l['id'])}&client_id=eq.eje",{"lead_data":ld})
    print(("wrote briefs." if APPLY else "(dry run — add --apply to write)"))

if __name__=="__main__":
    main()
