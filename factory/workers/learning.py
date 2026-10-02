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


if __name__ == "__main__":
    import json
    print(json.dumps({"replies_per_100": replies_per_100(), "strategies": strategy_scores()}, indent=2))
