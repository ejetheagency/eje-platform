#!/usr/bin/env python3
# scripts/orchestrator.py
#
# THE DAILY ORCHESTRATOR (Phase 3). Config-driven, per-client, autonomous.
# Loops every active client config and runs their pipeline against THEIR settings + the gate.
# Adding a client = adding a config file, not touching this code (built for hundreds).
#
# COST NOTE: this engine is 100% DETERMINISTIC. Gate = code. Draft = template interpolation.
# Reconcile = IMAP + DB. ZERO LLM calls. The only expensive stage (sourcing/enriching NEW leads)
# is separate and routed through the cheap-LLM lane / Lead Library, never this loop.
#
#   python3 scripts/orchestrator.py            # DRY RUN — per-client plan, writes nothing
#   python3 scripts/orchestrator.py --apply     # enforce gate + reconcile + create drafts
#
# Reads config/*.json (active clients). Operates on the live (prod) leads for each client_id.

import json, sys, os, re, glob, imaplib, email, email.message, time, datetime, urllib.request, urllib.parse
from collections import Counter

SB  = "https://ogdsuztzhmnnjolilsuo.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZHN1enR6aG1ubmpvbGlsc3VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMDI0MDMsImV4cCI6MjA5MTc3ODQwM30.9iKhJJWd_zg6WfdxTR9ojK4DVLR3e-bLdPXY-0uDp7Q"
H   = {"apikey": KEY, "Authorization": "Bearer " + KEY}
APPLY = "--apply" in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERIC = {"info","contacto","hola","hello","mail","office","proyectos","ventas","equipo","team","contact","studio","estudio","agencia"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def sb_get(q): return json.load(urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/"+q, headers=H)))
def sb_post(t,b): urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/"+t, data=json.dumps(b).encode(), headers={**H,"Content-Type":"application/json","Prefer":"return=minimal"}, method="POST"))
def sb_patch(q,b): urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/"+q, data=json.dumps(b).encode(), headers={**H,"Content-Type":"application/json","Prefer":"return=minimal"}, method="PATCH"))

def load_env(path):
    e={}
    for l in open(os.path.expanduser(path)):
        l=l.strip()
        if "=" in l and not l.startswith("#"): k,v=l.split("=",1); e[k]=v
    return e

def named(n):
    if not n: return False
    p=[x for x in re.split(r"\s+",n.strip()) if x]
    return len(p)>=2 and p[0].lower() not in GENERIC

# ── STAGE 1: gate (deterministic) ──
def stage_gate(cid, gcfg):
    leads=sb_get(f"leads?client_id=eq.{cid}&select=id,company,contact_name,contact_email,score,lead_data&limit=1000")
    npass=0; held=0
    for l in leads:
        ld=l.get("lead_data") or {}; hard=[]
        if not (ld.get("companyName") or l.get("company")): hard.append("no company")
        if gcfg.get("require_named_decisor") and not named(ld.get("contactName") or l.get("contact_name")): hard.append("no decisor")
        em=(ld.get("contactEmail") or l.get("contact_email") or "").strip()
        if gcfg.get("require_valid_email") and not EMAIL_RE.match(em): hard.append("no email")
        if gcfg.get("require_channel") and not (ld.get("instagramHandle") or ld.get("contactLinkedIn")): hard.append("no channel")
        ok=not hard
        if ok: npass+=1
        else: held+=1
        if APPLY:
            ld["readyToSend"]=ok; ld["_holdReason"]="; ".join(hard)
            sb_patch(f"leads?id=eq.{urllib.parse.quote(l['id'])}&client_id=eq.{cid}", {"lead_data":ld})
    return npass, held

# ── STAGE 2: reconcile yesterday's sends (deterministic: IMAP + DB) ──
def imap_connect(outbox):
    e=load_env(outbox["env_file"]); p=outbox["env_prefix"]
    M=imaplib.IMAP4_SSL("imap.gmail.com"); M.login(e[p+"_EMAIL"], e[p+"_APP_PW"])
    return M, e[p+"_EMAIL"]

def stage_reconcile(cid, outbox):
    leads=sb_get(f"leads?client_id=eq.{cid}&status=eq.none&select=id,company,lead_data")
    if not leads: return 0
    M,_=imap_connect(outbox)
    typ,data=M.list(); sent='"[Gmail]/Sent Mail"'
    for line in data or []:
        s=line.decode(errors="ignore")
        if "\\Sent" in s: sent=s.split(' "/" ')[-1].strip(); break
    M.select(sent, readonly=True); marked=0
    for l in leads:
        tok="".join(c for c in l["company"] if ord(c)<128).strip() or l["company"]
        try: t,d=M.search(None,"SUBJECT",'"%s x EJE"'%tok)
        except Exception: continue
        ids=d[0].split() if d and d[0] else []
        if not ids: continue
        t,md=M.fetch(ids[-1],"(BODY[HEADER.FIELDS (DATE)])"); m=re.search(r"Date:\s*(.+)", md[0][1].decode(errors="ignore"))
        ts=email.utils.parsedate_to_datetime(m.group(1).strip()).isoformat() if m else datetime.datetime.utcnow().isoformat()
        marked+=1
        if APPLY:
            sb_post("messages_sent", {"lead_id":l["id"],"user_name":outbox.get("user_name","operator"),"channel":"email","message_text":(l.get("lead_data") or {}).get("pitchEmailES",""),"sent_at":ts,"client_id":cid})
            sb_patch(f"leads?id=eq.{urllib.parse.quote(l['id'])}&client_id=eq.{cid}", {"status":"contacted"})
    M.logout(); return marked

# ── STAGE 3: draft today's due first-touches (deterministic: template + IMAP) ──
def stage_draft(cid, outbox):
    today=datetime.datetime.utcnow().strftime("%Y-%m-%d")
    leads=sb_get(f"leads?client_id=eq.{cid}&status=eq.none&source_date=eq.{today}&select=id,company,contact_email,lead_data")
    due=[l for l in leads if (l.get("lead_data") or {}).get("readyToSend") and (l.get("contact_email") or (l.get('lead_data') or {}).get('contactEmail'))]
    if not APPLY: return len(due), [l["company"] for l in due[:6]]
    M,frm=imap_connect(outbox)
    typ,data=M.list(); drafts="[Gmail]/Drafts"
    for line in data or []:
        s=line.decode(errors="ignore")
        if "\\Drafts" in s: drafts=s.split(' "/" ')[-1].strip().strip('"'); break
    n=0
    for l in due:
        ld=l.get("lead_data") or {}; to=l.get("contact_email") or ld.get("contactEmail")
        subj=ld.get("subject") or (l["company"]+" x EJE"); body=ld.get("pitchEmailES") or ""
        if not (to and body): continue
        msg=email.message.EmailMessage(); msg["From"]=frm; msg["To"]=to; msg["Subject"]=subj; msg.set_content(body)
        M.append(drafts, "(\\Draft)", imaplib.Time2Internaldate(time.time()), msg.as_bytes()); n+=1
    M.logout(); return n, [l["company"] for l in due[:6]]

def main():
    print(("APPLY" if APPLY else "DRY RUN")+" — daily orchestrator (deterministic, $0 LLM)\n")
    cfgs=[json.load(open(f)) for f in sorted(glob.glob(os.path.join(ROOT,"config","*.json")))]
    cfgs=[c for c in cfgs if c.get("active")]
    print(f"active clients: {len(cfgs)}\n")
    for c in cfgs:
        cid=c["client_id"]; print(f"── {c.get('name',cid)} ({cid}) ──")
        p,h=stage_gate(cid, c.get("gate",{}))
        print(f"   gate:      {p} shippable, {h} held")
        try:
            rc=stage_reconcile(cid, c["outbox"]); print(f"   reconcile: {'marked' if APPLY else 'would mark'} {rc} sent lead(s)")
        except Exception as e: print(f"   reconcile: skipped ({str(e)[:50]})")
        try:
            dr=stage_draft(cid, c["outbox"]); n=dr[0] if isinstance(dr,tuple) else dr; names=dr[1] if isinstance(dr,tuple) else []
            print(f"   draft:     {'drafted' if APPLY else 'would draft'} {n} email(s) for today  {names}")
        except Exception as e: print(f"   draft:     skipped ({str(e)[:50]})")
        print()
    print("done." + ("" if APPLY else "  Re-run with --apply to enforce + draft."))

if __name__ == "__main__":
    main()
