# factory/workers/scheduler.py
# D0 Scheduler (the night shift). ONLY enqueues jobs; never does the work itself. tick() scans each active
# client's pipeline and enqueues the next job per lead state. The real deployment calls tick() on a cron
# (overnight) then runs the worker drain; this module is cron-agnostic so it runs anywhere.
from factory.packages import db, queue


def tick(client_id=None, limit=1000):
    q = "state=eq.DISCOVERED&select=id,client_id,company_id&limit=%d" % limit
    if client_id:
        q += "&client_id=eq.%s" % client_id
    discovered = db.select("client_leads", q)
    for cl in discovered:
        queue.enqueue("enrich_t1", client_id=cl["client_id"], company_id=cl["company_id"], client_lead_id=cl["id"])
    # (later: re-queue PARKED leads when a new provider/strategy appears; enqueue logo refreshes; etc.)
    return {"enqueued_enrich_t1": len(discovered), "queue_depth": queue.depth("queued")}


if __name__ == "__main__":
    import json
    print(json.dumps(tick(), indent=2))
