# factory/workers/reply_reconcile.py
# Email reply capture (the moat input that needs NO Meta). Reads the agency inbox over IMAP, finds
# inbound mail whose sender matches a known lead, and records it as an engagement_event (outcome=replied)
# linked to that lead's playbook_run, flipping the run to 'replied'. Feeds the learning loop + the cadence.
# DRY-RUN by default (apply=False). Creds: ~/claude/eje-leads/.env (EJE_WORK_EMAIL / EJE_WORK_APP_PW).
#   python3 -m factory.workers.reply_reconcile [--client eje] [--since 120] [--apply]
import imaplib, email, email.utils, os, datetime, sys
from factory.packages import db


def _env():
    # Prefer environment variables (so it works on Railway); fall back to the local eje-leads/.env file.
    if os.environ.get("EJE_WORK_EMAIL") and os.environ.get("EJE_WORK_APP_PW"):
        return {"EJE_WORK_EMAIL": os.environ["EJE_WORK_EMAIL"], "EJE_WORK_APP_PW": os.environ["EJE_WORK_APP_PW"]}
    e = {}
    p = os.path.expanduser("~/claude/eje-leads/.env")
    if os.path.exists(p):
        for l in open(p):
            l = l.strip()
            if "=" in l and not l.startswith("#"):
                k, v = l.split("=", 1)
                e[k] = v
    return e


def _addr(frm):
    return (email.utils.parseaddr(frm or "")[1] or "").lower().strip()


def reconcile_email(client="eje", since_days=120, apply=False):
    # lead email -> lead id
    leads = db.select_all("leads", "client_id=eq.%s&select=id,contact_email,lead_data" % client)
    email2lead = {}
    for r in leads:
        ce = (r.get("contact_email") or (r.get("lead_data") or {}).get("contactEmail") or "").lower().strip()
        if ce:
            email2lead[ce] = r["id"]
    # run per lead (to link the reply) + existing replied runs (dedup)
    runs = db.select_all("playbook_runs", "client_id=eq.%s&select=id,legacy_lead_id,state" % client)
    run_by_lead = {r["legacy_lead_id"]: r for r in runs if r.get("legacy_lead_id")}
    existing = db.select_all("engagement_events", "client_id=eq.%s&outcome=eq.replied&select=run_id" % client)
    replied_runs = {e["run_id"] for e in existing if e.get("run_id")}

    env = _env()
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(env["EJE_WORK_EMAIL"], env["EJE_WORK_APP_PW"])
    M.select("INBOX", readonly=True)
    since = (datetime.date.today() - datetime.timedelta(days=since_days)).strftime("%d-%b-%Y")

    rep = {"client": client, "inbox_since": since, "lead_emails": len(email2lead),
           "lead_repliers": 0, "new_to_record": 0, "samples": []}
    to_write = []
    # Server-side: ask the inbox for mail FROM each lead's address (fast), instead of pulling every header.
    for ce, lead_id in email2lead.items():
        typ, data = M.search(None, '(FROM "%s" SINCE %s)' % (ce, since))
        mids = data[0].split() if data and data[0] else []
        if not mids:
            continue
        rep["lead_repliers"] += 1
        run = run_by_lead.get(lead_id)
        rid = run["id"] if run else None
        if rid and rid in replied_runs:
            continue  # already captured
        t, hd = M.fetch(mids[-1], "(BODY.PEEK[HEADER.FIELDS (DATE SUBJECT MESSAGE-ID)])")  # most recent reply
        hdr = email.message_from_bytes(hd[0][1]) if hd and hd[0] else email.message_from_string("")
        try:
            at = email.utils.parsedate_to_datetime(hdr.get("Date")).isoformat()
        except Exception:
            at = None
        rep["new_to_record"] += 1
        if len(rep["samples"]) < 10:
            rep["samples"].append({"from": ce, "subject": (hdr.get("Subject") or "")[:48], "linked_run": bool(rid)})
        to_write.append((client, rid, run, at, ce, hdr.get("Subject"), hdr.get("Message-ID")))
    M.logout()

    if apply:
        from factory.packages import engagement
        for (cl, rid, run, at, frm, subj, mid) in to_write:
            db.insert("engagement_events", {
                "client_id": cl, "event": "replied", "channel": "email", "outcome": "replied",
                "run_id": rid, "at": at,
                "meta": {"from": frm, "subject": (subj or "")[:140], "msg_id": mid, "source": "reply_reconcile"},
            })
            if rid and run and run.get("state") == "running":
                try:
                    engagement.move(rid, "replied")
                except Exception:
                    pass
        rep["recorded"] = len(to_write)
    return rep


def main():
    apply = "--apply" in sys.argv
    client = sys.argv[sys.argv.index("--client") + 1] if "--client" in sys.argv else "eje"
    since = int(sys.argv[sys.argv.index("--since") + 1]) if "--since" in sys.argv else 120
    import json
    print("== reply reconcile (%s) ==" % ("APPLY" if apply else "DRY-RUN"))
    print(json.dumps(reconcile_email(client=client, since_days=since, apply=apply), indent=2, default=str))


if __name__ == "__main__":
    main()
