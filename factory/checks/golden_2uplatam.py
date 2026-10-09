# factory/checks/golden_2uplatam.py
# GOLDEN CHECKS for 2uplatam (Fernando) — the safety net. One plain-language rule per line, PASS/FAIL, re-runnable.
# PROTOCOL (CLAUDE.md): run BEFORE a change, make ONE change, run AFTER; any NEW fail => auto-restore from the
# report_guard backup + report which rule broke. Every fix adds its rule here. Read-only (queries prod + reads app.html).
#   python3 -m factory.checks.golden_2uplatam
import os, re, datetime
from factory.packages import db, calendar_bd as cal

CLIENT = "2uplatam"
COUNTRY = "Ecuador"
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "public", "app.html")
TODAY = datetime.date.today().isoformat()
# his real first-touch (icp_config.outreach_first_touch) — canonical key phrases that MUST be present
TEMPLATE_MUST_HAVE = ["2upLatam", "scale hub", "www.2uplatam.com"]
CLIENT_TABS = ["hoy", "tareas", "decisores"]  # tabs the client view must have
CLIENT_BUTTONS = ["Contactar"]


def _leads():
    return db.select_all("leads", "client_id=eq.%s&select=id,source_date,status,lead_data" % CLIENT)


def _delivered(rows):
    # delivered = approved AND source_date <= today (what the client is allowed to see)
    return [r for r in rows if (r.get("lead_data") or {}).get("approved") and (r.get("source_date") or "") <= TODAY]


def _shippable(ld):
    return bool((ld.get("contactName") or ld.get("decisor")) and ld.get("contactEmail") and not ld.get("emailBounced"))


def r1_only_delivered_contacts(rows):
    d = _delivered(rows)
    bad = [r for r in d if not _shippable(r.get("lead_data") or {})]
    ok = not bad
    return ok, "%d delivered, %d not a real contact (missing decisor/email)" % (len(d), len(bad))


def r2_decisores_equals_distinct(rows):
    d = [r for r in _delivered(rows) if _shippable(r.get("lead_data") or {})]
    shown = len(d)                                              # what the Decisores tab counts (not deduped)
    distinct = len({(r.get("lead_data") or {}).get("contactEmail", "").lower() for r in d})
    ok = shown == distinct
    return ok, "Decisores shows %d, distinct delivered contacts = %d" % (shown, distinct)


def r3_no_duplicate_delivered(rows):
    d = [r for r in _delivered(rows) if _shippable(r.get("lead_data") or {})]
    seen, dups = set(), []
    for r in d:
        e = (r.get("lead_data") or {}).get("contactEmail", "").lower()
        if e in seen:
            dups.append(e)
        seen.add(e)
    ok = not dups
    return ok, "0 duplicates" if ok else "%d duplicate contacts: %s" % (len(dups), ", ".join(sorted(set(dups))[:3]))


def r4_template_is_his_real_one():
    ic = (db.select("clients", "id=eq.%s&select=icp_config" % CLIENT) or [{}])[0].get("icp_config") or {}
    tpl = ic.get("outreach_first_touch") or ""
    missing = [p for p in TEMPLATE_MUST_HAVE if p.lower() not in tpl.lower()]
    ok = not missing
    return ok, "template intact" if ok else "template missing phrases: %s" % missing


def r5_no_report_on_non_business_days(rows):
    d = [r for r in rows if (r.get("lead_data") or {}).get("approved") and _shippable(r.get("lead_data") or {})]
    bad = sorted({r.get("source_date") for r in d
                  if (r.get("source_date") or "") and not cal.is_business_day(r["source_date"], COUNTRY)})
    ok = not bad
    return ok, "none" if ok else "deliverable leads dated on non-business days: %s" % bad


def r6_client_tabs_and_buttons_exist():
    try:
        html = open(APP, encoding="utf-8").read()
    except Exception as e:
        return False, "cannot read app.html: %s" % e
    miss_t = [t for t in CLIENT_TABS if ('data-view="%s"' % t) not in html]
    miss_b = [b for b in CLIENT_BUTTONS if b not in html]
    ok = not miss_t and not miss_b
    return ok, "all present" if ok else "missing tabs=%s buttons=%s" % (miss_t, miss_b)


RULES = [
    ("client view only shows delivered contacts", lambda rows: r1_only_delivered_contacts(rows)),
    ("Decisores tab == count of distinct delivered contacts", lambda rows: r2_decisores_equals_distinct(rows)),
    ("no duplicate contacts in delivered reports", lambda rows: r3_no_duplicate_delivered(rows)),
    ("template = his real sent email", lambda rows: r4_template_is_his_real_one()),
    ("no report on non-business days", lambda rows: r5_no_report_on_non_business_days(rows)),
    ("required tabs and buttons exist in the client view", lambda rows: r6_client_tabs_and_buttons_exist()),
]


def run():
    rows = _leads()
    results = []
    for name, fn in RULES:
        try:
            ok, detail = fn(rows)
        except Exception as e:
            ok, detail = False, "check error: %s" % str(e)[:80]
        results.append((name, ok, detail))
        print("[%s] %s  (%s)" % ("PASS" if ok else "FAIL", name, detail))
    npass = sum(1 for _, ok, _ in results if ok)
    print("\n%d/%d PASS" % (npass, len(results)))
    return results


if __name__ == "__main__":
    run()
