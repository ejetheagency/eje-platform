# Publish the Universidades segment as 2uplatam's report for TOMORROW (2026-10-08), approved + networking pitch.
import sys, os, json, re, urllib.request, datetime
sys.path.insert(0, "/Users/jofreeyzaguirre/claude/unabase-app")
from factory.packages import db

SP = os.path.dirname(__file__); MINE = os.path.join(SP, "mine")
CID = "2uplatam"; DAY = "2026-10-08"
now = datetime.datetime.now(datetime.timezone.utc).isoformat()

people = json.load(open(os.path.join(MINE, "uni_ecuador_enriched.json")))
extra_p = os.path.join(MINE, "uni_extra.json")
if os.path.exists(extra_p):
    try: people += json.load(open(extra_p))
    except Exception as e: print("extra load warn", e)

try: PIT = json.load(open(os.path.join(SP, "uni_pitches.json")))
except Exception: PIT = {}
PIT = {k: v.replace("—", ", ").replace("–", "-") for k, v in PIT.items()}

def _nd(s): return (s or "").replace("—", ", ").replace("–", "-")
def slug(s): return "uni-" + re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:46]
def fallback_pitch(p):
    first = (p.get("name") or "").split(" ")[0]
    role = p.get("role") or "su rol"; uni = p.get("university") or "su universidad"
    return ("Hola %s, ¿cómo está?\n\nLe escribo desde 2upLatam. Vi que %s en %s.\n\n"
            "Construimos una red de trabajo y networking sin costo para emprendedores y pymes, y nos encantaria conectar con sus estudiantes emprendedores y su programa, y explorar una colaboracion (charlas, mentoria, acceso a la red para sus emprendedores).\n\n"
            "¿Coordinamos una breve llamada para ver como sumar valor a sus estudiantes y a su programa?\n\n"
            "Fernando González · 2upLatam" % (first or "", (p.get("role") or "lidera su area").lower(), uni))

def rich(p):
    s = 60
    if p.get("email"): s += 14
    if p.get("linkedin"): s += 12
    if p.get("whatsapp"): s += 6
    if p.get("note"): s += 3
    return min(s, 99)

# dedupe by name, require a name, rank by richness, take 20
seen = set(); cand = []
for p in people:
    nm = (p.get("name") or "").strip()
    if not nm or nm.lower() in seen: continue
    seen.add(nm.lower()); cand.append(p)
cand.sort(key=rich, reverse=True)
use = cand[:20]
print("university candidates: %d | publishing: %d" % (len(cand), len(use)))

n = 0
for p in use:
    lid = slug(p.get("name"))
    uni = p.get("university") or ""; fac = p.get("faculty_or_area") or ""
    note = _nd(p.get("note") or ((p.get("role") or "") + (" · " + fac if fac else "")))
    ld = {
        "_key": lid, "companyName": uni or (p.get("name")), "contactName": p.get("name"),
        "contactTitle": p.get("role") or "", "contactEmail": p.get("email") or "",
        "country": "Ecuador", "website": p.get("profile_url") or "",
        "instagramHandle": (p.get("instagram") or "").lstrip("@"),
        "contactLinkedIn": p.get("linkedin") or "", "whatsapp": p.get("whatsapp") or "",
        "companyBrief": note, "pitchEmailES": PIT.get(p.get("name")) or fallback_pitch(p),
        "whyICP": _nd(p.get("note") or ""), "sector": "Universidad / Academia",
        "score": rich(p), "additionalContacts": [], "segment": "universidades",
        "source_date": DAY, "approved": True, "approvedBy": "admin", "approvedAt": now, "source": "uni_segment",
    }
    base = {"company": uni or p.get("name"), "contact_name": p.get("name"),
            "contact_email": p.get("email") or None, "score": rich(p), "source_date": DAY, "lead_data": ld, "updated_at": now}
    ex = db.select_all("leads", "client_id=eq.%s&id=eq.%s&select=id" % (CID, lid))
    if ex: db.update("leads", "id=eq.%s&client_id=eq.%s" % (lid, CID), base)
    else:
        row = dict(base); row.update({"id": lid, "client_id": CID, "status": "none"})
        try: db.insert("leads", row, returning=False)
        except Exception as e: print("insert fail", lid, str(e)[:80])
    n += 1

print("published %d university leads for %s" % (n, DAY))
# verify
r = db.select_all("leads", "client_id=eq.%s&source_date=eq.%s&select=company,contact_name,lead_data" % (CID, DAY))
ap = [x for x in r if (x.get('lead_data') or {}).get('approved') and (x.get('lead_data') or {}).get('segment')=='universidades']
em = sum(1 for x in ap if x.get('lead_data',{}).get('contactEmail'))
li = sum(1 for x in ap if x.get('lead_data',{}).get('contactLinkedIn'))
wa = sum(1 for x in ap if x.get('lead_data',{}).get('whatsapp'))
pit = all(x.get('lead_data',{}).get('pitchEmailES') for x in ap)
print("Oct-8 university report: %d approved | email:%d linkedin:%d whatsapp:%d | all pitched:%s" % (len(ap), em, li, wa, pit))
