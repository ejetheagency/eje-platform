# factory/packages/playbook.py
# The planner: given a playbook run, decide the NEXT due task (the "siguiente tarea"). Data-driven
# from playbook_steps (OUTREACH_PLAYBOOKS.md), mirroring the cadence logic but READ from the DB
# instead of hardcoded in app.html. The core, next_step(), is a PURE function (no DB, unit-testable
# offline); plan_run() is the DB-backed wrapper. Dormant until a worker calls it, wires nothing into
# the live app. Engagement state (run.state) comes from factory/packages/engagement.py (NOT lead_state).
import datetime
from factory.packages import db

# Reply-type outcomes stop a no_reply chain.
REPLY_OUTCOMES = {"replied", "soft_no", "hard_no", "question", "reopened", "asked_for_material", "positive_reply"}
# Terminal engagement states: no further task.
TERMINAL = {"hard_no", "converted", "stopped"}


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _has_reply(touches):
    return any(t.get("outcome") in REPLY_OUTCOMES for t in touches)


def _matches(on, run_state):
    # on may be "soft_no", a composite "reopened_or_asked_for_material", or a worker-only cue
    # like "answer_to_step_4" (not a run_state -> never auto-fires here; the worker/human advances it).
    if on == run_state:
        return True
    if "_or_" in on:
        return run_state in on.split("_or_")
    return False


def next_step(steps, touches, run_state="running", now=None):
    """PURE. Decide the next task for a run.
    steps:   list of step dicts (step_no, trigger, channel, intent, template_id, required_fields, ...).
    touches: list of {step_no, at (iso), outcome} already executed for this run.
    Returns {status, step, due_at, reason?} where status in due | waiting | done | stopped.
    """
    now = now or _now()
    steps = sorted(steps, key=lambda s: s["step_no"])
    done = {t["step_no"] for t in touches}
    last_touch = max((_parse(t.get("at")) for t in touches if _parse(t.get("at"))), default=None)

    if run_state in TERMINAL:
        return {"status": "stopped", "step": None, "due_at": None, "reason": run_state}

    for s in steps:
        if s["step_no"] in done:
            continue
        trig = s.get("trigger") or {}

        # event-driven step: fires only when the run is in the matching engagement state
        on = trig.get("on")
        if on:
            if _matches(on, run_state):
                return {"status": "due", "step": s, "due_at": now.isoformat()}
            continue

        # start step: due when nothing has been sent yet
        if trig.get("start"):
            if not touches:
                return {"status": "due", "step": s, "due_at": now.isoformat()}
            continue

        # time-driven step: after_days since the last touch, only while there is no reply
        ad = trig.get("after_days")
        if ad is not None:
            if trig.get("if") == "no_reply" and _has_reply(touches):
                return {"status": "stopped", "step": None, "due_at": None, "reason": "replied"}
            if not last_touch:
                return {"status": "due", "step": s, "due_at": now.isoformat()}
            due = last_touch + datetime.timedelta(days=ad)
            if now >= due:
                return {"status": "due", "step": s, "due_at": due.isoformat()}
            return {"status": "waiting", "step": s, "due_at": due.isoformat()}

    return {"status": "done", "step": None, "due_at": None}


# ── DB-backed wrappers ──
def load_steps(playbook_id):
    return db.select("playbook_steps",
                     "playbook_id=eq.%s&select=step_no,trigger,channel,intent,template_id,required_fields,stop_if,next_state,meta&order=step_no" % playbook_id)


def plan_run(run_id):
    """Look up a run, its playbook steps, and its touches (engagement_events), then plan the next task."""
    runs = db.select("playbook_runs", "id=eq.%s&select=id,playbook_id,client_id,state,current_step" % run_id)
    if not runs:
        return None
    run = runs[0]
    steps = load_steps(run["playbook_id"])
    # Include ALL events for the run: step touches carry step_no; a reply/meeting event may have no
    # step_no but its outcome must still stop a no_reply chain (_has_reply).
    evs = db.select("engagement_events",
                    "run_id=eq.%s&select=step_no,at,outcome&order=at" % run_id)
    touches = [{"step_no": e.get("step_no"), "at": e.get("at"), "outcome": e.get("outcome")} for e in evs]
    plan = next_step(steps, touches, run.get("state") or "running")
    return {"run": run, "plan": plan}
