# factory/workers/release.py
# Daily-report DRIP. A client's deliverable leads are RELEASED ~N/day (ready_leads_per_day) across dates, so the
# client sees a dated report of N/day instead of the whole pool at once. Uncontacted leads (status none), best-first
# by score, get source_dates starting from the client's go-live (contract.term_start) or today, N per date. The app's
# Hoy shows source_date <= today (released); future dates are held "for next reports".
# Non-destructive: already-released leads (source_date <= today) KEEP their date (a lead a client already saw never
# vanishes); only unreleased leads (no date or future) are (re)scheduled, filling each day up to the cap.
import datetime
from factory.packages import db


def schedule(client_id, per_day=None, start_date=None):
    ic = ((db.select("clients", "id=eq.%s&select=icp_config" % client_id) or [{}])[0].get("icp_config") or {})
    per_day = int(per_day or ic.get("ready_leads_per_day") or 20)
    today = datetime.date.today()
    if start_date:
        start = datetime.date.fromisoformat(start_date)
    else:
        start = today
        cs = (ic.get("contract") or {}).get("term_start")
        if cs:
            try:
                d = datetime.date.fromisoformat(cs)
                start = d if d > today else today
            except Exception:
                pass
    rows = db.select_all("leads", "client_id=eq.%s&status=eq.none&select=id,score,source_date,lead_data&order=score.desc" % client_id)
    used = {}            # date -> count already placed (released leads reserve their day's capacity)
    unreleased = []
    for r in rows:
        sd = r.get("source_date") or ""
        if sd and start.isoformat() <= sd <= today.isoformat():   # released within the valid window -> keep (don't vanish)
            used[sd] = used.get(sd, 0) + 1
        else:
            unreleased.append(r)
    day = start
    n = 0
    for r in unreleased:
        while used.get(day.isoformat(), 0) >= per_day:
            day = day + datetime.timedelta(days=1)
        d = day.isoformat()
        used[d] = used.get(d, 0) + 1
        ld = r.get("lead_data") or {}
        ld["source_date"] = d
        db.update("leads", "id=eq.%s&client_id=eq.%s" % (r["id"], client_id), {"source_date": d, "lead_data": ld})
        n += 1
    last = max(used.keys()) if used else start.isoformat()
    return {"client_id": client_id, "rescheduled": n, "per_day": per_day, "from": start.isoformat(), "through": last}


def schedule_all(only=None):
    """Drip-schedule client workspaces that have a daily cap (ready_leads_per_day), excluding EJE's own + the library."""
    targets = [c["id"] for c in db.select("clients", "select=id,icp_config")
               if (c.get("icp_config") or {}).get("ready_leads_per_day") and c["id"] not in ("eje", "eje_productoras")]
    if only:
        targets = [t for t in targets if t == only]
    return {cid: schedule(cid) for cid in targets}
