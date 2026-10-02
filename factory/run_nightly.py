# factory/run_nightly.py  —  THE NIGHT SHIFT. One command the cron (D0) calls each night:
#   1. scheduler.tick()   enqueue the next job per lead state (per active client)
#   2. runner.drain()     work the queue: enrich -> score -> gates -> READY (retry + dead-letter)
#   3. reports.build_all() precompute each client's report (app reads this, never computes)
#   4. admin.snapshot()   ops health (queue, states, spend, gate pass rates, replies-per-100)
# Safe to run anytime: it's idempotent and no-ops cleanly when there's nothing to do.
# Run:  python3 -m factory.run_nightly        (add --client <id> to scope the tick)
import sys, json
from factory.workers import scheduler, runner, reports, admin


def main():
    client = None
    if "--client" in sys.argv:
        client = sys.argv[sys.argv.index("--client") + 1]

    print("== EJE factory night shift ==")
    tick = scheduler.tick(client_id=client)
    print("1. scheduler:", tick)

    drained = runner.drain()
    by = {}
    for d in drained:
        k = (d["type"], "ok" if d["ok"] else "fail")
        by[k] = by.get(k, 0) + 1
    print("2. worker drained %d jobs:" % len(drained), {("%s:%s" % k): v for k, v in by.items()})

    reps = reports.build_all()
    print("3. reports built:", {r["client_id"]: r["count"] for r in reps})

    snap = admin.snapshot()
    print("4. ops snapshot:")
    print(json.dumps({
        "queue": snap["queue"], "lead_states": snap["lead_states"], "pool": snap["pool"],
        "spend_today_usd": snap["spend_today_usd"], "replies_per_100": snap["replies_per_100"]["replies_per_100"],
    }, indent=2))
    print("== night shift complete ==")


if __name__ == "__main__":
    main()
