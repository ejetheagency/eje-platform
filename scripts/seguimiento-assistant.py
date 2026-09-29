#!/usr/bin/env python3
# scripts/seguimiento-assistant.py
#
# THE SEGUIMIENTO ASSISTANT (core). A client pastes a thread / notes / a voice-memo transcript about a
# lead that did NOT come from EJE's sourcing; the cheap LLM (Gemini flash-lite, ~$0) structures it into a
# real tracked_lead and files it, plus a summary note and a recommended next move. No manual field-plugging.
#
#   python3 scripts/seguimiento-assistant.py "Hablé con Carla de Nebula Studio ..."   # DRY: show structured lead
#   echo "long thread..." | python3 scripts/seguimiento-assistant.py --apply           # structure + LOG to Seguimiento
#
# This is the beta of the live assistant: it DOES the work (log + remind), it doesn't just answer.

import os, sys, json, re, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_router import route

SB="https://ogdsuztzhmnnjolilsuo.supabase.co"
KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZHN1enR6aG1ubmpvbGlsc3VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMDI0MDMsImV4cCI6MjA5MTc3ODQwM30.9iKhJJWd_zg6WfdxTR9ojK4DVLR3e-bLdPXY-0uDp7Q"
H={"apikey":KEY,"Authorization":"Bearer "+KEY,"Content-Type":"application/json"}
APPLY="--apply" in sys.argv
CLIENT="eje"  # per-client in production; the assistant writes into THIS client's Seguimiento
STAGES={"nuevo","contactado","respondio","conversacion","reunion","propuesta","ganado","perdido","pausa"}
SOURCES={"referral","inbound","event","manual","ad_ig","ad_meta","other"}

def sb_post(t,b,ret=False):
    r=urllib.request.Request(SB+"/rest/v1/"+t,data=json.dumps(b).encode(),
        headers={**H,"Prefer":"return=representation" if ret else "return=minimal"},method="POST")
    out=urllib.request.urlopen(r); return json.load(out) if ret else None

def structure(text):
    prompt=("Del siguiente texto (un hilo, notas o transcripción de una nota de voz sobre un posible cliente), "
        "extrae la info del lead. Responde SOLO con JSON valido, sin markdown, con estas claves exactas:\n"
        '{"company":..,"decisor_name":..,"contact_email":..,"contact_phone":..,"instagram":(handle sin @ o null),'
        '"linkedin":(url o null),"source":("referral"|"inbound"|"event"|"manual"|"ad_ig"|"ad_meta"|"other"),'
        '"stage":("nuevo"|"contactado"|"respondio"|"conversacion"|"reunion"|"propuesta"|"ganado"|"perdido"|"pausa"),'
        '"summary":(2-3 frases en espanol: quien es + estado de la relacion, sin guiones largos),'
        '"next_action":(un proximo paso concreto recomendado en espanol)}\n'
        "Usa null para lo que no aparezca. TEXTO:\n"+text)
    raw=route(prompt, tier="cheap", client=CLIENT).strip()
    raw=re.sub(r"^```(json)?|```$","",raw.strip(),flags=re.M).strip()
    m=re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0) if m else raw)

def main():
    args=[a for a in sys.argv[1:] if not a.startswith("--")]
    text=" ".join(args) if args else sys.stdin.read()
    if not text.strip():
        print("usage: seguimiento-assistant.py \"<paste text>\" [--apply]  (or pipe via stdin)"); return
    d=structure(text)
    # sanitize
    d["stage"]=d.get("stage") if d.get("stage") in STAGES else "nuevo"
    d["source"]=d.get("source") if d.get("source") in SOURCES else "manual"
    print("── assistant structured this lead (cheap lane) ──")
    for k in ["company","decisor_name","contact_email","contact_phone","instagram","linkedin","source","stage"]:
        print(f"  {k:15} {d.get(k)}")
    print(f"  summary        {d.get('summary')}")
    print(f"  NEXT ACTION -> {d.get('next_action')}")
    if not APPLY:
        print("\n(dry run — add --apply to file it into Seguimiento)"); return
    row=sb_post("tracked_leads",{"client_id":CLIENT,"user_name":"emiliano","company":d.get("company") or "(sin nombre)",
        "decisor_name":d.get("decisor_name"),"contact_email":d.get("contact_email"),"contact_phone":d.get("contact_phone"),
        "instagram":d.get("instagram"),"linkedin":d.get("linkedin"),"source":d["source"],"stage":d["stage"]}, ret=True)[0]
    note=(d.get("summary") or "")+"\n\nPROXIMO PASO (asistente): "+(d.get("next_action") or "")
    sb_post("tracked_lead_notes",{"tracked_lead_id":row["id"],"client_id":CLIENT,"user_name":"emiliano",
        "note_text":note,"stage_at_time":d["stage"]})
    print(f"\nFILED to Seguimiento -> {row['company']} ({d['stage']}), with summary + recommended next step.")

if __name__=="__main__":
    main()
