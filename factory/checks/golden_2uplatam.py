# factory/checks/golden_2uplatam.py
# GOLDEN CHECKS for 2uplatam (Fernando) — the safety net. One plain-language rule per line, PASS/FAIL, re-runnable.
# PROTOCOL (CLAUDE.md): run BEFORE a change, make ONE change, run AFTER; any NEW fail => auto-restore from the
# report_guard backup + report which rule broke. Every fix adds its rule here. Read-only (queries prod + reads app.html).
# Client-parameterized: GOLDEN_CLIENT env var (default 2uplatam) so it can run against 2uplatam_staging too.
#   python3 -m factory.checks.golden_2uplatam           # 2uplatam
#   GOLDEN_CLIENT=2uplatam_staging python3 -m factory.checks.golden_2uplatam
import os, datetime
from factory.packages import db, calendar_bd as cal
from factory.workers import deliveries

CLIENT = os.environ.get("GOLDEN_CLIENT", "2uplatam")
COUNTRY = "Ecuador"
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "public", "app.html")
TODAY = datetime.date.today().isoformat()
TEMPLATE_MUST_HAVE = ["2upLatam", "scale hub", "www.2uplatam.com"]   # his real first-touch, canonical phrases
CLIENT_TABS = ["hoy", "tareas", "decisores"]
CLIENT_BUTTONS = ["Contactar"]


def _leads():
    return db.select_all("leads", "client_id=eq.%s&select=id,contact_email,source_date,status,lead_data" % CLIENT)


def _ckey(r):
    ld = r.get("lead_data") or {}
    return ((ld.get("contactEmail") or r.get("contact_email") or "")).strip().lower()


def _shippable(ld):
    return bool((ld.get("contactName") or ld.get("decisor")) and ld.get("contactEmail") and not ld.get("emailBounced"))


def _delivered(rows):
    return [r for r in rows if (r.get("lead_data") or {}).get("approved") and (r.get("source_date") or "") <= TODAY]


def r1_only_delivered_contacts(rows):
    d = _delivered(rows)
    bad = [r for r in d if not _shippable(r.get("lead_data") or {})]
    return not bad, "%d delivered, %d not a real contact" % (len(d), len(bad))


def r2_decisores_from_ledger(rows):
    # Decisores reads ONLY from client_deliveries; it must equal the distinct delivered contacts derived from leads.
    ledger = deliveries.count(CLIENT)
    distinct = len({_ckey(r) for r in _delivered(rows) if _shippable(r.get("lead_data") or {})})
    return ledger == distinct, "Decisores (client_deliveries) = %d, distinct delivered contacts = %d" % (ledger, distinct)


def r3_ledger_no_duplicates():
    rows = db.select_all("client_deliveries", "client_id=eq.%s&select=contact_key" % CLIENT)
    total, distinct = len(rows), len({r["contact_key"] for r in rows})
    return total == distinct, "ledger rows %d, distinct contacts %d" % (total, distinct)


def r4_template_is_his_real_one():
    ic = (db.select("clients", "id=eq.%s&select=icp_config" % CLIENT) or [{}])[0].get("icp_config") or {}
    tpl = ic.get("outreach_first_touch") or ""
    missing = [p for p in TEMPLATE_MUST_HAVE if p.lower() not in tpl.lower()]
    return not missing, "template intact" if not missing else "missing: %s" % missing


def r5_no_report_on_non_business_days(rows):
    d = [r for r in rows if (r.get("lead_data") or {}).get("approved") and _shippable(r.get("lead_data") or {})]
    bad = sorted({r["source_date"] for r in d if (r.get("source_date") or "") and not cal.is_business_day(r["source_date"], COUNTRY)})
    return not bad, "none" if not bad else "deliverable leads on non-business days: %s" % bad


def r6_client_tabs_and_buttons_exist():
    try:
        html = open(APP, encoding="utf-8").read()
    except Exception as e:
        return False, "cannot read app.html: %s" % e
    miss_t = [t for t in CLIENT_TABS if ('data-view="%s"' % t) not in html]
    miss_b = [b for b in CLIENT_BUTTONS if b not in html]
    return (not miss_t and not miss_b), "all present" if not (miss_t or miss_b) else "missing tabs=%s buttons=%s" % (miss_t, miss_b)


def r7_no_scheduled_repeats_delivered(rows):
    # no FUTURE scheduled card repeats a contact already delivered (in the ledger)
    ledger = deliveries.delivered_keys(CLIENT)
    sched = [r for r in rows if (r.get("lead_data") or {}).get("approved") and _shippable(r.get("lead_data") or {})
             and (r.get("source_date") or "") > TODAY]
    repeats = [r for r in sched if _ckey(r) in ledger]
    return not repeats, "%d scheduled cards, %d repeat a delivered contact" % (len(sched), len(repeats))


def r8_serper_nightly_cap():
    # SPEND RULE (operator 2026-10-08): serper is capped at <=1000 searches/night in code (protects the $3 cap +
    # the miner's reserved slice that 2uplatam's self-production depends on). The cap must exist and be sane.
    from factory.packages import budget
    cap = int((budget._cfg().get("provider_nightly_call_caps") or {}).get("serper") or 0)
    return (0 < cap <= 1000), "serper nightly call cap = %s (expect 1..1000)" % (cap or "none")


def r9_archived_clients_off():
    # OFF SWITCH (operator 2026-10-08): altavia is archived (FD stop); archived clients must never leak into the
    # nightly release/discovery targets (re-derived read-only with release.schedule_all's own predicate).
    from factory.workers import client_status
    cs = db.select("clients", "select=id,icp_config")
    arch = [c["id"] for c in cs if client_status.is_archived(c.get("icp_config"))]
    targets = [c["id"] for c in cs
               if (c.get("icp_config") or {}).get("ready_leads_per_day") and c["id"] not in ("eje", "eje_productoras")
               and not client_status.is_archived(c.get("icp_config"))]
    leaked = [a for a in arch if a in targets]
    altavia_off = "altavia" in arch
    return (altavia_off and not leaked), "archived=%s; altavia_off=%s; leaked into targets=%s" % (
        arch or "none", altavia_off, leaked or "none")


RULES = [
    ("client view only shows delivered contacts", lambda rows: r1_only_delivered_contacts(rows)),
    ("Decisores tab == count of distinct delivered contacts (reads client_deliveries)", lambda rows: r2_decisores_from_ledger(rows)),
    ("no duplicate contacts in delivered reports (ledger unique)", lambda rows: r3_ledger_no_duplicates()),
    ("template = his real sent email", lambda rows: r4_template_is_his_real_one()),
    ("no report on non-business days", lambda rows: r5_no_report_on_non_business_days(rows)),
    ("required tabs and buttons exist in the client view", lambda rows: r6_client_tabs_and_buttons_exist()),
    ("no scheduled card repeats a delivered contact", lambda rows: r7_no_scheduled_repeats_delivered(rows)),
    ("serper nightly search cap configured (<=1000)", lambda rows: r8_serper_nightly_cap()),
    ("archived clients are OFF (altavia; none leak into nightly targets)", lambda rows: r9_archived_clients_off()),
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
    print("\n%d/%d PASS  [client=%s]" % (sum(1 for _, ok, _ in results if ok), len(results), CLIENT))
    return results


if __name__ == "__main__":
    run()
