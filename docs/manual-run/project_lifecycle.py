# Project every 2uplatam lead's full lifecycle + day-by-day forecast + problems. Matches the WhatsApp-FORWARD
# non-EJE cadence: t1 email d0, t2 WhatsApp +2, t3 IG +4, t4 email +7, t5 LinkedIn +5, monthly +30.
# resolveCh (non-EJE): each non-email touch prefers WhatsApp, then the others, then email.
import sys, os, json, datetime
sys.path.insert(0, "/Users/jofreeyzaguirre/claude/unabase-app")
from factory.packages import db
CID="2uplatam"
rows=db.select_all("leads","client_id=eq.%s&select=id,company,source_date,lead_data"%CID)
leads=[x for x in rows if (x.get('lead_data') or {}).get('approved') and (x.get('source_date') or '')>='2026-10-08']
DAYS=sorted(set(x["source_date"] for x in leads))
# cumulative day-offset from the send date + nominal channel
SEQ=[(1,"email",0),(2,"whatsapp",2),(3,"ig",6),(4,"email",13),(5,"linkedin",18),(6,"mensual",48)]
def resolve(ch, ig, li, wa):
    if ch=="whatsapp": return "whatsapp" if wa else ("instagram" if ig else ("linkedin" if li else "email"))
    if ch=="ig": return "instagram" if ig else ("whatsapp" if wa else ("linkedin" if li else "email"))
    if ch=="linkedin": return "linkedin" if li else ("whatsapp" if wa else "email")
    return "email"
routes=[]; cal={}; prob={"pure_email":[], "wa_reach":0, "fallback_email":0}
for x in leads:
    ld=x.get("lead_data") or {}
    ig=bool(ld.get("instagramHandle")); li=bool(ld.get("contactLinkedIn") or ld.get("companyLinkedIn")); wa=bool(ld.get("whatsapp"))
    sd=datetime.date.fromisoformat(x["source_date"]); touches=[]; onwa=False
    for (tn,nom,off) in SEQ:
        rc=resolve(nom, ig, li, wa); dt=(sd+datetime.timedelta(days=off)).isoformat()
        touches.append({"t":tn,"nominal":nom,"channel":rc,"date":dt})
        cal.setdefault(dt,{}); cal[dt][rc]=cal[dt].get(rc,0)+1
        if rc=="whatsapp": onwa=True
    if onwa: prob["wa_reach"]+=1
    if not any(t["channel"]!="email" for t in touches[1:]): prob["pure_email"].append(ld.get("companyName") or x.get("company"))
    prob["fallback_email"]+=sum(1 for t in touches if t["t"] in (2,3,5) and t["channel"]=="email")
    routes.append({"company":ld.get("companyName") or x.get("company"),"contact":ld.get("contactName"),
        "segment":ld.get("segment") or "biz","send_date":x["source_date"],
        "has":{"ig":ig,"li":li,"wa":wa,"email":bool(ld.get("contactEmail"))},"touches":touches})
out={"reports":DAYS,"n_leads":len(leads),"routes":routes,"calendar":cal,"problems":prob}
json.dump(out, open(os.path.join(os.path.dirname(__file__),"projection.json"),"w"), ensure_ascii=False, indent=1)
print("=== PROJECTION (WhatsApp-forward) · %d leads · reports %s ==="%(len(leads),DAYS))
print("WhatsApp now reaches %d/%d leads in the route"%(prob["wa_reach"],len(leads)))
print("pure-email leads (no wa/ig/li):",len(prob["pure_email"]))
print("touches that still fall to email:",prob["fallback_email"])
for d in sorted(cal):
    c=cal[d]; print("  %s: %2d  (email %d · WA %d · IG %d · LI %d)"%(d,sum(c.values()),c.get('email',0),c.get('whatsapp',0),c.get('instagram',0),c.get('linkedin',0)))
