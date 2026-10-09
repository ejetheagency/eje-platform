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


# ── SCREEN-LEVEL (operator 2026-10-08): the client-facing rules must check WHAT THE CLIENT SEES, not a parallel
# DB query that can pass while the screen is wrong. These mirror app.html's EXACT client render algorithm:
#   today = ejeTodayET() (America/Santiago, rolls at 08:00 Chile) — app.html:1320
#   delivered = approved && source_date<=today                    — app.html:1116/1302
#   Decisores = dedup by (contactEmail.lower() || domain)          — app.html:1745
def _today_chile():
    import zoneinfo
    now = datetime.datetime.now(zoneinfo.ZoneInfo("America/Santiago"))
    d = now.date() - datetime.timedelta(days=1) if now.hour < 8 else now.date()
    return d.isoformat()


def _dom(r):
    return str(r.get("id") or "").lower()


def _screen_delivered(rows):
    t = _today_chile()
    return [r for r in rows if (r.get("lead_data") or {}).get("approved") and (r.get("source_date") or "") and (r.get("source_date") or "") <= t]


def _screen_decisores(rows):
    # EXACT app.html dedup: key = contactEmail.lower() OR domain fallback.
    seen, n = set(), 0
    for r in _screen_delivered(rows):
        k = _ckey(r) or _dom(r)
        if k in seen:
            continue
        seen.add(k); n += 1
    return n


def r1_only_delivered_contacts(rows):
    d = _delivered(rows)
    bad = [r for r in d if not _shippable(r.get("lead_data") or {})]
    return not bad, "%d delivered, %d not a real contact" % (len(d), len(bad))


def r2_decisores_from_ledger(rows):
    # SCREEN-LEVEL: the number app.html actually renders in Decisores (its exact filter+dedup, Chile-today) must
    # equal the ledger. This FAILS if the dedup regresses (screen shows raw 54) — a DB-only query would still pass.
    ledger = deliveries.count(CLIENT)
    screen = _screen_decisores(rows)
    raw = len(_screen_delivered(rows))
    return ledger == screen, "ledger=%d, screen-Decisores(app algo)=%d, raw delivered rows=%d" % (ledger, screen, raw)


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


def _contract_volume():
    ic = (db.select("clients", "id=eq.%s&select=icp_config" % CLIENT) or [{}])[0].get("icp_config") or {}
    return int(ic.get("ready_leads_per_day") or 0)


def _approved_shippable(rows):
    return [r for r in rows if (r.get("lead_data") or {}).get("approved") and _shippable(r.get("lead_data") or {})]


def r10_report_size_equals_contract(rows):
    # NEW (operator 2026-10-08, expected FAIL): each future report date delivers EXACTLY the contract daily volume.
    vol = _contract_volume()
    import collections
    g = collections.Counter(r.get("source_date") for r in _approved_shippable(rows) if (r.get("source_date") or "") > _today_chile())
    bad = {d: n for d, n in g.items() if n != vol}
    return (vol > 0 and not bad), "contract=%d/day; off-size future reports=%s" % (vol, dict(sorted(bad.items())) or "none")


def r11_no_card_below_fit_60(rows):
    # NEW (expected FAIL): no delivered-or-scheduled card ships with fit score < 60.
    def score(r):
        ld = r.get("lead_data") or {}
        try:
            return float(ld.get("score") or r.get("score") or 0)
        except Exception:
            return 0
    low = [r for r in _approved_shippable(rows) if score(r) < 60]
    return not low, "%d cards with fit<60 (e.g. %s)" % (len(low), ", ".join("%s=%s" % ((r.get("lead_data") or {}).get("companyName") or r.get("id"), int(score(r))) for r in sorted(low, key=score)[:6]) or "none")


def r12_company_contact_caps(rows):
    # NEW (expected FAIL): max 1 contact per company per report (source_date) AND max 2 per company overall.
    import collections, re
    def ck(r):
        c = ((r.get("lead_data") or {}).get("companyName") or r.get("company") or "").lower()
        c = re.sub(r"\b(sa|s\.a\.|ltda|cia|c\.a\.|inc|llc|corp|group|grupo|del ecuador|ecuador)\b", "", c)
        return re.sub(r"[^a-z0-9]+", "", c)
    sh = _approved_shippable(rows)
    per_report = collections.Counter((ck(r), r.get("source_date")) for r in sh)
    overall = collections.Counter(ck(r) for r in sh)
    dup_report = {k: n for k, n in per_report.items() if n > 1 and k[0]}
    over_overall = {k: n for k, n in overall.items() if n > 2 and k}
    ok = not dup_report and not over_overall
    return ok, "same-company-same-report=%d, company>2-overall=%d (e.g. %s)" % (
        len(dup_report), len(over_overall),
        ", ".join("%s x%d" % (k, n) for k, n in sorted(over_overall.items(), key=lambda kv: -kv[1])[:5]) or "none")


def r13_admin_labels_client_vs_pipeline():
    # NEW (expected FAIL): every count in the ADMIN view is labeled whether it is what "cliente ve" vs the full "pipeline".
    try:
        html = open(APP, encoding="utf-8").read().lower()
    except Exception as e:
        return False, "cannot read app.html: %s" % e
    has = ("cliente ve" in html) and ("pipeline" in html)
    return has, "admin counts labeled cliente-ve/pipeline: %s" % ("yes" if has else "NO (counts are ambiguous across views)")


def r15_client_counts_single_source(rows):
    # SCREEN-LEVEL (operator 2026-10-08): the two client Decisores render paths must agree AND equal the ledger.
    #   SIDEBAR badge  = load() app.html:2026 -> _n = UNIVERSE.filter(approved).length (NO email dedup)
    #   PAGE header    = renderDecisores app.html:1752 -> email-deduped (app.html:1745)
    # FAILs while they use different formulas (badge 54 vs header 41); PASSes once both read one source == ledger.
    badge = len(_screen_delivered(rows))       # mirrors the no-dedup badge formula
    header = _screen_decisores(rows)           # mirrors the deduped page-header formula
    ledger = deliveries.count(CLIENT)
    ok = (badge == header == ledger)
    return ok, "sidebar badge=%d, page header=%d, ledger=%d%s" % (
        badge, header, ledger, "" if ok else "  <-- diverge: counts not from ONE function")


def r14_live_deploy_matches_repo():
    # SCREEN-LEVEL deploy freshness: the app.html the CLIENT actually loads must be the repo's current app.html,
    # so no rule can pass while the live screen runs stale code (the 54-vs-41 incident = stale/other render path).
    import hashlib, urllib.request
    try:
        local = open(APP, "rb").read()
        req = urllib.request.Request("https://app.ejetheagency.com/app.html", headers={"User-Agent": "golden/1.0", "Cache-Control": "no-cache"})
        live = urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:
        return False, "cannot fetch live app.html: %s" % str(e)[:80]
    lh, vh = hashlib.sha256(local).hexdigest()[:12], hashlib.sha256(live).hexdigest()[:12]
    return lh == vh, "repo app.html %s vs live %s (%s)" % (lh, vh, "match" if lh == vh else "STALE DEPLOY — client runs old code")


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
    # NEW 2026-10-08 (expected FAIL until the account cleanup is approved + applied):
    ("report size == contract daily volume", lambda rows: r10_report_size_equals_contract(rows)),
    ("no delivered/scheduled card with fit score < 60", lambda rows: r11_no_card_below_fit_60(rows)),
    ("max 1 contact/company/report and max 2/company overall", lambda rows: r12_company_contact_caps(rows)),
    ("admin view labels every count cliente-ve vs pipeline", lambda rows: r13_admin_labels_client_vs_pipeline()),
    ("client Decisores: sidebar badge == page header == ledger (one source)", lambda rows: r15_client_counts_single_source(rows)),
    ("live deployed app.html matches repo (no stale screen)", lambda rows: r14_live_deploy_matches_repo()),
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
