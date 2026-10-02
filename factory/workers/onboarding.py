# factory/workers/onboarding.py
# Self-serve onboarding spine (ENRICHMENT_MASTER_PLAN §8/§9). Two entry points:
#   backfill_icps(apply) : promote existing clients.icp_config blobs into structured `icps` rows.
#   activate_client(...) : the primitive that provisions/updates a client in ONE idempotent call.
#                          Dual-writes clients.icp_config (what the app reads today) AND the
#                          structured icps row, so the app keeps working during the transition.
# DRY-RUN by default (apply=False), mirroring the other migration tools.
#   python3 -m factory.workers.onboarding            # dry-run backfill
#   python3 -m factory.workers.onboarding --apply    # apply backfill
#   python3 -m factory.workers.onboarding --activate  [--apply]   # demo activate_client
import sys, json
from factory.packages import db

DEFAULT_PLAYBOOK = "pb_eje_default"


def _existing_icp_id(client_id, name="default"):
    rows = db.select("icps", "client_id=eq.%s&name=eq.%s&select=id" % (client_id, name))
    return rows[0]["id"] if rows else None


def _row_from_config(client_id, cfg):
    geo = cfg.get("geo")
    return {
        "client_id": client_id,
        "name": "default",
        "brief": cfg.get("icp"),
        "voice": cfg.get("voice"),
        "geos": [geo] if geo else None,
        "discovery_queries": cfg.get("discovery_queries"),
        "signals": cfg.get("signals"),
        "playbook_id": DEFAULT_PLAYBOOK,
        "config": cfg,
        "active": True,
    }


def backfill_icps(apply=False):
    clients = db.select("clients", "select=id,icp_config")
    rep = {"candidates": 0, "skipped_no_icp": 0, "skipped_existing": 0, "created": 0, "rows": []}
    for c in clients:
        cfg = c.get("icp_config") or {}
        if not cfg.get("icp"):                       # library / no-ICP (e.g. eje_productoras kind=library)
            rep["skipped_no_icp"] += 1
            continue
        rep["candidates"] += 1
        if _existing_icp_id(c["id"]):
            rep["skipped_existing"] += 1
            continue
        row = _row_from_config(c["id"], cfg)
        rep["rows"].append({"client_id": c["id"], "brief": (row["brief"] or "")[:70],
                            "geos": row["geos"], "playbook": row["playbook_id"]})
        if apply:
            db.insert("icps", row)
            rep["created"] += 1
    return rep


def activate_client(client_id, name, brief, voice=None, geos=None, sectors=None,
                    signals=None, discovery_queries=None, decisor_role=None,
                    playbook_id=DEFAULT_PLAYBOOK, apply=False):
    """Provision or update a client + its default ICP in one idempotent call. Dual-writes the
    flat clients.icp_config (app) and the structured icps row (factory). Returns the plan of action."""
    cfg = {"icp": brief}
    if voice:
        cfg["voice"] = voice
    if geos:
        cfg["geo"] = geos[0]
    if discovery_queries:
        cfg["discovery_queries"] = discovery_queries
    if signals:
        cfg["signals"] = signals

    plan = {"client_id": client_id, "applied": apply, "will": []}

    cl = db.select("clients", "id=eq.%s&select=id,icp_config" % client_id)
    if cl:
        plan["will"].append("update clients.icp_config")
        if apply:
            merged = dict(cl[0].get("icp_config") or {})
            merged.update(cfg)
            db.update("clients", "id=eq.%s" % client_id, {"icp_config": merged})
    else:
        plan["will"].append("insert clients")
        if apply:
            db.insert("clients", {"id": client_id, "name": name, "icp_config": cfg})

    icp = {"client_id": client_id, "name": "default", "brief": brief, "voice": voice,
           "decisor_role": decisor_role, "geos": geos, "sectors": sectors, "signals": signals,
           "discovery_queries": discovery_queries, "playbook_id": playbook_id,
           "config": cfg, "active": True}
    eid = _existing_icp_id(client_id)
    if eid:
        plan["will"].append("update icps(default)")
        if apply:
            upd = {k: v for k, v in icp.items() if k not in ("client_id", "name")}
            db.update("icps", "id=eq.%s" % eid, upd)
    else:
        plan["will"].append("insert icps(default)")
        if apply:
            db.insert("icps", icp)
    return plan


def main():
    apply = "--apply" in sys.argv
    if "--activate" in sys.argv:
        print("== activate_client demo (%s) ==" % ("APPLY" if apply else "DRY-RUN"))
        print(json.dumps(activate_client(
            client_id="demo_activation_test", name="Demo Activation",
            brief="(demo) prueba de activate_client", voice="neutro LATAM", geos=["Chile"],
            apply=apply), indent=2, default=str))
    else:
        print("== backfill_icps (%s) ==" % ("APPLY" if apply else "DRY-RUN"))
        print(json.dumps(backfill_icps(apply=apply), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
