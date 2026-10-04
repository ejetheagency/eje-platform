# factory/packages/lead_state.py
# The lead lifecycle state machine (ENRICHMENT_MASTER_PLAN §4). THE single source of transition rules.
# Workers only move leads between states through move(); invalid transitions raise.
import datetime
from factory.packages import db

STATES = [
    "DISCOVERED", "T1_ENRICHING", "SCORED", "DISCARDED",
    "GATE_CHECK", "T2_ENRICHING", "T3_REASONING", "READY", "PARKED", "DELIVERED",
]

# Allowed transitions (mirror the master-plan state diagram).
ALLOWED = {
    "DISCOVERED":   {"T1_ENRICHING"},
    "T1_ENRICHING": {"SCORED"},
    "SCORED":       {"DISCARDED", "GATE_CHECK", "T2_ENRICHING"},
    "T2_ENRICHING": {"GATE_CHECK", "DISCARDED"},   # DISCARDED = excluded chain/franchise caught at Gate A
    "GATE_CHECK":   {"READY", "T1_ENRICHING", "T3_REASONING", "PARKED"},
    "T3_REASONING": {"GATE_CHECK"},
    "READY":        {"DELIVERED"},
    "PARKED":       {"T1_ENRICHING", "GATE_CHECK"},  # re-enrich OR re-gate (e.g. email just got verified)
    "DISCARDED":    set(),
    "DELIVERED":    set(),
}


class InvalidTransition(Exception):
    pass


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def can_move(frm, to):
    return to in ALLOWED.get(frm, set())


def move(client_lead_id, to_state):
    rows = db.select("client_leads", "id=eq.%s&select=id,state,cycle_count" % client_lead_id)
    if not rows:
        raise InvalidTransition("client_lead %s not found" % client_lead_id)
    cur = rows[0]["state"]
    if not can_move(cur, to_state):
        raise InvalidTransition("%s -> %s not allowed" % (cur, to_state))
    patch = {"state": to_state, "updated_at": _now()}
    # count a full re-enrichment cycle each time we re-enter enrichment from a gate
    if to_state == "T1_ENRICHING" and cur in ("GATE_CHECK", "PARKED"):
        patch["cycle_count"] = (rows[0].get("cycle_count") or 0) + 1
    if to_state == "DELIVERED":
        patch["delivered_at"] = _now()
    db.update("client_leads", "id=eq.%s" % client_lead_id, patch)
    return to_state
