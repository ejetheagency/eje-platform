# factory/workers/scheduler.py
# D0 Scheduler (the night shift). ONLY enqueues jobs; never does the work itself. tick() scans each active
# client's pipeline and enqueues the next job per lead state. The real deployment calls tick() on a cron
# (overnight) then runs the worker drain; this module is cron-agnostic so it runs anywhere.
import os, json, datetime
from urllib.parse import quote
from factory.packages import db, queue

_TH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "thresholds.json")


def _cfg():
    with open(_TH) as f:
        return json.load(f)


def _today():
    return datetime.date.today().isoformat()


def _spend_today(client_id):
    start = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    rows = db.select("cost_ledger", "client_id=eq.%s&created_at=gte.%s&select=usd_cost" % (client_id, quote(start, safe="")))
    return sum(float(r.get("usd_cost") or 0) for r in rows)


def pool_floor(client_id=None):
    """Per active client: target READY = ready_leads_per_day x ready_pool_days. If below, discover enough to
    close the gap (sized to a night's worth), within provider caps (every call is can_spend-gated). Logs one
    row per client per night to pool_floor_log; alerts (notify) if under 50% of target two nights running."""
    from factory.workers import discovery
    from factory.packages import notify
    cfg = _cfg()
    days = cfg.get("ready_pool_days", 7)
    default_rld = cfg.get("default_ready_leads_per_day", 20)
    clients = db.select("clients", ("id=eq.%s&" % client_id if client_id else "") + "select=id,icp_config")
    out = []
    from factory.workers import client_status
    for c in clients:
        cid = c["id"]
        icp = c.get("icp_config") or {}
        if client_status.is_archived(icp):   # OFF: archived client -> no discovery at all (kept, not deleted)
            continue
        if not icp.get("icp"):          # skip library / no-ICP clients
            continue
        # FD: don't even discover for a paused (idle non-paying demo) client — no queue churn, no spend. Kept, not deleted.
        if (icp.get("spend_policy") or "").lower() == "paused" and (icp.get("commercial_status") or "").lower() != "paying":
            out.append({"client": cid, "ready_now": db.count("client_leads", "client_id=eq.%s&state=eq.READY" % cid),
                        "target": 0, "jobs_enqueued": 0, "spend": 0, "under_50pct": False,
                        "line": "pool-floor %s: PAUSED (idle demo — FD stop, no discovery)" % cid})
            continue
        rld = int(icp.get("ready_leads_per_day") or default_rld)
        target = rld * days
        ready_now = db.count("client_leads", "client_id=eq.%s&state=eq.READY" % cid)
        enqueued = 0
        if ready_now < target:
            gap = target - ready_now
            want = min(gap, rld * 4)    # a night's worth of candidates toward the gap
            r = discovery.discover_for_client(cid, max_leads=want)
            enqueued = r.get("created", 0) if r.get("ok") else 0
        spend = round(_spend_today(cid), 4)
        under50 = ready_now < 0.5 * target
        row = {"client_id": cid, "run_date": _today(), "ready_now": ready_now, "target": target,
               "jobs_enqueued": enqueued, "spend_usd": spend, "under_50pct": under50}
        ex = db.select("pool_floor_log", "client_id=eq.%s&run_date=eq.%s&select=id" % (cid, _today()))
        if ex:
            db.update("pool_floor_log", "id=eq.%s" % ex[0]["id"], row)
        else:
            db.insert("pool_floor_log", row, returning=False)
        if under50:
            prev = db.select("pool_floor_log", "client_id=eq.%s&run_date=lt.%s&select=under_50pct&order=run_date.desc&limit=1" % (cid, _today()))
            if prev and prev[0].get("under_50pct"):
                notify.notify("pool-floor: %s under 50%% two nights" % cid,
                              "%s READY=%d of target %d (gap %d). Likely provider cap or ICP width. The system will NOT raise caps on its own; buy credits or widen the ICP." % (cid, ready_now, target, target - ready_now))
        out.append({"client": cid, "ready_now": ready_now, "target": target, "jobs_enqueued": enqueued,
                    "spend": spend, "under_50pct": under50,
                    "line": "pool-floor %s: ready_now=%d target=%d jobs_enqueued=%d spend=$%.4f%s" % (
                        cid, ready_now, target, enqueued, spend, " UNDER-50%" if under50 else "")})
    return out


def tick(client_id=None, limit=1000):
    from factory.workers import client_status
    q = "state=eq.DISCOVERED&select=id,client_id,company_id&limit=%d" % limit
    if client_id:
        q += "&client_id=eq.%s" % client_id
    else:  # OFF: never enqueue enrichment for an archived client's leftover DISCOVERED leads
        arch = client_status.archived_ids()
        if arch:
            q += "&client_id=not.in.(%s)" % ",".join(arch)
    discovered = db.select("client_leads", q)
    for cl in discovered:
        queue.enqueue("enrich_t1", client_id=cl["client_id"], company_id=cl["company_id"], client_lead_id=cl["id"])
    # (later: re-queue PARKED leads when a new provider/strategy appears; enqueue logo refreshes; etc.)
    return {"enqueued_enrich_t1": len(discovered), "queue_depth": queue.depth("queued")}


if __name__ == "__main__":
    import json
    print(json.dumps(tick(), indent=2))
