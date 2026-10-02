# factory/workers/outreach.py
# Outreach playbook migration (+ future execution). backfill_runs() bridges the OLD world (the flat
# `leads` table + `messages_sent`) into the new engine (playbook_runs + engagement_events), so the
# data-driven planner has real history to operate on. DRY-RUN by default (apply=False), mirroring
# factory/migrate_leads.py. Idempotent: a lead that already has a pb_eje_default run is skipped.
#   python3 -m factory.workers.outreach [--client eje] [--apply]
import sys
from collections import defaultdict, Counter
from factory.packages import db, playbook

PB = "pb_eje_default"
# pb_eje_default: send 1 = email, send 2 = instagram_dm, send 3+ = email (collapse to step 3).
STEP_CHANNEL = {1: "email", 2: "instagram_dm", 3: "email"}
# lead.status -> (engagement run state, reply-event outcome or None)
STATUS_STATE = {
    "replied":   ("replied", "replied"),
    "loom_sent": ("replied", "replied"),
    "meeting":   ("converted", "reopened"),   # a booked meeting = the outreach goal reached
    "closed":    ("stopped", None),
    "skip":      ("stopped", None),
    "contacted": ("running", None),
    "none":      ("running", None),
}


def _step_no(i):  # i is the 1-based message index
    return i if i <= 3 else 3


def _channel(i):
    return STEP_CHANNEL.get(_step_no(i), "email")


def backfill_runs(client="eje", apply=False):
    leads = db.select_all("leads", "client_id=eq.%s&select=id,status" % client)
    status_by = {r["id"]: (r.get("status") or "none") for r in leads}
    ms = db.select_all("messages_sent", "select=lead_id,sent_at")
    by_lead = defaultdict(list)
    for m in ms:
        lid = m.get("lead_id")
        if lid in status_by:
            by_lead[lid].append(m.get("sent_at"))

    existing = {r.get("legacy_lead_id")
                for r in db.select_all("playbook_runs", "playbook_id=eq.%s&select=legacy_lead_id" % PB)}

    rep = {"client": client, "leads_with_msgs": len(by_lead), "runs_to_create": 0,
           "events_to_create": 0, "skipped_existing": 0, "run_states": Counter()}
    to_write = []
    for lid, times in by_lead.items():
        if lid in existing:
            rep["skipped_existing"] += 1
            continue
        times = sorted([t for t in times if t])
        st = status_by.get(lid, "none")
        run_state, reply_outcome = STATUS_STATE.get(st, ("running", None))
        evs = [{"event": "contacted", "channel": _channel(i), "at": t, "step_no": _step_no(i), "outcome": "none"}
               for i, t in enumerate(times, start=1)]
        if reply_outcome:
            evs.append({"event": "replied", "channel": None, "at": times[-1] if times else None,
                        "step_no": None, "outcome": reply_outcome})
        rep["runs_to_create"] += 1
        rep["events_to_create"] += len(evs)
        rep["run_states"][run_state] += 1
        to_write.append((lid, run_state, len(times), evs))

    if apply:
        created = ev_created = 0
        for lid, run_state, ntouch, evs in to_write:
            run = db.insert("playbook_runs", {
                "playbook_id": PB, "client_id": client, "legacy_lead_id": lid,
                "current_step": min(ntouch, 3), "state": run_state,
            }, returning=True)
            rid = (run[0] if isinstance(run, list) else run)["id"]
            body = [dict(e, run_id=rid, client_id=client) for e in evs]
            if body:
                db.insert("engagement_events", body)
            created += 1
            ev_created += len(body)
        rep["created_runs"] = created
        rep["created_events"] = ev_created
    rep["run_states"] = dict(rep["run_states"])
    return rep


def main():
    client = sys.argv[sys.argv.index("--client") + 1] if "--client" in sys.argv else "eje"
    apply = "--apply" in sys.argv
    print("== outreach backfill (%s) client=%s ==" % ("APPLY" if apply else "DRY-RUN", client))
    import json
    print(json.dumps(backfill_runs(client=client, apply=apply), indent=2, default=str))
    print("== done ==")


if __name__ == "__main__":
    main()
