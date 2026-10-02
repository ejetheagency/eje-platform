# factory/workers/runner.py
# The worker loop: claim a job -> dispatch to its department -> complete or fail (with retry). One dispatch
# map; add a department by adding a handler. run_once() does one job; drain() empties the queue; the real
# deployment calls drain() on the scheduler's tick (or runs loop() as a long-lived worker).
import time
from factory.packages import queue, db
from factory.providers import site_enrich, gemini, logo
from factory.workers import gates


def _h_enrich_t1(job):
    out = {"site": site_enrich.enrich(job["company_id"])}
    out["brief"] = gemini.brief(job["company_id"], job.get("client_id"))
    return out


def _h_gates(job):
    cl = db.select("client_leads", "id=eq.%s&select=id,client_id,company_id,contact_id,cycle_count" % job["client_lead_id"])
    return gates._run_one(cl[0]) if cl else {"skip": "no lead"}


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
