# factory/workers/refit.py
# RE-SCORE THE UNDELIVERED POOL with the repaired scorer (operator 2026-10-09, queue item 1).
#
# Scope, deliberately narrow: ONLY cards the client has not seen (source_date IS NULL). A delivered card is frozen,
# and re-scoring one would rewrite what the client was already shown, in the past. The release gate ranks on
# lead_data.score, so re-scoring the pool is exactly what changes which cards ship next.
#
# compare() is READ-ONLY and is meant to be read BEFORE apply(): PLAN item 1 says compare the recomputed score
# against the hand/hybrid score before letting the computed one drive the gate. It reports the drift, and
# critically, whether the ranker's TOP 20 changes character (that is the thing that must not silently move).
#
#   python3 -m factory.workers.refit 2uplatam              # read-only comparison
#   python3 -m factory.workers.refit 2uplatam --apply
import datetime
from factory.packages import db
from factory.workers import fit, release

LEAD_COLS = "id,company,contact_name,contact_email,score,status,source_date,updated_at,lead_data"


def _ic(client_id):
    return ((db.select("clients", "id=eq.%s&select=icp_config" % client_id) or [{}])[0].get("icp_config") or {})


def pool_rows(client_id):
    """The undelivered pool: approved, no date. The cards the gate can still choose from."""
    rows = db.select_all("leads", "client_id=eq.%s&select=%s" % (client_id, LEAD_COLS))
    return [r for r in rows if (r.get("lead_data") or {}).get("approved") and not (r.get("source_date") or "")]


def compare(client_id):
    """Stored score vs the repaired scorer, over the undelivered pool. Writes nothing."""
    ic = _ic(client_id)
    rows = pool_rows(client_id)
    diffs = []
    for r in rows:
        ld = r.get("lead_data") or {}
        old = int(float(ld.get("score") or 0))
        new = int(fit.fit_score_card(ld, ic))
        diffs.append({"id": r["id"], "title": (ld.get("contactTitle") or "")[:38],
                      "old": old, "new": new, "delta": new - old,
                      "crosses": ("up" if old < 60 <= new else ("down" if new < 60 <= old else "")),
                      })
    up = [d for d in diffs if d["crosses"] == "up"]
    down = [d for d in diffs if d["crosses"] == "down"]
    eligible_old = sum(1 for d in diffs if d["old"] >= release.FIT_FLOOR)
    eligible_new = sum(1 for d in diffs if d["new"] >= release.FIT_FLOOR)

    # Does the TOP 20 change character? Rank the same pool twice, once on each score, and compare the sets.
    def top_n(use_new, n=20):
        scored = []
        for r in rows:
            ld = r.get("lead_data") or {}
            sc = int(fit.fit_score_card(ld, ic)) if use_new else int(float(ld.get("score") or 0))
            if sc < release.FIT_FLOOR:
                continue
            rk = sc + 4 * release.channels_of(r) + 2 * release.completeness_of(r) + release.freshness_of(r)
            scored.append((-rk, -sc, r["id"]))
        return [i for _, _, i in sorted(scored)[:n]]

    t_old, t_new = top_n(False), top_n(True)
    same = [i for i in t_new if i in t_old]
    return {
        "client_id": client_id, "pool": len(rows),
        "eligible_old": eligible_old, "eligible_new": eligible_new,
        "crossed_up": up, "crossed_down": down,
        "mean_delta": round(sum(d["delta"] for d in diffs) / float(len(diffs)), 1) if diffs else 0,
        "unchanged": sum(1 for d in diffs if d["delta"] == 0),
        "top20_overlap": len(same), "top20_in": [i for i in t_new if i not in t_old],
        "top20_out": [i for i in t_old if i not in t_new],
        "diffs": sorted(diffs, key=lambda d: -abs(d["delta"])),
        "line": "%s: pool %d | eligible (fit>=%d) %d -> %d | mean delta %+.1f | top20 overlap %d/20" % (
            client_id, len(rows), release.FIT_FLOOR, eligible_old, eligible_new,
            (sum(d["delta"] for d in diffs) / float(len(diffs))) if diffs else 0, len(same)),
    }


def apply(client_id, reason="fit repair (queue item 1)", by="operator"):
    """Write the recomputed score onto the undelivered pool's cards. Keeps the previous value in
    lead_data.scoreBefore so the change is auditable and reversible from the card itself."""
    ic = _ic(client_id)
    changed, now = [], datetime.datetime.now(datetime.timezone.utc).isoformat()
    for r in pool_rows(client_id):
        ld = r.get("lead_data") or {}
        old = int(float(ld.get("score") or 0))
        new = int(fit.fit_score_card(ld, ic))
        if new == old:
            continue
        ld["score"] = new
        ld["scoreBefore"] = old
        ld["scoreRepair"] = {"from": old, "to": new, "reason": reason, "by": by, "at": now}
        db.update("leads", "id=eq.%s&client_id=eq.%s" % (r["id"], client_id),
                  {"score": new, "lead_data": ld})
        changed.append({"id": r["id"], "old": old, "new": new})
    return {"client_id": client_id, "rescored": len(changed), "changes": changed,
            "line": "%s: rescored %d pooled cards" % (client_id, len(changed))}


if __name__ == "__main__":
    import sys, json
    cid = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "2uplatam"
    if "--apply" in sys.argv:
        print(json.dumps(apply(cid), indent=2))
    else:
        c = compare(cid)
        print(c["line"])
        print("\ncrossed UP over the floor (%d):" % len(c["crossed_up"]))
        for d in c["crossed_up"]:
            print("   %-28s %3d -> %3d   %s" % (d["id"], d["old"], d["new"], d["title"]))
        print("\ncrossed DOWN under the floor (%d):" % len(c["crossed_down"]))
        for d in c["crossed_down"]:
            print("   %-28s %3d -> %3d   %s" % (d["id"], d["old"], d["new"], d["title"]))
        print("\ntop20 in:", c["top20_in"] or "none")
        print("top20 out:", c["top20_out"] or "none")
        print("\nbiggest moves:")
        for d in c["diffs"][:12]:
            print("   %-28s %3d -> %3d (%+d)  %s" % (d["id"], d["old"], d["new"], d["delta"], d["title"]))
