# factory/run_nightly.py  —  THE NIGHT SHIFT. run() is callable (by the service / cron); main() is the CLI.
#   discovery -> enqueue -> drain -> reports -> ops snapshot. Idempotent, safe to run anytime.
#   python3 -m factory.run_nightly [--client <id>] [--max <N>]
import sys, json
from factory.workers import scheduler, runner, reports, admin, discovery
from factory.packages import db, queue


def run(client=None, max_leads=None):
    out = {"discovery": {}, "jobs": 0, "reports": {}}
    out["reaped"] = queue.reap()  # re-queue any jobs orphaned by a dead worker before processing
    clients = [{"id": client}] if client else db.select("clients", "select=id")
    for c in clients:
        r = discovery.discover_for_client(c["id"], max_leads=max_leads or 25)
        if r.get("ok"):
            out["discovery"][c["id"]] = r.get("created", 0)
    scheduler.tick(client_id=client)
    drained = runner.drain_concurrent(workers=4)  # concurrent workers (atomic claim) = faster nightly runs
    out["jobs"] = len(drained)
    try:  # capture inbound email replies for EJE's own outreach (agency inbox) -> engagement + learning
        from factory.workers import reply_reconcile
        out["replies_captured"] = reply_reconcile.reconcile_email(client="eje", apply=True).get("recorded", 0)
    except Exception:
        pass
    reps = reports.build_all() if not client else [reports.build(client)]
    out["reports"] = {r["client_id"]: r["count"] for r in reps}
    try:
        snap = admin.snapshot()
        out["pool"] = snap["pool"]
        out["lead_states"] = snap["lead_states"]
        out["spend_today_usd"] = snap["spend_today_usd"]
    except Exception:
        pass
    return out


def main():
    client = sys.argv[sys.argv.index("--client") + 1] if "--client" in sys.argv else None
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else None
    print("== EJE factory night shift ==")
    print(json.dumps(run(client=client, max_leads=mx), indent=2))
    print("== done ==")


if __name__ == "__main__":
    main()
