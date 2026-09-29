#!/usr/bin/env python3
# scripts/reconcile-sends.py
#
# THE SEND-DRIFT FIX (Phase 3). Sends made via Gmail Schedule Send never tell the platform,
# so leads sit at status=none while the email already went out. This reconciles the truth:
# reads the contact@ Sent folder, matches "[Company] x EJE" first-touch emails to EJE leads,
# and ADDITIVELY logs messages_sent + marks contacted at the REAL send time. Never deletes.
#
#   python3 scripts/reconcile-sends.py            # DRY RUN — shows what it would mark
#   python3 scripts/reconcile-sends.py --apply     # write the marks to the platform
#
# Designed to become a scheduled job (daily) so no human ever reconciles again.
# Creds: contact@ IMAP in ~/claude/eje-leads/.env ; Supabase anon key below (prod).

import imaplib, email, json, os, sys, re, datetime, urllib.request, urllib.parse

SB  = "https://ogdsuztzhmnnjolilsuo.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZHN1enR6aG1ubmpvbGlsc3VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMDI0MDMsImV4cCI6MjA5MTc3ODQwM30.9iKhJJWd_zg6WfdxTR9ojK4DVLR3e-bLdPXY-0uDp7Q"
H   = {"apikey": KEY, "Authorization": "Bearer " + KEY}
APPLY = "--apply" in sys.argv
ENV_PATH = os.path.expanduser("~/claude/eje-leads/.env")

def env():
    e = {}
    for l in open(ENV_PATH):
        l = l.strip()
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1); e[k] = v
    return e

def sb_get(q):
    return json.load(urllib.request.urlopen(urllib.request.Request(SB + "/rest/v1/" + q, headers=H)))

def sb_post(table, body):
    r = urllib.request.Request(SB + "/rest/v1/" + table, data=json.dumps(body).encode(),
                               headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"}, method="POST")
    urllib.request.urlopen(r)

def sb_patch(q, body):
    r = urllib.request.Request(SB + "/rest/v1/" + q, data=json.dumps(body).encode(),
                               headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(r)

def imap_sent():
    e = env()
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(e["EJE_WORK_EMAIL"], e["EJE_WORK_APP_PW"])
    typ, data = M.list(); sent = '"[Gmail]/Sent Mail"'
    for line in data or []:
        s = line.decode(errors="ignore")
        if "\\Sent" in s: sent = s.split(' "/" ')[-1].strip(); break
    M.select(sent, readonly=True)
    return M

def find_sent(M, token):
    # ASCII-safe substring search of the subject; returns the most recent send date or None
    try:
        typ, d = M.search(None, "SUBJECT", '"%s x EJE"' % token)
    except Exception:
        return None
    ids = d[0].split() if d and d[0] else []
    if not ids:
        return None
    t, md = M.fetch(ids[-1], "(BODY[HEADER.FIELDS (DATE)])")
    raw = md[0][1].decode(errors="ignore")
    m = re.search(r"Date:\s*(.+)", raw)
    if not m:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(m.group(1).strip())
        return dt.isoformat()
    except Exception:
        return None

def ascii_token(company):
    # ASCII-safe distinctive token (IMAP subject search chokes on accents)
    t = "".join(c for c in company if ord(c) < 128).strip()
    return t or company

def main():
    print(("APPLY" if APPLY else "DRY RUN") + " — reconciling Gmail sends -> platform (EJE, additive)\n")
    leads = sb_get("leads?client_id=eq.eje&status=eq.none&select=id,company,source_date,lead_data")
    if not leads:
        print("no status=none EJE leads to check."); return
    M = imap_sent()
    marked = 0
    for l in leads:
        token = ascii_token(l["company"])
        sent_iso = find_sent(M, token)
        if not sent_iso:
            continue
        pitch = (l.get("lead_data") or {}).get("pitchEmailES", "")
        print(f"  SENT  {l['company']:24} on {sent_iso[:10]}  ->  will mark contacted")
        if APPLY:
            sb_post("messages_sent", {"lead_id": l["id"], "user_name": "emiliano", "channel": "email",
                                      "message_text": pitch, "sent_at": sent_iso, "client_id": "eje"})
            try:
                sb_post("actions", {"lead_id": l["id"], "user_name": "emiliano", "channel": "email",
                                    "completed": True, "completed_at": sent_iso, "client_id": "eje"})
            except Exception:
                pass
            sb_patch(f"leads?id=eq.{urllib.parse.quote(l['id'])}&client_id=eq.eje", {"status": "contacted"})
        marked += 1
    M.logout()
    print(f"\n{'marked' if APPLY else 'would mark'} {marked} lead(s). "
          + ("" if APPLY else "Re-run with --apply to write."))

if __name__ == "__main__":
    main()
