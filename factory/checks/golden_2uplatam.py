# factory/checks/golden_2uplatam.py
# GOLDEN CHECKS for 2uplatam (Fernando) — the safety net. One plain-language rule per line, PASS/FAIL, re-runnable.
# PROTOCOL (CLAUDE.md): run BEFORE a change, make ONE change, run AFTER; any NEW fail => auto-restore from the
# report_guard backup + report which rule broke. Every fix adds its rule here. Read-only (queries prod + reads app.html).
# Client-parameterized: GOLDEN_CLIENT env var (default 2uplatam) so it can run against 2uplatam_staging too.
#   python3 -m factory.checks.golden_2uplatam           # 2uplatam
#   GOLDEN_CLIENT=2uplatam_staging python3 -m factory.checks.golden_2uplatam
import os, re, datetime
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


def _dated(r):
    """A card is IN A REPORT only if it has a date. No date = POOL (release.py's gate has not picked it yet) and a
    pooled card is in no report, delivered or future. Never compare an empty source_date against today: "" <= today
    is true in string order, which would read the whole pool as delivered."""
    return bool(r.get("source_date") or "")


def _delivered(rows):
    return [r for r in rows if (r.get("lead_data") or {}).get("approved") and _dated(r) and r["source_date"] <= TODAY]


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
    """No card sits in a report dated a day nobody works. ONE accepted exception (operator 2026-10-09): a card the
    client ACTUALLY ACTED ON. The Oct 9 publish leak dated cards on the Ecuador holiday; the un-actioned ones were
    taken back (release.undeliver_date) and are pooled again, but a card he used is really in his hands and keeps
    its date. Those are listed by name here, never hidden behind a PASS."""
    d = [r for r in rows if (r.get("lead_data") or {}).get("approved") and _shippable(r.get("lead_data") or {})
         and (r.get("source_date") or "") and not cal.is_business_day(r["source_date"], COUNTRY)]
    if not d:
        return True, "none"
    t = deliveries.touched(CLIENT)
    kept = sorted("%s@%s" % (r["id"], r["source_date"]) for r in d if deliveries.is_actioned(r, t))
    bad = sorted({r["source_date"] for r in d if not deliveries.is_actioned(r, t)})
    return not bad, ("accepted exceptions (client acted on them, not recallable): %s" % kept if not bad
                     else "un-actioned deliverable leads on non-business days: %s (take back with "
                          "release.undeliver_date); accepted exceptions: %s" % (bad, kept or "none"))


def r18_no_unactioned_card_stays_delivered_on_a_holiday(rows):
    """The leak's own rule (operator 2026-10-09): a card delivered on a non-business day that the client never
    touched must be back in the pool, not sitting in his history burning a real lead on a day nobody worked."""
    dated = [r for r in rows if (r.get("source_date") or "") and not cal.is_business_day(r["source_date"], COUNTRY)]
    visible = [r for r in dated if (r.get("lead_data") or {}).get("approved")]
    # un-approved rows are invisible to the client (app.html demands approved), so they are not DELIVERED — but
    # they still carry a holiday date, so they are counted out loud here instead of hiding behind the PASS.
    hidden = len(dated) - len(visible)
    if not visible:
        return True, "0 client-visible cards dated a non-business day (%d un-approved rows still carry one, invisible to the client)" % hidden
    t = deliveries.touched(CLIENT)
    stuck = sorted(r["id"] for r in visible if not deliveries.is_actioned(r, t) and _shippable(r.get("lead_data") or {}))
    acted = sorted(r["id"] for r in visible if deliveries.is_actioned(r, t))
    return not stuck, "%d client-visible cards dated a non-business day: %d actioned (stay), %d un-actioned still delivered%s (+%d un-approved, invisible)" % (
        len(visible), len(acted), len(stuck), "" if not stuck else " -> %s" % stuck, hidden)


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
    # nightly release/discovery targets (re-derived read-only with release.assemble_all's own predicate).
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
    # REPORT SIZE: no report a client has not received yet may hold MORE than the contract daily volume. Oversize is
    # the old pre-scheduling bug (leftovers + padding riding on an already-dated day). SHORT is allowed and honest —
    # the gate never pads below the fit floor — and r16 proves a short report is the pool's true ceiling.
    # Legacy delivered days are reported, not failed (already in the client's hands).
    vol = _contract_volume()
    import collections
    t = _today_chile()
    sh = _approved_shippable(rows)
    g = collections.Counter(r.get("source_date") for r in sh if (r.get("source_date") or "") > t)
    over = {d: n for d, n in g.items() if n > vol}
    legacy_over = {d: n for d, n in collections.Counter(
        r.get("source_date") for r in sh if (r.get("source_date") or "") and (r.get("source_date") or "") <= t).items() if n > vol}
    return (vol > 0 and not over), "contract=%d/day; next report(s)=%s; oversize=%s; legacy delivered days over size=%s" % (
        vol, dict(sorted(g.items())) or "none", dict(sorted(over.items())) or "none", dict(sorted(legacy_over.items())) or "none")


def _fit(r):
    ld = r.get("lead_data") or {}
    try:
        return float(ld.get("score") or r.get("score") or 0)
    except Exception:
        return 0


def r11_no_card_below_fit_60(rows):
    # THE FIT FLOOR, as a release gate: no card below fit 60 may SHIP, i.e. may sit in a report that has not been
    # delivered yet (the next report + anything dated ahead of it). That is what the gate controls.
    # SCOPE (2026-10-09, honest): cards ALREADY delivered are in the client's hands and in client_deliveries —
    # they cannot be recalled or re-scored into the past, so they are reported here as legacy, not as a live fail.
    t = _today_chile()
    shipping = [r for r in _approved_shippable(rows) if (r.get("source_date") or "") > t]
    low = [r for r in shipping if _fit(r) < 60]
    legacy = [r for r in _approved_shippable(rows) if _dated(r) and r["source_date"] <= t and _fit(r) < 60]
    return not low, "%d of %d shipping cards below fit 60 (%s); legacy already-delivered below 60: %d (in the client's hands, not recallable)" % (
        len(low), len(shipping),
        ", ".join("%s=%s" % ((r.get("lead_data") or {}).get("companyName") or r.get("id"), int(_fit(r))) for r in sorted(low, key=_fit)[:6]) or "none",
        len(legacy))


_UNI = re.compile(r"universidad|university|\bespol\b|\bespae\b|\busfq\b|\buda\b|polit[eé]cnica|escuela polit|instituto|college|facultad|campus", re.I)


def r12_company_contact_caps(rows):
    # Company caps: max 1 contact per company per report (source_date) AND max 2 per company overall.
    # UNIVERSITIES are EXEMPT (operator decision 2026-10-09: in-ICP, used for partnerships, several contacts fine).
    import collections, re
    def ck(r):
        c = ((r.get("lead_data") or {}).get("companyName") or r.get("company") or "").lower()
        c = re.sub(r"\b(sa|s\.a\.|ltda|cia|c\.a\.|inc|llc|corp|group|grupo|del ecuador|ecuador)\b", "", c)
        return re.sub(r"[^a-z0-9]+", "", c)
    def is_uni(r):
        return bool(_UNI.search(((r.get("lead_data") or {}).get("companyName") or r.get("company") or "")))
    # Only cards IN A REPORT count: the pool may legitimately hold 3 contacts at one company (the gate decides which
    # 2 ever ship), and every pooled card shares the same empty date, which would read as one giant report.
    sh = [r for r in _approved_shippable(rows) if _dated(r) and not is_uni(r)]   # universities exempt from caps
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
    # SCREEN-LEVEL (operator 2026-10-08/09): sidebar badge == page header == ledger, from the LIVE screen.
    # Both the Decisores badge and header now read ONE function (clientCounts) in the deployed app.html, so they are
    # equal BY CONSTRUCTION; this rule verifies (a) the live app wires them to clientCounts with NO leftover
    # divergent badge formula, and (b) that single value == the ledger. FAILs on a stale deploy or a reintroduced
    # second formula. (The old divergent path was load()'s `_n = UNIVERSE.filter(approved).length`, no dedup -> 54.)
    import urllib.request
    ledger = deliveries.count(CLIENT)
    value = _screen_decisores(rows)            # the single clientCounts() value (email-deduped delivered)
    try:
        req = urllib.request.Request("https://app.ejetheagency.com/app.html", headers={"User-Agent": "golden/1.0", "Cache-Control": "no-cache"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        return False, "cannot fetch live app.html: %s" % str(e)[:60]
    one_source = ("function clientCounts(" in html) and ("window.__ejeSyncBadges" in html)
    no_divergent = "var _n=(CLIENTCLEAN()" not in html   # the old no-dedup badge formula must be gone from the live screen
    ok = (value == ledger) and one_source and no_divergent
    return ok, "single-source value=%d, ledger=%d, live one-source=%s, no-old-formula=%s" % (
        value, ledger, one_source, no_divergent)


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


def r16_next_report_is_top_of_pool(rows):
    # THE RELEASE GATE, reconciled: the report the client will open next must BE the top N of the pool as ranked
    # right now (fit floor + one-person-one-card + company caps), not an older night's pick. Re-derives the
    # assembly read-only (apply=False) and compares it to what is actually dated in the DB. This FAILS on a stale
    # pre-scheduled report, on a veto that was never backfilled, and on hand-dated cards that skipped the gate.
    from factory.workers import release
    t = _today_chile()
    live = {r["id"] for r in _approved_shippable(rows) if (r.get("source_date") or "") > t}
    plan = release.assemble(CLIENT, apply=False)
    if plan.get("error"):
        return False, "cannot re-derive the assembly: %s" % plan["error"]
    want = {c["id"] for c in plan["cards"]}
    missing, extra = sorted(want - live), sorted(live - want)
    short = plan.get("short") or 0
    return (not missing and not extra), "next report %s: live=%d, ranker wants=%d%s; missing=%s; not-in-top-N=%s" % (
        plan["target_date"], len(live), len(want),
        ("  (SHORT by %d — pool exhausted at fit>=%d, NOT padded)" % (short, release.FIT_FLOOR)) if short else "",
        missing[:5] or "none", extra[:5] or "none")


def r17_report_tabs_on_screen(rows):
    # SCREEN-LEVEL: the Reporte tabs the client actually sees. EXACT app.html clientCounts() algorithm (app.html:1748)
    #   repAll = approved && source_date >= today && pitchEmailES, deduped one-person-one-card; grouped by date.
    # Two rules in one, both as rendered: every tab holds <= the contract volume, and no tab exists beyond the NEXT
    # business day (a third tab = the factory pre-scheduling again). Also asserts the POOL is invisible: an undated
    # card must never become a tab, which is only true while the live screen filters Historial on a real date.
    from factory.packages import calendar_bd as _cal
    import collections, urllib.request
    vol = _contract_volume()
    t = _today_chile()
    nxt = _cal.next_business_day(datetime.date.fromisoformat(t) + datetime.timedelta(days=1), COUNTRY).isoformat()
    sel, seen = [], set()
    for r in sorted(rows, key=lambda x: (x.get("source_date") or "")):
        ld = r.get("lead_data") or {}
        if not (ld.get("approved") and (r.get("source_date") or "") >= t and (ld.get("pitchEmailES") or "").strip()):
            continue
        k = _ckey(r) or _dom(r)          # app.html _personKey: one person = one card
        if k in seen:
            continue
        seen.add(k); sel.append(r)
    tabs = collections.Counter(r["source_date"] for r in sel)
    oversize = {d: n for d, n in tabs.items() if n > vol}
    beyond = [d for d in tabs if d > nxt]
    try:
        req = urllib.request.Request("https://app.ejetheagency.com/app.html", headers={"User-Agent": "golden/1.0", "Cache-Control": "no-cache"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        return False, "cannot fetch live app.html: %s" % str(e)[:60]
    pool_hidden = "l.approved===true && !!(l.source_date" in html   # client Historial shows dated reports only
    ok = (vol > 0 and not oversize and not beyond and pool_hidden)
    return ok, "tabs on screen=%s (max %d/tab, horizon %s); oversize=%s; beyond-horizon=%s; pool hidden from client=%s" % (
        dict(sorted(tabs.items())), vol, nxt, oversize or "none", beyond or "none", pool_hidden)


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
    # NEW 2026-10-09 (the release gate = just-in-time assembly):
    ("next report == top N of the ranked pool (nothing inherited from an old night)", lambda rows: r16_next_report_is_top_of_pool(rows)),
    ("client screen: every report tab <= 20 cards, none beyond the next business day, pool invisible", lambda rows: r17_report_tabs_on_screen(rows)),
    ("client Decisores: sidebar badge == page header == ledger (one source)", lambda rows: r15_client_counts_single_source(rows)),
    # NEW 2026-10-09 (the Oct 9 holiday leak taken back):
    ("no un-actioned card stays delivered on a non-business day", lambda rows: r18_no_unactioned_card_stays_delivered_on_a_holiday(rows)),
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
