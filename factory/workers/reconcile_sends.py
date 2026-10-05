# factory/workers/reconcile_sends.py
# OUTBOUND reconcile (the mirror of reply_reconcile): reads the agency Sent folder over IMAP and logs any email
# the operator sent to a known lead that is NOT already in messages_sent. This keeps the task queue TRUE even when
# he sends from his own inbox -- including the FIRST email (which he never logs) and any chat-drafted email we create.
# Matches by RECIPIENT address (robust, subject-independent). Dedups by (lead, day) so it never double-logs the
# in-app sends (channel=email). Uses the factory db = SERVICE key, so RLS does not silently blank it (the bug that
# made the old anon-key scripts/reconcile-sends.py a no-op). EJE-only by default. DRY-RUN unless apply=True.
#   python3 -m factory.workers.reconcile_sends [--client eje] [--since 60] [--apply]
import imaplib, email, email.utils, os, sys, datetime
from factory.packages import db

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _env():
    if os.environ.get("EJE_WORK_EMAIL") and os.environ.get("EJE_WORK_APP_PW"):
        return {"EJE_WORK_EMAIL": os.environ["EJE_WORK_EMAIL"], "EJE_WORK_APP_PW": os.environ["EJE_WORK_APP_PW"]}
    e = {}
    p = os.path.expanduser("~/claude/eje-leads/.env")
    if os.path.exists(p):
        for l in open(p):
            l = l.strip()
            if "=" in l and not l.startswith("#"):
                k, v = l.split("=", 1)
                e[k] = v.strip().strip('"').strip("'")
    return e


def _sent_folder(M):
    folder = '"[Gmail]/Sent Mail"'
    for line in (M.list()[1] or []):
        s = line.decode(errors="ignore")
        if "\\Sent" in s:
            folder = s.split(' "/" ')[-1].strip()
            break
    return folder


def reconcile(client="eje", since_days=60, apply=False):
    leads = db.select_all("leads", "client_id=eq.%s&select=id,contact_email,status,lead_data" % client)
    email2lead = {}
    for r in leads:
        ce = (r.get("contact_email") or (r.get("lead_data") or {}).get("contactEmail") or "").lower().strip()
        if ce:
            email2lead[ce] = r["id"]
    status_by_lead = {r["id"]: (r.get("status") or "none") for r in leads}
    # existing EMAIL touches -> (lead_id, YYYY-MM-DD) so we never double-log in-app or prior-reconciled sends
    seen = set()
    for m in db.select_all("messages_sent", "client_id=eq.%s&channel=eq.email&select=lead_id,sent_at" % client):
        d = (m.get("sent_at") or "")[:10]
        if m.get("lead_id") and d:
            seen.add((str(m["lead_id"]), d))

    env = _env()
    if not env.get("EJE_WORK_EMAIL"):
        return {"error": "no mailbox creds", "recorded": 0}
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(env["EJE_WORK_EMAIL"], env["EJE_WORK_APP_PW"])
    M.select(_sent_folder(M), readonly=True)
    since = datetime.date.today() - datetime.timedelta(days=since_days)
    since_str = "%02d-%s-%d" % (since.day, MONTHS[since.month - 1], since.year)
    typ, data = M.search(None, "SINCE", since_str)
    ids = data[0].split() if data and data[0] else []
    recorded = 0
    for num in ids:
        t, d = M.fetch(num, "(BODY.PEEK[HEADER.FIELDS (TO CC DATE)])")
        if not (d and d[0] and d[0][1]):
            continue
        hdr = email.message_from_bytes(d[0][1])
        recips = [a.lower().strip() for _, a in email.utils.getaddresses([hdr.get("To", ""), hdr.get("Cc", "")]) if a]
        try:
            dt = email.utils.parsedate_to_datetime(hdr.get("Date", ""))
            iso = dt.isoformat()
            day = iso[:10]
        except Exception:
            continue
        for addr in recips:
            lead = email2lead.get(addr)
            if not lead:
                continue
            key = (str(lead), day)
            if key in seen:
                continue
            seen.add(key)
            if apply:
                try:
                    db.insert("messages_sent", {"lead_id": lead, "user_name": "emiliano", "channel": "email",
                                                "message_text": "", "sent_at": iso, "client_id": client}, returning=False)
                    if status_by_lead.get(lead, "none") in ("none", "", None):
                        db.update("leads", "id=eq.%s&client_id=eq.%s" % (lead, client), {"status": "contacted"})
                        status_by_lead[lead] = "contacted"
                except Exception:
                    continue
            recorded += 1
    M.logout()
    return {"client": client, "recorded": recorded, "applied": apply}


def main():
    client = sys.argv[sys.argv.index("--client") + 1] if "--client" in sys.argv else "eje"
    since = int(sys.argv[sys.argv.index("--since") + 1]) if "--since" in sys.argv else 60
    apply = "--apply" in sys.argv
    print(("APPLY" if apply else "DRY RUN") + " outbound reconcile (%s, since %dd)" % (client, since))
    print(reconcile(client=client, since_days=since, apply=apply))


if __name__ == "__main__":
    main()
