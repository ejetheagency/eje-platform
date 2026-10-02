# factory/packages/queue.py
# Durable job queue on the job_log table (works over the REST service key, no extra extension).
# claim() uses the claim_job() SQL function (SELECT ... FOR UPDATE SKIP LOCKED) so many workers can
# pull concurrently without grabbing the same job. Jobs are idempotent + retry-safe (ENRICHMENT_MASTER_PLAN §8).
from factory.packages import db

MAX_ATTEMPTS = 5


def enqueue(job_type, client_id=None, company_id=None, client_lead_id=None, estimated_cost=0):
    return db.insert("job_log", {
        "type": job_type, "client_id": client_id, "company_id": company_id,
        "client_lead_id": client_lead_id, "status": "queued", "estimated_cost": estimated_cost,
    })[0]


def claim(job_type=None):
    rows = db.rpc("claim_job", {"p_type": job_type})
    return rows[0] if rows else None


def complete(job_id):
    db.update("job_log", "id=eq.%s" % job_id, {"status": "done", "updated_at": _now()})


def fail(job_id, attempt, error):
    status = "dead" if (attempt or 0) >= MAX_ATTEMPTS else "queued"  # requeue until MAX_ATTEMPTS, then dead-letter
    db.update("job_log", "id=eq.%s" % job_id, {"status": status, "error": str(error)[:400], "updated_at": _now()})


def reap(minutes=10):
    # Re-queue jobs orphaned by a dead worker (stuck in 'running'); dead-letter after MAX_ATTEMPTS.
    try:
        return db.rpc("reap_stale_jobs", {"p_minutes": minutes, "p_max_attempts": MAX_ATTEMPTS})
    except Exception:
        return None


def depth(status="queued"):
    rows = db.select("job_log", "status=eq.%s&select=id" % status)
    return len(rows)


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
