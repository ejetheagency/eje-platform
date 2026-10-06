# factory/run_nightly.py  —  THE NIGHT SHIFT. run() is callable (by the service / cron); main() is the CLI.
#   discovery -> enqueue -> drain -> reports -> ops snapshot. Idempotent, safe to run anytime.
#   python3 -m factory.run_nightly [--client <id>] [--max <N>]
import sys, json
from factory.workers import scheduler, runner, reports, admin, discovery
from factory.packages import db, queue


def run(client=None, max_leads=None):
    out = {"discovery": {}, "jobs": 0, "reports": {}}
    out["reaped"] = queue.reap()  # re-queue any jobs orphaned by a dead worker before processing
    try:  # item 6: operator hand-enriched leads (seeds/<client>.csv) enter the NORMAL chain, nothing skips a gate
        from factory.workers import seed_import
        out["seeds"] = seed_import.import_seeds()
    except Exception as e:
        out["seeds"] = {"error": str(e)[:150]}
    out["pool_floor"] = scheduler.pool_floor(client_id=client)  # size discovery by the READY gap + log + alert
    out["discovery"] = {p["client"]: p["jobs_enqueued"] for p in out["pool_floor"]}
    # verifier credit alert (notify fires when the SMTP-verify credits run low)
    try:
        from factory.packages import notify
        pa = db.select("provider_accounts", "provider=eq.millionverifier&select=credits_remaining")
        cr = float(pa[0]["credits_remaining"]) if pa and pa[0].get("credits_remaining") is not None else None
        out["mv_credits"] = cr
        if cr is not None and cr < 100:
            notify.notify("verifier credits low: %d" % int(cr), "MillionVerifier credits_remaining=%d (<100). Buy a credit pack; verification will fall back / pause when exhausted." % int(cr))
    except Exception:
        pass
    scheduler.tick(client_id=client)
    try:  # re-verify leads Gate A NAMED on a prior night when the verify cap was spent (so they reach READY now)
        from factory.workers import reverify
        out["reverified"] = reverify.sweep(client_id=client)
    except Exception:
        pass
    try:  # promote found email CANDIDATES (verify + attach to the decisor) -> recovers leads whose email the factory
          # already scraped but never verified/attached (the 366-found-vs-50-promoted leak). Runs BEFORE re-enrich so
          # it catches parked-with-decisor-and-candidate leads first. Honest: real found addresses, verified, no guessing.
        from factory.workers import promote_candidates
        out["candidates_promoted"] = promote_candidates.sweep(client_id=client, max_leads=20, apply=True)
    except Exception:
        pass
    try:  # re-enrich parked leads missing a decisor/email through the (upgraded) site_decisor extraction -> recovers
          # the "no name / no email" parked bucket the factory left behind. The yield fix, run autonomously nightly.
        out["reenriched"] = reverify.reenrich_parked(client_id=client)
    except Exception:
        pass
    drained = runner.drain_concurrent(workers=4)  # concurrent workers (atomic claim) = faster nightly runs
    out["jobs"] = len(drained)
    try:  # capture inbound email replies for EJE's own outreach (agency inbox) -> engagement + learning
        from factory.workers import reply_reconcile
        out["replies_captured"] = reply_reconcile.reconcile_email(client="eje", apply=True).get("recorded", 0)
    except Exception:
        pass
    try:  # reconcile OUTBOUND email sends (first touch + chat-drafted + Gmail follow-ups) -> platform, by recipient,
          # so the task queue stays TRUE even when the operator sends from his own inbox. EJE-only (his comfort path).
        from factory.workers import reconcile_sends
        out["sends_reconciled"] = reconcile_sends.reconcile(client="eje", apply=True).get("recorded", 0)
    except Exception:
        pass
    reps = reports.build_all() if not client else [reports.build(client)]
    out["reports"] = {r["client_id"]: r["count"] for r in reps}
    try:  # bridge: publish READY factory leads -> the `leads` table the app reads (contact cards for full-access clients)
        from factory.workers import publish
        out["published"] = publish.publish_full_access(only=client if client else None)
    except Exception as e:
        out["published"] = {"error": str(e)[:150]}
    try:  # daily-report DRIP: date uncontacted leads N/day so clients see a dated report, not the whole pool at once
        from factory.workers import release
        out["released"] = release.schedule_all(only=client if client else None)
    except Exception as e:
        out["released"] = {"error": str(e)[:150]}
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
