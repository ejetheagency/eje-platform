# HYBRID report for 2uplatam, 2026-10-09: 10 universities (networking) + 10 pymes (business), fully enriched,
# approved, with per-lead email + aligned LinkedIn/WhatsApp/IG/follow-up scripts per segment.
import sys, os, json, re, urllib.request, datetime
sys.path.insert(0, "/Users/jofreeyzaguirre/claude/unabase-app")
from factory.packages import db

SP = os.path.dirname(__file__); MINE = os.path.join(SP, "mine")
CID = "2uplatam"; DAY = "2026-10-09"
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
ic = (db.select("clients", "id=eq.%s&select=icp_config" % CID)[0].get("icp_config") or {})
sender = ic.get("sender_name") or "Fernando González"
PYME_TPL = ic.get("outreach_first_touch") or ""   # has {first} {ofrecen} {sender}

def _nd(s): return (s or "").replace("—", ", ").replace("–", "-")
def dom_of(url): s=re.sub(r'^https?://(www\.)?','',(url or '').strip().lower()).split('/')[0]; return s
def slug(s): return "uni13-" + re.sub(r"[^a-z0-9]+","-",(s or "").lower()).strip("-")[:44]
def first_of(n): return (n or "").split(" ")[0] if n else ""

def load(f):
    p=os.path.join(MINE,f)
    try: return json.load(open(p)) if os.path.exists(p) else []
    except Exception as e: print("load warn",f,e); return []
pymes=load("pyme_oct13.json"); unis=load("uni_oct13.json")
print("loaded pymes=%d unis=%d"%(len(pymes),len(unis)))

def pyme_scripts(p):
    first=first_of(p.get("decisor_name")); of=(p.get("ofrecen") or "ofrecen sus servicios").strip()
    co=p.get("company") or ""
    email = PYME_TPL.replace("{first}",first).replace("{ofrecen}",of).replace("{sender}",sender).replace("Hola , ","Hola, ") if PYME_TPL else (
        "Hola %s, ¿cómo estás?\n\nTe escribo desde 2upLatam, vi que %s.\n\nConstruimos una red de trabajo y networking sin costo para emprendedores y pymes. ¿Te gustaria sumarte?\n\nSi creces tú, crecemos todos\n%s"%(first,of,sender))
    sal=("Hola %s"%first) if first else "Hola"
    return {
      "pitchEmailES": email,
      "linkedinDM": "%s, le escribo desde 2upLatam. Vi que %s. Construimos una red de networking sin costo para emprendedores y pymes y me encantaria sumar a %s. ¿Coordinamos una breve llamada?"%(sal, of, co or "tu empresa"),
      "whatsappMessage": "%s, le saludo desde 2upLatam 👋 Vi que %s. Estamos armando una red de networking sin costo para emprendedores y pymes y creo que encajarian perfecto. ¿Tendria 10 min para contarle?"%(sal, of),
      "instagramDM": "%s, le escribimos desde 2upLatam. Vimos que %s, nos encanta. Armamos una red sin costo para emprendedores y pymes, ¿le comparto como sumarse?"%(sal, of),
      "followupEmail": "%s, le reescribo por si mi mensaje anterior se traspapelo. En 2upLatam estamos sumando a emprendedores y pymes como %s a una red de networking sin costo. ¿Le interesaria una breve llamada?\n\nSi creces tú, crecemos todos\n%s"%(sal, co or "la tuya", sender),
    }

def uni_scripts(p):
    first=first_of(p.get("name")); role=(p.get("role") or "lidera su area"); u=(p.get("university") or "su universidad")
    sal=("Hola %s"%first) if first else "Hola"
    return {
      "pitchEmailES": "%s, ¿cómo está?\n\nLe escribo desde 2upLatam. Vi que es %s en %s.\n\nConstruimos una red de trabajo y networking sin costo para emprendedores y pymes, y nos encantaria conectar con sus estudiantes emprendedores y su programa, y explorar una colaboracion (charlas, mentoria, acceso a la red).\n\n¿Coordinamos una breve llamada para ver como sumar valor a sus estudiantes y a su programa?\n\nFernando González · 2upLatam"%(sal, role, u),
      "linkedinDM": "%s, le escribo desde 2upLatam. Vi que es %s en %s. Construimos una red de networking sin costo para emprendedores y pymes y me encantaria explorar una colaboracion con sus estudiantes (charlas, mentoria, acceso a la red). ¿Coordinamos una breve llamada?"%(sal, role, u),
      "whatsappMessage": "%s, le saludo desde 2upLatam. Vi su trabajo en %s y me encantaria contarle: armamos una red de networking sin costo para emprendedores y pymes, y sus estudiantes podrian sumar mucho. ¿Tendria 15 min?"%(sal, u),
      "instagramDM": "%s, le escribimos desde 2upLatam. Vimos lo que impulsan en %s. Creamos una red sin costo para emprendedores y pymes y nos encantaria colaborar con sus estudiantes. ¿Le comparto mas?"%(sal, u),
      "followupEmail": "%s, le reescribo por si mi mensaje anterior se traspapelo. En 2upLatam conectamos con universidades como %s para sumar a sus estudiantes emprendedores a nuestra red sin costo. ¿Le interesaria una breve llamada?\n\nSaludos cordiales\nFernando González · 2upLatam"%(sal, u),
    }

def chcount(d): return sum([bool(d.get("whatsapp") or d.get("whatsappMessage")),bool(d.get("instagram")),bool(d.get("linkedin") or d.get("contactLinkedIn") or d.get("company_linkedin")),bool(d.get("email") or d.get("contactEmail"))])
n=0
# PYMES (take best 10)
for p in pymes[:10]:
    web=dom_of(p.get("website") or "")
    if not web or not (p.get("decisor_name") or "").strip(): print("skip pyme",p.get("company")); continue
    sc=pyme_scripts(p); sd=p.get("second_decisor") or {}
    ld={"_key":web,"companyName":p.get("company") or web,"contactName":p.get("decisor_name"),"contactTitle":p.get("decisor_role") or "",
        "contactEmail":p.get("email") or "","country":"Ecuador","website":"https://"+web,"instagramHandle":(p.get("instagram") or "").lstrip("@"),
        "contactLinkedIn":p.get("decisor_linkedin") or "","companyLinkedIn":p.get("company_linkedin") or "","whatsapp":p.get("whatsapp") or "",
        "companyBrief":_nd(p.get("brief") or ""),"whyICP":_nd(p.get("why_now") or ""),"ofrecen":p.get("ofrecen") or "","sector":p.get("sector") or "",
        "additionalContacts":([{"title":sd.get("role","Contacto"),"name":sd["name"],"email":sd.get("email","")}] if sd.get("name") else []),
        "segment":"pyme","purpose":"networking","source_date":DAY,"approved":True,"approvedBy":"admin","approvedAt":now,"source":"hybrid_oct9"}
    ld.update(sc); ld["score"]=60+chcount(ld)*8
    base={"company":ld["companyName"],"contact_name":ld["contactName"],"contact_email":ld["contactEmail"] or None,"score":ld["score"],"source_date":DAY,"lead_data":ld,"updated_at":now}
    ex=db.select_all("leads","client_id=eq.%s&id=eq.%s&select=id"%(CID,urllib.request.quote(web,safe='')))
    if ex: print("skip existing pyme",web); continue
    if True:
        row=dict(base); row.update({"id":web,"client_id":CID,"status":"none"})
        try: db.insert("leads",row,returning=False)
        except Exception as e: print("pyme insert fail",web,str(e)[:70]); continue
    n+=1
# UNIVERSITIES (take best 10)
for p in unis[:10]:
    nm=(p.get("name") or "").strip()
    if not nm: continue
    lid=slug(nm); sc=uni_scripts(p)
    ld={"_key":lid,"companyName":p.get("university") or nm,"contactName":nm,"contactTitle":p.get("role") or "",
        "contactEmail":p.get("email") or "","country":"Ecuador","website":p.get("profile_url") or "","instagramHandle":(p.get("instagram") or "").lstrip("@"),
        "contactLinkedIn":p.get("linkedin") or "","companyLinkedIn":"","whatsapp":p.get("whatsapp") or "",
        "companyBrief":_nd(p.get("note") or ((p.get("role") or "")+" · "+(p.get("faculty_or_area") or ""))),"whyICP":_nd(p.get("note") or ""),"sector":"Universidad / Academia",
        "additionalContacts":[],"segment":"universidades","purpose":"networking","source_date":DAY,"approved":True,"approvedBy":"admin","approvedAt":now,"source":"hybrid_oct9"}
    ld.update(sc); ld["score"]=60+chcount(ld)*8
    base={"company":ld["companyName"],"contact_name":nm,"contact_email":ld["contactEmail"] or None,"score":ld["score"],"source_date":DAY,"lead_data":ld,"updated_at":now}
    ex=db.select_all("leads","client_id=eq.%s&id=eq.%s&select=id"%(CID,lid))
    if ex: print("skip existing uni",lid); continue
    if True:
        row=dict(base); row.update({"id":lid,"client_id":CID,"status":"none"})
        try: db.insert("leads",row,returning=False)
        except Exception as e: print("uni insert fail",lid,str(e)[:70]); continue
    n+=1

print("published %d hybrid leads for %s"%(n,DAY))
r=db.select_all("leads","client_id=eq.%s&source_date=eq.%s&select=lead_data"%(CID,DAY))
ap=[x for x in r if (x.get('lead_data') or {}).get('approved')]
from collections import Counter
print("Oct-9 report: %d approved | segments:%s | email:%d wa:%d ig:%d li:%d | all pitched:%s"%(
  len(ap), dict(Counter((x.get('lead_data') or {}).get('segment') for x in ap)),
  sum(1 for x in ap if x['lead_data'].get('contactEmail')), sum(1 for x in ap if x['lead_data'].get('whatsapp')),
  sum(1 for x in ap if x['lead_data'].get('instagramHandle')), sum(1 for x in ap if x['lead_data'].get('contactLinkedIn')),
  all(x['lead_data'].get('pitchEmailES') for x in ap)))
