# factory/workers/admin.py
# Ops observability (ENRICHMENT_MASTER_PLAN §8): one snapshot of the factory's health — queue depth,
# lead states, spend today/month (+ by provider), gate pass rates, and the north-star reply metric.
# Read-only. Powers an internal admin page / a daily ops ping.
import datetime
from urllib.parse import quote
from factory.packages import db
from factory.workers import learning


def _month_start():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


def _today_start():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _counts(table, field):
    rows = db.select_all(table, "select=%s" % field)  # paginated: correct past 1000 rows
    out = {}
    for r in rows:
        k = r.get(field) or "(none)"
        out[k] = out.get(k, 0) + 1
    return out


def _spend(since):
    rows = db.select("cost_ledger", "created_at=gte.%s&select=usd_cost,provider" % quote(since, safe=""))
    total = sum(float(r.get("usd_cost") or 0) for r in rows)
    by_prov = {}
    for r in rows:
        by_prov[r["provider"]] = round(by_prov.get(r["provider"], 0) + float(r.get("usd_cost") or 0), 5)
    return round(total, 4), by_prov


def _gate_pass_rates():
    rows = db.select("gate_results", "select=gate,passed")
    agg = {}
    for r in rows:
        a = agg.setdefault(r["gate"], [0, 0])
        a[0] += 1
        if r["passed"]:
            a[1] += 1
    return {g: {"checks": a[0], "pass_rate": round(a[1] / a[0] * 100, 1) if a[0] else None} for g, a in agg.items()}


def snapshot():
    today_total, today_prov = _spend(_today_start())
    month_total, month_prov = _spend(_month_start())
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "queue": _counts("job_log", "status"),
        "lead_states": _counts("client_leads", "state"),
        "pool": {"companies": db.count("companies"), "contacts": db.count("contacts")},
        "spend_today_usd": today_total, "spend_today_by_provider": today_prov,
        "spend_month_usd": month_total, "spend_month_by_provider": month_prov,
        "gate_pass_rates": _gate_pass_rates(),
        "replies_per_100": learning.replies_per_100(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(snapshot(), indent=2))
