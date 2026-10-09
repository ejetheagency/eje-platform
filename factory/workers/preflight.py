# factory/workers/preflight.py
# PRE-FLIGHT (operator, 2026-10-08): the four things that silently kill a night run, verified at the START and
# reported as the funnel email's FIRST line. Checks: Serper key, Google Places key, MillionVerifier credits, and the
# Gmail app password. Key/credit checks are read-only. The Gmail check reports credential PRESENCE; the live proof is
# that the funnel email ARRIVES (if it does, the send path works). send_test=True also fires ONE real test email now
# (used for the one-time "did you get it?" confirmation). NEVER raises — a failed check must still let the run report.
from factory.packages import notify
from factory.providers import health


def check(send_test=False):
    providers = health.check_all()  # REAL live probe of every provider the nightly uses
    em, pw = notify._creds()
    gmail = bool(em and pw)
    # a provider the nightly depends on to RUN at all (discovery + verify + compose): places, MV, cheap LLM.
    # serper/hunter/prospeo/apollo being out is visible but not a hard fail (discovery falls back to places).
    critical = ["google_places", "millionverifier", "cheap_llm"]
    crit_ok = all(providers.get(p, ("DOWN",))[0] == "OK" for p in critical)
    res = {"providers": providers, "gmail_creds": gmail, "ok": bool(crit_ok and gmail)}
    if send_test and gmail:
        res["test_send"] = notify.notify(
            "preflight test", "Preflight test send. If you received this, the Gmail app password works. (one-time check)")
    return res


def line(res):
    prov = health.line(res.get("providers") or {})
    gmail = "OK" if res.get("gmail_creds") else "MISSING"
    verdict = "PASS" if res.get("ok") else "CHECK"
    return "preflight %s | %s | gmail %s" % (verdict, prov, gmail)


if __name__ == "__main__":
    import json
    r = check(send_test="--test" in __import__("sys").argv)
    print(line(r))
    print(json.dumps(r, indent=2))
