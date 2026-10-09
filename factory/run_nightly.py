# factory/run_nightly.py  —  THE NIGHT SHIFT. run() is callable (by the service / cron); main() is the CLI.
#   preflight -> discovery -> enqueue -> drain -> reports -> publish -> miner -> funnel email. Idempotent, safe anytime.
#   python3 -m factory.run_nightly [--client <id>] [--max <N>]
# OPERATOR GUARANTEES (2026-10-08):
#   1) PREFLIGHT first, reported as the funnel email's first line (Serper/Places/MV-credits/Gmail).
#   2) CRASH STILL EMAILS: a top-level guard sends the funnel email even if a step throws ("run died at <step>");
#      silence is never an outcome. out["last_step"] names where we were.
#   3) BUDGET VISIBILITY: spend is traced per step; the miner gets a reserved $1.50 slice of the $3 daily cap.
#   4) MINER TIMEOUT: the miner hard-stops after 90 minutes and reports how far it got.
import sys, json, time, datetime
from factory.workers import scheduler, runner, reports, admin, discovery
from factory.packages import db, queue, budget

MINER_RESERVE_USD = 1.5       # carve this out of the daily cap so upstream can't starve the miner
MINER_DEADLINE_SECS = 90 * 60  # hard wall-clock stop for the miner


def run(client=None, max_leads=None):
    out = {"discovery": {}, "jobs": 0, "reports": {}, "last_step": "start"}
    _since = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")  # night window start
    out["run_started"] = _since
    _t0 = time.time()
    spend_trace = []
    _cap = 0.0
    try:
        _cap = budget.daily_cap()
    except Exception:
        pass
    _trip = {"step": None, "upstream_step": None, "prev": 0.0}

    def step(label):  # name where we are BEFORE each step (so a crash email can say where it died)
        out["last_step"] = label
        return label

    def rec(label):   # record cumulative spend AFTER a paid-heavy step + detect where the cap tripped
        try:
            v = budget.spent_today()
            spend_trace.append("  %-22s $%.3f" % (label, v))
            if _cap:
                if _trip["upstream_step"] is None and _trip["prev"] < (_cap - MINER_RESERVE_USD) <= v:
                    _trip["upstream_step"] = label  # upstream hit its effective ceiling (cap - reserve)
                if _trip["step"] is None and _trip["prev"] < _cap <= v:
                    _trip["step"] = label           # the full $3 cap tripped here
            _trip["prev"] = v
        except Exception:
            pass

    budget.reserve("miner", MINER_RESERVE_USD)  # miner's protected slice of the daily cap

    # PREFLIGHT — the first line of the email. Read-only; keys/credits/gmail-creds presence.
    try:
        from factory.workers import preflight
        out["preflight"] = preflight.check()
    except Exception as e:
        out["preflight"] = {"ok": False, "error": str(e)[:150]}

    fatal = None
    try:
        step("reap"); out["reaped"] = queue.reap()  # re-queue jobs orphaned by a dead worker before processing
        try:  # item 6: operator hand-enriched leads (seeds/<client>.csv) enter the NORMAL chain, nothing skips a gate
            from factory.workers import seed_import
            step("seeds"); out["seeds"] = seed_import.import_seeds()
        except Exception as e:
            out["seeds"] = {"error": str(e)[:150]}
        step("pool_floor"); out["pool_floor"] = scheduler.pool_floor(client_id=client)  # size discovery by READY gap
        out["discovery"] = {p["client"]: p["jobs_enqueued"] for p in out["pool_floor"]}
        try:  # verifier credit alert (notify fires when the SMTP-verify credits run low)
            from factory.packages import notify
            pa = db.select("provider_accounts", "provider=eq.millionverifier&select=credits_remaining")
            cr = float(pa[0]["credits_remaining"]) if pa and pa[0].get("credits_remaining") is not None else None
            out["mv_credits"] = cr
            if cr is not None and cr < 100:
                notify.notify("verifier credits low: %d" % int(cr), "MillionVerifier credits_remaining=%d (<100). Buy a credit pack; verification will fall back / pause when exhausted." % int(cr))
        except Exception:
            pass
        step("scheduler.tick"); scheduler.tick(client_id=client)
        try:  # re-verify leads Gate A NAMED on a prior night when the verify cap was spent (so they reach READY now)
            from factory.workers import reverify
            step("reverify"); out["reverified"] = reverify.sweep(client_id=client)
        except Exception:
            pass
        try:  # promote found email CANDIDATES (verify + attach) -> recovers the 366-found-vs-50-promoted leak. Runs
              # BEFORE re-enrich. Honest: real found addresses, verified, no guessing.
            from factory.workers import promote_candidates
            step("promote_candidates"); out["candidates_promoted"] = promote_candidates.sweep(client_id=client, max_leads=20, apply=True)
        except Exception:
            pass
        rec("promote_candidates")
        try:  # MICRO-ROUTES: for NAMED-but-no-email leads, actively FIND+verify+attach an email via the lane framework
              # (instrumented per lane so route_yield ranks which lane wins per ICP -> double down on winners).
            from factory.workers import micro_routes
            step("micro_routes")
            mr = {}
            for _cid in ([client] if client else [c["id"] for c in db.select("clients", "select=id")]):
                r = micro_routes.sweep(_cid, apply=True)
                if r.get("found"):
                    mr[_cid] = r
            out["micro_routes"] = mr
        except Exception as e:
            out["micro_routes"] = {"error": str(e)[:150]}
        rec("micro_routes")
        try:  # re-enrich parked leads missing a decisor/email through the upgraded site_decisor extraction -> recovers
              # the "no name / no email" parked bucket. The yield fix, run autonomously nightly.
            step("reenrich_parked"); out["reenriched"] = reverify.reenrich_parked(client_id=client)
        except Exception:
            pass
        rec("reenrich_parked")
        try:  # WHATSAPP micro-route BEFORE the gates: find wa.me/tel on carryover pre-gate leads so WhatsApp can clear
              # the >=2-channel bar. Same-night leads are covered inline in gates._run_one.
            from factory.workers import whatsapp_find
            step("whatsapp_find")
            out["whatsapp"] = {c: whatsapp_find.sweep(c, apply=True) for c in ([client] if client else [x["id"] for x in db.select("clients", "select=id")])}
        except Exception as e:
            out["whatsapp"] = {"error": str(e)[:150]}
        rec("whatsapp_find")
        step("drain"); drained = runner.drain_concurrent(workers=4)  # concurrent workers (atomic claim) = faster runs
        out["jobs"] = len(drained)
        rec("drain")
        try:  # capture inbound email replies for EJE's own outreach (agency inbox) -> engagement + learning
            from factory.workers import reply_reconcile
            step("reply_reconcile"); out["replies_captured"] = reply_reconcile.reconcile_email(client="eje", apply=True).get("recorded", 0)
        except Exception:
            pass
        try:  # reconcile OUTBOUND email sends -> platform, by recipient, so the task queue stays TRUE even when the
              # operator sends from his own inbox. EJE-only (his comfort path).
            from factory.workers import reconcile_sends
            step("reconcile_sends"); out["sends_reconciled"] = reconcile_sends.reconcile(client="eje", apply=True).get("recorded", 0)
        except Exception:
            pass
        try:  # INVARIANT: no READY (shippable) card may exist without a verified email -> back to factory or trash.
            from factory.workers import tsa
            step("ready_invariant"); out["ready_invariant"] = tsa.enforce_ready_invariant(client_id=client)
        except Exception as e:
            out["ready_invariant"] = {"error": str(e)[:150]}
        step("reports"); reps = reports.build_all() if not client else [reports.build(client)]
        out["reports"] = {r["client_id"]: r["count"] for r in reps}
        try:  # bridge: publish READY factory leads -> the `leads` table the app reads (contact cards for full-access)
            from factory.workers import publish
            step("publish"); out["published"] = publish.publish_full_access(only=client if client else None)
        except Exception as e:
            out["published"] = {"error": str(e)[:150]}
        try:  # daily-report DRIP: date uncontacted leads N/day so clients see a dated report, not the whole pool at once
            from factory.workers import release
            step("release"); out["released"] = release.schedule_all(only=client if client else None)
        except Exception as e:
            out["released"] = {"error": str(e)[:150]}
        try:  # DELIVERED LEDGER: record newly-delivered contacts (client_deliveries = source of truth for counts)
            from factory.workers import deliveries
            step("deliveries_sync"); out["deliveries"] = deliveries.sync_all()
        except Exception as e:
            out["deliveries"] = {"error": str(e)[:150]}
        try:  # MINER EXPERIMENT (2026-10-07): serper+judgment miner, wired for ONE client (2uplatam), capped at 20,
              # STAGED (approved=False) for hand review vs a manual run. Reserved $1.50 slice of the daily cap + a 90-min
              # hard wall-clock stop. Stays staged: it NEVER counts toward the 3-night auto-approved gate.
            if client is None or client == "2uplatam":
                from factory.workers import agent_miner
                step("miner")
                budget.activate_pool("miner")
                try:
                    # deadline anchored to MINER START, not run start: the drain (1000+ jobs) runs first and would
                    # otherwise eat the whole 90-min budget, leaving the miner 0 time (Night 1: mined=0, stopped=deadline).
                    out["miner"] = agent_miner.mine_and_publish(
                        "2uplatam", 20, report_date=datetime.date.today().isoformat(), approved=False,
                        deadline_ts=time.time() + MINER_DEADLINE_SECS)
                finally:
                    budget.deactivate_pool()
        except Exception as e:
            out["miner"] = {"error": str(e)[:150]}
        rec("miner")
        try:  # THE DAILY GUARANTEE: verify every paying client's Hoy hit its target; alert (notify) on any shortfall
            from factory.workers import sla_check
            step("sla_check"); out["sla"] = sla_check.enforce(only=client if client else None)
        except Exception as e:
            out["sla"] = {"error": str(e)[:150]}
        try:
            step("snapshot")
            snap = admin.snapshot()
            out["pool"] = snap["pool"]
            out["lead_states"] = snap["lead_states"]
            out["spend_today_usd"] = snap["spend_today_usd"]
        except Exception:
            pass
        out["last_step"] = "complete"
    except Exception as e:  # ANY unguarded step crashed — record it; the finally still emails the funnel.
        fatal = {"step": out.get("last_step"), "error": str(e)[:300]}
        out["fatal"] = fatal
    finally:
        # THE ONE EMAIL — always sent, crash or not. Silence must never be an outcome.
        try:
            from factory.workers import funnel, preflight as _pf
            from factory.packages import notify
            pre_line = None
            try:
                pre_line = _pf.line(out.get("preflight") or {})
            except Exception:
                pass
            # spend-trace footer: name where the cap tripped (full $3) and where upstream hit its effective ceiling
            if _cap:
                foot = "  cap $%.2f/night (miner reserve $%.2f)" % (_cap, MINER_RESERVE_USD)
                if _trip["step"]:
                    foot += "; FULL CAP tripped at: %s" % _trip["step"]
                if _trip["upstream_step"]:
                    foot += "; upstream ceiling ($%.2f) hit at: %s" % (_cap - MINER_RESERVE_USD, _trip["upstream_step"])
                if not _trip["step"] and not _trip["upstream_step"]:
                    foot += "; cap NOT reached"
                spend_trace.append(foot)
            pubd = out.get("published") or {}
            results = {}
            if isinstance(pubd, dict) and "error" not in pubd:
                for cid, pres in pubd.items():
                    disc = (out.get("discovery") or {}).get(cid, 0)
                    pcount = pres.get("published", 0) if isinstance(pres, dict) else 0
                    results[cid] = funnel.compute(cid, _since, discovered=disc, published=pcount)
            if not results:  # publish never ran (early crash) — still report the client(s) with zeros so the email goes
                cids = [client] if client else [c["id"] for c in (db.select("clients", "select=id") or [])]
                for cid in cids:
                    try:
                        results[cid] = funnel.compute(cid, _since, discovered=(out.get("discovery") or {}).get(cid, 0), published=0)
                    except Exception:
                        pass
            subject, body = funnel.report(results, preflight_line=pre_line, spend_trace=spend_trace, fatal=fatal)
            notify.notify(subject, body)
            out["funnel"] = {cid: r["funnel"] for cid, r in results.items()}
            out["spend_trace"] = spend_trace
        except Exception as e:
            out["funnel"] = {"error": str(e)[:200]}
    return out


def main():
    client = sys.argv[sys.argv.index("--client") + 1] if "--client" in sys.argv else None
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else None
    print("== EJE factory night shift ==")
    print(json.dumps(run(client=client, max_leads=mx), indent=2))
    print("== done ==")


if __name__ == "__main__":
    main()
