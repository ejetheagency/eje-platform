# factory/workers/learning.py
# Learning (D3). Two read-models the rest of the system optimizes against:
#   1. replies_per_100() — THE north-star metric: positive replies per 100 delivered leads (per client / global).
#   2. strategy_scores() — verified-fields-per-dollar + replies-per-dollar per strategy, so winners get more runs.
# Pure aggregation over engagement_events + strategy_runs. Runs nightly after the enrichment shift.
from factory.packages import db

DELIVERED_EVENTS = ("contacted",)
REPLY_EVENTS = ("replied", "positive_reply")


def replies_per_100(client_id=None):
    q = "select=event,client_lead_id"
    if client_id:
        q += "&client_id=eq.%s" % client_id
    ev = db.select("engagement_events", q)
    delivered = len({e["client_lead_id"] for e in ev if e["event"] in DELIVERED_EVENTS})
    replies = sum(1 for e in ev if e["event"] in REPLY_EVENTS)
    positive = sum(1 for e in ev if e["event"] == "positive_reply")
    return {
        "client_id": client_id or "ALL",
        "delivered": delivered, "replies": replies, "positive_replies": positive,
        "replies_per_100": round(replies / delivered * 100, 1) if delivered else 0.0,
        "positive_per_100": round(positive / delivered * 100, 1) if delivered else 0.0,
    }


def strategy_scores():
    runs = db.select("strategy_runs", "select=strategy_id,fields_passed_gate,cost_usd,reply_outcome")
    agg = {}
    for r in runs:
        sid = r.get("strategy_id") or "unknown"
        a = agg.setdefault(sid, {"runs": 0, "fields": 0, "cost": 0.0, "pos_replies": 0})
        a["runs"] += 1
        a["fields"] += (r.get("fields_passed_gate") or 0)
        a["cost"] += float(r.get("cost_usd") or 0)
        if r.get("reply_outcome") == "positive":
            a["pos_replies"] += 1
    out = []
    for sid, a in agg.items():
        out.append({
            "strategy_id": sid, "runs": a["runs"], "verified_fields": a["fields"], "cost_usd": round(a["cost"], 4),
            "fields_per_dollar": round(a["fields"] / a["cost"], 1) if a["cost"] else None,
            "replies_per_dollar": round(a["pos_replies"] / a["cost"], 2) if a["cost"] else None,
        })
    out.sort(key=lambda x: (x["replies_per_dollar"] or 0, x["fields_per_dollar"] or 0), reverse=True)
    return out


def outreach_rollup(client_id=None):
    """Per-playbook funnel + outcome intelligence for the outreach engine (OUTREACH_PLAYBOOKS.md §5).
    Keyed on playbook_runs (robust to legacy leads whose engagement rows have no client_lead_id).
    This is the response-intelligence moat: which playbook/channel actually earns replies."""
    from collections import defaultdict, Counter
    rq = "select=id,playbook_id,client_id,state"
    if client_id:
        rq += "&client_id=eq.%s" % client_id
    runs = db.select_all("playbook_runs", rq)
    run_ids = {r["id"] for r in runs}
    evs = [e for e in db.select_all("engagement_events", "select=run_id,step_no,channel,event,outcome")
           if e.get("run_id") in run_ids]

    sends_by_run = defaultdict(list)
    replied_runs = set()
    channel_sends = Counter()
    REPLY_OUTCOMES = {"replied", "soft_no", "reopened", "asked_for_material", "positive_reply"}
    for e in evs:
        if e.get("event") == "contacted" and e.get("step_no") is not None:
            sends_by_run[e["run_id"]].append(e["step_no"])
            if e.get("channel"):
                channel_sends[e["channel"]] += 1
        if e.get("outcome") in REPLY_OUTCOMES:
            replied_runs.add(e["run_id"])

    REPLY_STATES = {"replied", "reopened", "converted"}
    by_pb = defaultdict(lambda: {"runs": 0, "reached_1": 0, "reached_2": 0, "reached_3": 0, "replied": 0, "converted": 0})
    for r in runs:
        a = by_pb[r["playbook_id"]]
        a["runs"] += 1
        maxstep = max(sends_by_run.get(r["id"]) or [0])
        a["reached_1"] += 1 if maxstep >= 1 else 0
        a["reached_2"] += 1 if maxstep >= 2 else 0
        a["reached_3"] += 1 if maxstep >= 3 else 0
        if r["state"] in REPLY_STATES or r["id"] in replied_runs:
            a["replied"] += 1
        if r["state"] == "converted":
            a["converted"] += 1

    out = []
    for pb, a in by_pb.items():
        row = dict(a, playbook_id=pb,
                   reply_rate=round(a["replied"] / a["runs"] * 100, 1) if a["runs"] else 0.0)
        out.append(row)
    return {"client_id": client_id or "ALL",
            "by_playbook": sorted(out, key=lambda x: -x["runs"]),
            "channel_sends": dict(channel_sends)}


if __name__ == "__main__":
    import json
    print(json.dumps({
        "replies_per_100": replies_per_100(),
        "strategies": strategy_scores(),
        "outreach_rollup": outreach_rollup(),
    }, indent=2))
