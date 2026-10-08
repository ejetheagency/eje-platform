# factory/workers/preflight.py
# PRE-FLIGHT (operator, 2026-10-08): the four things that silently kill a night run, verified at the START and
# reported as the funnel email's FIRST line. Checks: Serper key, Google Places key, MillionVerifier credits, and the
# Gmail app password. Key/credit checks are read-only. The Gmail check reports credential PRESENCE; the live proof is
# that the funnel email ARRIVES (if it does, the send path works). send_test=True also fires ONE real test email now
# (used for the one-time "did you get it?" confirmation). NEVER raises — a failed check must still let the run report.
import os
from factory.packages import db, notify


def check(send_test=False):
    serper = bool(os.environ.get("SERPER_API_KEY"))
    places = bool(os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY"))
    try:
        pa = db.select("provider_accounts", "provider=eq.millionverifier&select=credits_remaining")
        mv = float(pa[0]["credits_remaining"]) if pa and pa[0].get("credits_remaining") is not None else None
    except Exception:
        mv = None
    em, pw = notify._creds()
    gmail = bool(em and pw)
    res = {"serper": serper, "places": places, "mv_credits": mv, "gmail_creds": gmail}
    res["ok"] = bool(serper and places and gmail and (mv is None or mv > 0))
    if send_test and gmail:
        res["test_send"] = notify.notify(
            "preflight test", "Preflight test send. If you received this, the Gmail app password works. (one-time check)")
    return res


def line(res):
    mv = res.get("mv_credits")
    mv_s = "?" if mv is None else str(int(mv))
    flag = lambda b: "OK" if b else "MISSING"
    return "preflight %s: serper %s | places %s | mv_credits %s | gmail %s" % (
        "PASS" if res.get("ok") else "FAIL", flag(res.get("serper")), flag(res.get("places")), mv_s, flag(res.get("gmail_creds")))


if __name__ == "__main__":
    import json
    r = check(send_test="--test" in __import__("sys").argv)
    print(line(r))
    print(json.dumps(r, indent=2))
