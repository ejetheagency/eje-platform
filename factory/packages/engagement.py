# factory/packages/engagement.py
# The OUTREACH engagement state machine (OUTREACH_PLAYBOOKS.md). This is DELIBERATELY SEPARATE from
# factory/packages/lead_state.py: that machine answers "is this lead pitch-ready?" (ENRICHMENT_MASTER_PLAN
# §4, states on client_leads.state). THIS machine answers "how is the outreach conversation going?" and
# only begins after a lead is DELIVERED. State lives on playbook_runs.state. Audit decision 003, fix F1:
# never add these states to lead_state; never add enrichment states here.
import datetime
from factory.packages import db

STATES = [
    "running", "replied", "soft_no", "hard_no", "reopened", "nurture", "converted", "stopped",
]

# Allowed transitions. Terminal: hard_no (flags the contact), converted (win), stopped.
ALLOWED = {
    "running":   {"replied", "soft_no", "hard_no", "converted", "stopped"},
    "replied":   {"soft_no", "hard_no", "converted", "nurture", "stopped"},
    "soft_no":   {"reopened", "nurture", "hard_no", "stopped"},
    "reopened":  {"converted", "nurture", "soft_no", "stopped"},
    "nurture":   {"reopened", "replied", "converted", "stopped"},
    "hard_no":   set(),
    "converted": set(),
    "stopped":   set(),
}


class InvalidTransition(Exception):
    pass


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def can_move(frm, to):
    return to in ALLOWED.get(frm, set())


def start_run(playbook_id, client_id, legacy_lead_id=None, client_lead_id=None):
    """Open a playbook run for a lead. Returns the created run row."""
    row = {
        "playbook_id": playbook_id,
        "client_id": client_id,
        "legacy_lead_id": legacy_lead_id,
        "client_lead_id": client_lead_id,
        "current_step": 0,
        "state": "running",
        "updated_at": _now(),
    }
    out = db.insert("playbook_runs", row, returning=True)
    return out[0] if isinstance(out, list) else out


def move(run_id, to_state):
    rows = db.select("playbook_runs", "id=eq.%s&select=id,state" % run_id)
    if not rows:
        raise InvalidTransition("playbook_run %s not found" % run_id)
    cur = rows[0]["state"]
    if cur == to_state:
        return to_state
    if not can_move(cur, to_state):
        raise InvalidTransition("%s -> %s not allowed" % (cur, to_state))
    db.update("playbook_runs", "id=eq.%s" % run_id, {"state": to_state, "updated_at": _now()})
    return to_state


def advance_step(run_id, step_no):
    """Record progress through the sequence (the worker sets the step it just executed)."""
    db.update("playbook_runs", "id=eq.%s" % run_id, {"current_step": step_no, "updated_at": _now()})
    return step_no
