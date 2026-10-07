# factory/workers/sla_check.py
# THE DAILY GUARANTEE, enforced + alerted. The deliverable 2uplatam (and every paying client) pays for is a
# full Hoy EVERY business day: >= ready_leads_per_day actionable cards, dated today. pool_floor keeps the pool
# stocked, publish/release put cards on Hoy; THIS is the backstop that VERIFIES the count the client will actually
# see and ALERTS (notify) the moment Hoy is short, so a dry night is never silent. Read-only on the pipeline.
import os, json, datetime
from urllib.parse import quote
from factory.packages import db

_TH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "thresholds.json")

try:
    from zoneinfo import ZoneInfo
    _SCL = ZoneInfo("America/Santiago")  # Hoy rolls over at 08:00 Chile (mirrors app.html ejeTodayET)
except Exception:
    _SCL = None


def _cfg():
    with open(_TH) as f:
        return json.load(f)


def report_today():
    """The active-report date the app shows as 'today': Santiago wall-clock, rolling over at 08:00."""
    if _SCL:
        now = datetime.datetime.now(_SCL)
        d = now.date()
        if now.hour < 8:
            d = d - datetime.timedelta(days=1)
        return d.isoformat()
    return datetime.date.today().isoformat()


def check(client_id, icp=None, cfg=None, day=None):
    """Count the Hoy a client will actually see today vs their daily target. Actionable = approved + has email."""
    cfg = cfg or _cfg()
    if icp is None:
        c = db.select("clients", "id=eq.%s&select=icp_config" % client_id)
        icp = (c[0].get("icp_config") or {}) if c else {}
    day = day or report_today()
    target = int(icp.get("ready_leads_per_day") or cfg.get("default_ready_leads_per_day", 20))
    rows = db.select_all("leads", "client_id=eq.%s&source_date=eq.%s&select=id,contact_email,lead_data"
                         % (client_id, quote(day, safe="")))
    approved = [r for r in rows if ((r.get("lead_data") or {}).get("approved"))]
    actionable = [r for r in approved if (r.get("contact_email") or "").strip()]
    live = len(actionable)
    gap = max(0, target - live)
    return {"client_id": client_id, "day": day, "target": target, "approved_today": len(approved),
            "live": live, "gap": gap, "ok": gap == 0,
            "line": "SLA %s %s: %d/%d actionable on Hoy%s" % (
                client_id, day, live, target, "" if gap == 0 else "  <-- SHORT by %d" % gap)}


def enforce(only=None):
    """Verify every paying client's Hoy hit target; fire ONE shortfall alert if any came up short. Wire at run end."""
    cfg = _cfg()
    clients = db.select("clients", ("id=eq.%s&" % only if only else "") + "select=id,icp_config")
    reports, shortfalls = [], []
    for c in clients:
        icp = c.get("icp_config") or {}
        if not icp.get("icp"):                       # skip library / no-ICP spaces
            continue
        if not icp.get("ready_leads_per_day"):       # only clients with a committed daily target (SLA)
            continue
        paying = (icp.get("commercial_status") or "").lower() == "paying"
        if not paying:                               # SLA is a paying-client promise; others don't alert
            continue
        r = check(c["id"], icp=icp, cfg=cfg)
        reports.append(r)
        if not r["ok"]:
            shortfalls.append(r)
    if shortfalls:
        try:
            from factory.packages import notify
            body = "\n".join("%s: %d/%d on Hoy (short %d) for %s" % (
                s["client_id"], s["live"], s["target"], s["gap"], s["day"]) for s in shortfalls)
            notify.notify("SLA shortfall: %d client(s) under daily target" % len(shortfalls),
                          body + "\n\nHoy is NOT full. Backfill from the enriched pool or mine net-new before 8 AM.")
        except Exception:
            pass
    return {"checked": len(reports), "short": len(shortfalls), "reports": reports}


if __name__ == "__main__":
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None
    out = enforce(only=only)
    for r in out["reports"]:
        print(r["line"])
    print("== %d checked, %d short ==" % (out["checked"], out["short"]))
