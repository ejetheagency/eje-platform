# factory/workers/runner.py
# The worker loop: claim a job -> dispatch to its department -> complete or fail (with retry). One dispatch
# map; add a department by adding a handler. run_once() does one job; drain() empties the queue; the real
# deployment calls drain() on the scheduler's tick (or runs loop() as a long-lived worker).
import time
from factory.packages import queue, db, lead_state
from factory.providers import site_enrich, gemini, logo, signal_spotter
from factory.workers import gates, scoring, tier2

_CL = "id,client_id,company_id,contact_id,cycle_count,state"


def _h_enrich_t1(job):
    clid, coid = job.get("client_lead_id"), job["company_id"]
    if clid:
        st = db.select("client_leads", "id=eq.%s&select=state" % clid)
        if st and st[0]["state"] in ("DISCOVERED", "PARKED"):
            lead_state.move(clid, "T1_ENRICHING")
    out = {"site": site_enrich.enrich(coid), "signals": signal_spotter.spot(coid),
           "brief": gemini.brief(coid, job.get("client_id")), "logo": logo.resolve(coid)}
    if clid:
        cur = db.select("client_leads", "id=eq.%s&select=state" % clid)
        if cur and cur[0]["state"] == "T1_ENRICHING":
            lead_state.move(clid, "SCORED")
            routed = scoring.score_and_route(clid)  # SCORED -> GATE_CHECK | T2_ENRICHING | DISCARDED
            out["scoring"] = routed
            nxt = {"GATE_CHECK": "verify", "T2_ENRICHING": "gate_a"}.get(routed.get("route"))  # Gate A (free) before paid tier2
            if nxt:
                queue.enqueue(nxt, client_id=job.get("client_id"), company_id=coid, client_lead_id=clid)
    return out


def _h_tier2(job):
    r = tier2.run(job["client_lead_id"])  # finds a named decisor + email, moves T2_ENRICHING -> GATE_CHECK
    queue.enqueue("verify", client_id=job.get("client_id"), company_id=job["company_id"], client_lead_id=job["client_lead_id"])
    return r


def _h_verify(job):
    # Verify the chosen contact's email via Hunter (STEP 1.5), then enqueue gates. Only this step writes
    # email_status="verified" + email_verified_at. Mapping: deliverable -> verified; accept_all/risky ->
    # catch_all (gate passes only if ICP allows); undeliverable/invalid -> bounced (clear email, back to T1);
    # unknown -> retry once next night, then catch_all. Never re-verify within verify_ttl_days.
    import datetime, json as _json, os as _os
    from factory.providers import verifier
    clid = job["client_lead_id"]
    rows = db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,contact_id,state" % clid)
    if not rows:
        return {"skip": "no lead"}
    cl = rows[0]

    def _now():
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def go_gates():
        queue.enqueue("gates", client_id=cl["client_id"], company_id=cl["company_id"], client_lead_id=clid)

    def regate_if_parked():  # a fresh verification un-parks a lead so gates can promote it this same run
        if cl.get("state") == "PARKED":
            try:
                lead_state.move(cl["id"], "GATE_CHECK")
            except Exception:
                pass

    cid = cl.get("contact_id")
    if not cid:
        go_gates(); return {"skip": "no contact"}
    ct = db.select("contacts", "id=eq.%s&select=email,email_status,email_verified_at,email_verify_attempts" % cid)
    ct = ct[0] if ct else {}
    email = ct.get("email")
    if not email:
        go_gates(); return {"skip": "no email"}
    # Already resolved (verified, or decided catch_all / catch_all_suspected / bounced) -> don't spend another credit.
    if ct.get("email_verified_at") or ct.get("email_status") in ("catch_all", "catch_all_suspected", "bounced"):
        go_gates(); return {"skip": "resolved (%s)" % (ct.get("email_status") or "verified")}

    # night_credit_cap: HARD stop on paid SMTP verifications per UTC day (config verify.night_credit_cap).
    _thp = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "config", "thresholds.json")
    try:
        _ncap = int((_json.load(open(_thp)).get("verify") or {}).get("night_credit_cap", 100))
    except Exception:
        _ncap = 100
    _day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if db.count("cost_ledger", "created_at=gte.%s&provider=in.(millionverifier,hunter)" % _day) >= _ncap:
        go_gates(); return {"skip": "night_credit_cap reached (>=%d today), budget stop" % _ncap}  # not an error

    v = verifier.verify(email, client_id=cl["client_id"])  # Gate B (SMTP): millionverifier -> hunter
    if not v.get("ok"):
        go_gates(); return {"verify_error": v.get("reason")}
    status = (v.get("status") or "").lower()
    result = (v.get("result") or "").lower()
    patch = {"last_verified_at": _now(), "email_verify_method": "smtp"}
    if result == "deliverable" or status == "valid":
        patch.update({"email_verified_at": _now(), "email_status": "verified"})
        db.update("contacts", "id=eq.%s" % cid, patch)
        regate_if_parked()
        go_gates()
        return {"result": "verified"}
    if result == "risky" or status == "accept_all":
        patch["email_status"] = "catch_all"
        db.update("contacts", "id=eq.%s" % cid, patch)
        if gates._allow_catch_all(cl["client_id"]):  # catch_all only un-parks when the ICP allows it
            regate_if_parked()
        go_gates()
        return {"result": "catch_all"}
    if result == "undeliverable" or status in ("invalid", "disposable"):
        patch.update({"email": None, "email_status": "bounced"})
        db.update("contacts", "id=eq.%s" % cid, patch)
        if cl["state"] == "GATE_CHECK":
            lead_state.move(cl["id"], "T1_ENRICHING")
            queue.enqueue("enrich_t1", client_id=cl["client_id"], company_id=cl["company_id"], client_lead_id=clid)
        return {"result": "bounced"}
    # unknown (incl. SMTP timeout): retry up to 2 attempts total, then catch_all_suspected (Gate A decides tomorrow)
    attempts = (ct.get("email_verify_attempts") or 0) + 1
    patch["email_verify_attempts"] = attempts
    if attempts >= 2:
        patch["email_status"] = "catch_all_suspected"
        db.update("contacts", "id=eq.%s" % cid, patch); go_gates()
        return {"result": "unknown->catch_all_suspected"}
    patch["email_status"] = "unknown"
    db.update("contacts", "id=eq.%s" % cid, patch)  # stays in GATE_CHECK; re-verified next night
    return {"result": "unknown-retry (%d/2)" % attempts}


def _h_gates(job):
    rows = db.select("client_leads", "id=eq.%s&select=%s" % (job["client_lead_id"], _CL))
    if not rows:
        return {"skip": "no lead"}
    cl = rows[0]
    if cl["state"] == "SCORED":
        lead_state.move(cl["id"], "GATE_CHECK")
        cl = db.select("client_leads", "id=eq.%s&select=%s" % (cl["id"], _CL))[0]
    if cl["state"] != "GATE_CHECK":
        return {"skip": "not in GATE_CHECK (%s)" % cl["state"]}
    result = gates._run_one(cl)
    if result.get("result") == "READY":  # pitch-ready: auto-compose the premium dossier + pitch
        queue.enqueue("compose", client_id=cl.get("client_id"), company_id=cl["company_id"], client_lead_id=cl["id"])
    return result


def _h_compose(job):
    import datetime
    from factory.workers import composer
    r = composer.compose(job["client_lead_id"])
    if r.get("ok"):
        db.update("client_leads", "id=eq.%s" % job["client_lead_id"],
                  {"composed": r, "composed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    return {"composed": bool(r.get("ok")), "provider": r.get("_provider")}


def _h_logo(job):
    return logo.resolve(job["company_id"])


def _h_gate_a(job):
    # FREE loop first (Gate A corroboration, $0). Fall to PAID tier2 ONLY when Gate A ends with no name or no
    # email candidate. On a corroborated name+email, move the lead to GATE_CHECK and run verify -> gates.
    from factory.workers import gate_a
    clid = job["client_lead_id"]
    r = gate_a.run(clid)
    if r.get("name") and r.get("email"):
        st = db.select("client_leads", "id=eq.%s&select=state" % clid)
        if st and st[0]["state"] in ("T2_ENRICHING", "SCORED", "PARKED"):
            try:
                lead_state.move(clid, "GATE_CHECK")
            except Exception:
                pass
        queue.enqueue("verify", client_id=job.get("client_id"), company_id=job["company_id"], client_lead_id=clid)
    else:
        queue.enqueue("tier2", client_id=job.get("client_id"), company_id=job["company_id"], client_lead_id=clid)
    return r


def _h_provision_client(job):
    # Runs when a client pays (the Stripe webhook enqueues this with the client_id). Provisioning =
    # flip the client to active + build their FIRST prospection batch. Closes the payment->activation loop.
    import datetime
    from factory.workers import discovery
    cid = job.get("client_id")
    if not cid:
        return {"skip": "no client_id on job"}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = db.select("clients", "id=eq.%s&select=icp_config" % cid)
    if not rows:
        return {"skip": "client %s not found" % cid}
    cfg = rows[0].get("icp_config") or {}
    if not cfg.get("activated_at"):
        cfg["activated_at"] = now
        db.update("clients", "id=eq.%s" % cid, {"icp_config": cfg})
    disc = {}
    try:
        disc = discovery.discover_for_client(cid, max_leads=25)  # they paid -> spend is justified
    except Exception as e:
        disc = {"error": str(e)[:200]}
    return {"client_id": cid, "activated_at": cfg.get("activated_at"), "discovery": disc}


HANDLERS = {
    "enrich_t1": _h_enrich_t1,
    "tier2": _h_tier2,
    "gate_a": _h_gate_a,
    "verify": _h_verify,
    "gates": _h_gates,
    "compose": _h_compose,
    "logo": _h_logo,
    "provision_client": _h_provision_client,
}


def _process(job):
    h = HANDLERS.get(job["type"])
    try:
        if not h:
            raise RuntimeError("no handler for job type %s" % job["type"])
        result = h(job)
        queue.complete(job["id"])
        return {"id": job["id"], "type": job["type"], "ok": True, "result": result}
    except Exception as e:
        queue.fail(job["id"], job.get("attempt"), e)
        return {"id": job["id"], "type": job["type"], "ok": False, "error": str(e)}


def run_once(job_type=None):
    job = queue.claim(job_type)
    return _process(job) if job else None


def drain(job_type=None, max_jobs=500):
    done = []
    for _ in range(max_jobs):
        r = run_once(job_type)
        if r is None:
            break
        done.append(r)
    return done


def drain_concurrent(workers=4, job_type=None, max_jobs=2000):
    # Many workers claim concurrently (claim_job uses FOR UPDATE SKIP LOCKED, so no double-grant). A worker
    # exits only when the queue is empty AND no worker is still processing (so chained jobs aren't missed).
    import threading
    results, active = [], {"n": 0}
    lock = threading.Lock()

    def w():
        while True:
            with lock:
                if len(results) >= max_jobs:
                    return
            job = queue.claim(job_type)
            if job is None:
                with lock:
                    if active["n"] == 0:
                        return
                time.sleep(0.4)
                continue
            with lock:
                active["n"] += 1
            try:
                r = _process(job)
            finally:
                with lock:
                    active["n"] -= 1
            with lock:
                results.append(r)

    ts = [threading.Thread(target=w, daemon=True) for _ in range(max(1, workers))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return results


def loop(poll_seconds=5, job_type=None):
    while True:
        if run_once(job_type) is None:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    import json
    print(json.dumps(drain(), indent=2))
