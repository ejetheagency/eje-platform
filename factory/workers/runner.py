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
            nxt = {"GATE_CHECK": "gates", "T2_ENRICHING": "tier2"}.get(routed.get("route"))
            if nxt:
                queue.enqueue(nxt, client_id=job.get("client_id"), company_id=coid, client_lead_id=clid)
    return out


def _h_tier2(job):
    r = tier2.run(job["client_lead_id"])  # finds a named decisor + email, moves T2_ENRICHING -> GATE_CHECK
    queue.enqueue("gates", client_id=job.get("client_id"), company_id=job["company_id"], client_lead_id=job["client_lead_id"])
    return r


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
