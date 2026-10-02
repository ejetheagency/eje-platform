# factory/workers/runner.py
# The worker loop: claim a job -> dispatch to its department -> complete or fail (with retry). One dispatch
# map; add a department by adding a handler. run_once() does one job; drain() empties the queue; the real
# deployment calls drain() on the scheduler's tick (or runs loop() as a long-lived worker).
import time
from factory.packages import queue, db, lead_state
from factory.providers import site_enrich, gemini, logo, signal_spotter
from factory.workers import gates, scoring

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
            routed = scoring.score_and_route(clid)  # SCORED -> GATE_CHECK (or DISCARDED if below floor)
            out["scoring"] = routed
            if routed.get("route") == "GATE_CHECK":
                queue.enqueue("gates", client_id=job.get("client_id"), company_id=coid, client_lead_id=clid)
    return out


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
    return gates._run_one(cl)


def _h_logo(job):
    return logo.resolve(job["company_id"])


HANDLERS = {
    "enrich_t1": _h_enrich_t1,
    "gates": _h_gates,
    "logo": _h_logo,
}


def run_once(job_type=None):
    job = queue.claim(job_type)
    if not job:
        return None
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


def drain(job_type=None, max_jobs=500):
    done = []
    for _ in range(max_jobs):
        r = run_once(job_type)
        if r is None:
            break
        done.append(r)
    return done


def loop(poll_seconds=5, job_type=None):
    while True:
        if run_once(job_type) is None:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    import json
    print(json.dumps(drain(), indent=2))
