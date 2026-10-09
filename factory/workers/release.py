# factory/workers/release.py
# THE RELEASE GATE — just-in-time report assembly (operator 2026-10-09; replaces the old pre-scheduling DRIP).
#
# WHY: the drip assigned source_dates days ahead, so a report was frozen the night it was dripped. Cards that were
# the best available on Tuesday still shipped on Friday after the pool had better ones, short days got padded with
# whatever was left, and low-fit cards rode along because they already had a date. A report must be the BEST 20 the
# pool can offer on the morning it ships, not the leftovers of an old night.
#
# THE MODEL (two states, one date field):
#   POOL   = source_date IS NULL. Enriched, gate-passed, waiting. Invisible to the client (app.html's
#            _deliveredToClient demands a non-empty source_date), re-ranked every night, nothing expires.
#   REPORT = source_date = one business day. The ONLY way into a client's report is this gate.
#   DELIVERED = source_date <= today. Frozen forever: a card the client has already seen never moves and never
#            vanishes (it is in client_deliveries, which is what the Decisores count reads).
#            ONE exception, operator 2026-10-09: a card dated by a BUG that the client NEVER ACTED ON can be
#            taken back (undeliver / undeliver_date): nothing of his is undone, and the lead is not burned on a
#            day nobody worked. A card he acted on is never revocable, whatever put the date there.
#
# EVERY NIGHT, per client: return every undelivered dated card to the pool, rank the whole pool against the client's
# CURRENT ICP, and build ONLY the next business day's report from the top N. Rules, all enforced below:
#   - fit >= FIT_FLOOR (60). A card under the floor never ships; it stays pooled and is re-ranked tomorrow.
#   - one person = one card (dedup by contact email, inside the report and against the delivered ledger).
#   - company caps: a NON-university company gets max 1 card per report and max 2 across all reports ever.
#     Universities are EXEMPT (operator 2026-10-09: in-ICP, partnership play, several contacts are fine).
#   - NEVER pad: if fewer than N clear the bar, the report ships short and says so (the funnel email flags it).
#   - operator veto: lead_data.vetoed drops a card out of the report and out of the pool, permanently; the next
#     best card takes its place on the next assembly (which is the same night, so a veto is same-day effective).
#
# FIT is the card's OWN score (lead_data.score) — the one number the client's card shows, golden r11 checks and this
# ranker sorts by. One source, no second opinion computed in the dark.
#
#   python3 -m factory.workers.release <client>                  # assemble the next business day (dry-run preview)
#   python3 -m factory.workers.release <client> --apply
#   python3 -m factory.workers.release <client> --veto <lead_id> "reason"
#   python3 -m factory.workers.release <client> --undeliver <lead_id> "reason" [--apply]
#   python3 -m factory.workers.release <client> --undeliver-date <YYYY-MM-DD> "reason" [--apply]
import datetime, re
from factory.packages import db, calendar_bd as cal
from factory.workers import tsa, deliveries

FIT_FLOOR = 60          # operator 2026-10-09: no card below this ships, ever. Not a knob to open on a short day.
HOLD_DATE = "2099-01-01"  # TSA's "never show" sentinel (tsa.clean_surface) — not a report, never un-scheduled here

_UNI = re.compile(r"universidad|university|\bespol\b|\bespae\b|\busfq\b|\buda\b|polit[eé]cnica|escuela polit|"
                  r"instituto|college|facultad|campus", re.I)
_CO_NOISE = re.compile(r"\b(sa|s\.a\.|ltda|cia|c\.a\.|inc|llc|corp|group|grupo|del ecuador|ecuador)\b")

LEAD_COLS = "id,company,contact_name,contact_email,score,status,source_date,updated_at,lead_data"


def _ld(r):
    return r.get("lead_data") or {}


def company_key(r):
    c = _CO_NOISE.sub("", (_ld(r).get("companyName") or r.get("company") or "").lower())
    return re.sub(r"[^a-z0-9]+", "", c)


def is_university(r):
    return bool(_UNI.search(_ld(r).get("companyName") or r.get("company") or ""))


def contact_key(r):
    return ((_ld(r).get("contactEmail") or r.get("contact_email") or "")).strip().lower()


def fit_of(r):
    """The card's fit against the client's ICP: lead_data.score (what the card shows, what golden r11 reads)."""
    try:
        return int(float(_ld(r).get("score") or r.get("score") or 0))
    except Exception:
        return 0


def channels_of(r):
    """Reachable channels on the card (multi-channel doctrine): email + IG + LinkedIn + WhatsApp."""
    ld = _ld(r)
    n = 1 if (r.get("contact_email") or ld.get("contactEmail")) else 0
    if ld.get("instagramHandle"):
        n += 1
    if ld.get("contactLinkedIn") or ld.get("companyLinkedIn"):
        n += 1
    if ld.get("whatsapp"):
        n += 1
    return n


def completeness_of(r):
    """How finished the card is: the five fields that decide whether it reads as a real decisor card on screen."""
    ld = _ld(r)
    return sum(1 for v in (ld.get("logo"), ld.get("companyBrief"), ld.get("website"),
                           ld.get("contactTitle"), ld.get("pitchEmailES")) if (v or "").strip())


def freshness_of(r):
    """Signal freshness: a card carrying why-now signals, enriched recently, outranks an equal-fit stale one."""
    ld = _ld(r)
    s = 5 if (ld.get("whyNow") or []) else 0
    up = (r.get("updated_at") or "")[:10]
    if up:
        try:
            age = (datetime.date.today() - datetime.date.fromisoformat(up)).days
            s += 3 if age <= 14 else (1 if age <= 45 else 0)
        except Exception:
            pass
    return s


def rank_of(r):
    """Rank = fit (primary, and the only floor) + the operator's three tie-breakers, all additive and visible."""
    return fit_of(r) + 4 * channels_of(r) + 2 * completeness_of(r) + freshness_of(r)


def _why_not(r, delivered_keys, today):
    """Why this card is not a candidate for the next report. None = eligible."""
    ld = _ld(r)
    if (r.get("status") or "none") != "none":
        return "already in the lifecycle (%s)" % r.get("status")
    if ld.get("reportLocked"):
        return "locked into the %s report" % (r.get("source_date") or "?")
    if ld.get("vetoed"):
        return "vetoed by operator"
    if not ld.get("approved"):
        return "not approved (staged for review)"
    if not tsa.passes_lead_row(r):
        return "not shippable (TSA: decisor + verified email)"
    sd = r.get("source_date") or ""
    if sd and sd <= today:
        return "already delivered"
    if contact_key(r) in delivered_keys:
        return "this person was already delivered"
    if fit_of(r) < FIT_FLOOR:
        return "fit < %d" % FIT_FLOOR
    return None


def _config(client_id):
    ic = ((db.select("clients", "id=eq.%s&select=icp_config" % client_id) or [{}])[0].get("icp_config") or {})
    return int(ic.get("ready_leads_per_day") or 20), ic.get("geo")


def min_universities(client_id):
    """Per-client floor on how many university cards a report must carry (icp_config.min_universities_per_report).

    Why it exists (operator 2026-10-09): with the repaired scorer, SMB owner cards legitimately out-rank academic
    decisors, and a pure fit ranking took 2uplatam's reports from 12 universities to 4. The university segment is
    a deliberate bet (partnership play, several contacts per institution allowed), not a scoring accident, so the
    MIX is configured instead of being whatever the ranking happens to produce. 0 = no minimum (every other client)."""
    ic = ((db.select("clients", "id=eq.%s&select=icp_config" % client_id) or [{}])[0].get("icp_config") or {})
    return int(ic.get("min_universities_per_report") or 0)


def pool(client_id):
    """The ranked pool: every card that COULD ship in the next report, best first, plus why the rest cannot."""
    today = datetime.date.today().isoformat()
    rows = db.select_all("leads", "client_id=eq.%s&select=%s" % (client_id, LEAD_COLS))
    try:
        delivered = deliveries.delivered_keys(client_id)
    except Exception:
        delivered = set()
    ranked, rejected = [], {}
    for r in rows:
        why = _why_not(r, delivered, today)
        if why:
            rejected[why.split(" (")[0]] = rejected.get(why.split(" (")[0], 0) + 1
        else:
            ranked.append(r)
    ranked.sort(key=lambda r: (-rank_of(r), -fit_of(r), r["id"]))
    return {"rows": rows, "ranked": ranked, "rejected": rejected, "today": today, "delivered_keys": delivered}


def assemble(client_id, target_date=None, apply=False):
    """Build ONE report: the next business day, top N of the ranked pool, caps + dedup + fit floor enforced.
    Idempotent: every undelivered dated card goes back to the pool first, so re-running rebuilds the same report
    from the same pool. Delivered cards (source_date <= today) are never touched."""
    per_day, country = _config(client_id)
    p = pool(client_id)
    today = p["today"]
    target = target_date or cal.next_business_day(datetime.date.today(), country).isoformat()
    if not cal.is_business_day(target, country):
        return {"client_id": client_id, "error": "%s is not a business day in %s" % (target, country)}

    # 0) A LOCKED REPORT IS FINAL. Normally a dated-but-undelivered report goes back to the pool every night and is
    #    reassembled, which is the whole point of the gate. A lock is the operator saying "this one is settled, do
    #    not reshuffle it": used when a scoring change lands and the imminent report must ship as reviewed.
    #    The gate builds ONLY the next business day, so if that day is locked there is nothing to assemble tonight.
    locked_on_target = [r for r in p["rows"] if (r.get("source_date") or "") == target and _ld(r).get("reportLocked")]
    if locked_on_target:
        return {"client_id": client_id, "target_date": target, "applied": False, "locked": True,
                "shipped": len(locked_on_target), "target_size": per_day, "short": 0,
                "lowest_fit": min([fit_of(r) for r in locked_on_target], default=None),
                "highest_fit": max([fit_of(r) for r in locked_on_target], default=None),
                "universities": sum(1 for r in locked_on_target if is_university(r)),
                "line": "release %s %s: LOCKED (%d cards, reviewed and final), nothing reassembled" % (
                    client_id, target, len(locked_on_target))}

    # 1) UN-SCHEDULE: nothing keeps a future date. A report is assembled, never inherited. A LOCKED card keeps its
    #    date (it is a settled report, not an inherited one) and is excluded from the pool by _why_not.
    returned = [r for r in p["rows"]
                if (r.get("source_date") or "") > today and (r.get("source_date") or "") != HOLD_DATE
                and not _ld(r).get("tsa_held") and not _ld(r).get("reportLocked")]
    if apply:
        for r in returned:
            _set_date(client_id, r, None)

    # 2) COUNT WHAT IS ALREADY OUT: company caps count across every report ever delivered.
    delivered_rows = [r for r in p["rows"] if (r.get("source_date") or "") and (r.get("source_date") or "") <= today
                      and _ld(r).get("approved") and tsa.passes_lead_row(r)]
    overall = {}
    for r in delivered_rows:
        if not is_university(r):
            k = company_key(r)
            overall[k] = overall.get(k, 0) + 1

    # 3) FILL the target day. TWO PASSES when the client sets a university minimum: the best UNIVERSITIES first
    #    (up to the minimum), then the best of everything else. Within each pass it is still pure rank order, and
    #    the fit floor + caps + one-person-one-card still decide every single pick.
    #
    #    THE MINIMUM CAN NEVER SHORTEN A REPORT OR PAD ONE, and that is structural rather than careful: the second
    #    pass fills to per_day from the WHOLE ranked pool, and the ranked pool only ever holds cards at or above the
    #    fit floor. A university shortfall therefore lands in the MIX and nowhere else. Verified by forcing a
    #    minimum the pool cannot supply (8 required, 3 available): still 20 cards, short=0, nothing under the floor.
    #    A thin mix prints YELLOW in the nightly review ("universities 5/8"), never red and never an alert: it says
    #    university discovery is behind, not that the report is wrong.
    picked, in_report_companies, seen_people, blocked = [], set(), set(p["delivered_keys"]), {}
    min_uni = min_universities(client_id)

    picked_ids = set()

    def take(candidates, limit):
        for r in candidates:
            if len(picked) >= limit:
                break
            if r["id"] in picked_ids:       # already taken by the university pass; not a "blocked" card
                continue
            ck, k, uni = contact_key(r), company_key(r), is_university(r)
            if ck and ck in seen_people:
                blocked["one person = one card"] = blocked.get("one person = one card", 0) + 1
                continue
            if not uni and k:
                if k in in_report_companies:
                    blocked["max 1 per company per report"] = blocked.get("max 1 per company per report", 0) + 1
                    continue
                if overall.get(k, 0) >= 2:
                    blocked["max 2 per company overall"] = blocked.get("max 2 per company overall", 0) + 1
                    continue
            picked.append(r)
            picked_ids.add(r["id"])
            if ck:
                seen_people.add(ck)
            if not uni and k:
                in_report_companies.add(k)
                overall[k] = overall.get(k, 0) + 1

    if min_uni:
        take([r for r in p["ranked"] if is_university(r)], min(min_uni, per_day))
    take(p["ranked"], per_day)      # the rest of the day, best first, universities included on merit
    if apply:
        for r in picked:
            _set_date(client_id, r, target)

    short = max(0, per_day - len(picked))
    eligible_left = len(p["ranked"]) - len(picked)
    out = {
        "client_id": client_id, "target_date": target, "applied": bool(apply),
        "shipped": len(picked), "target_size": per_day, "short": short,
        "lowest_fit": min([fit_of(r) for r in picked], default=None),
        "highest_fit": max([fit_of(r) for r in picked], default=None),
        "universities": sum(1 for r in picked if is_university(r)),
        "returned_to_pool": len(returned),
        "pool_eligible_after": eligible_left,
        "days_covered": round(eligible_left / float(per_day), 1) if per_day else 0,
        "pool_blocked_by_caps": blocked, "pool_rejected": p["rejected"],
        "cards": [{"id": r["id"], "company": _ld(r).get("companyName") or r.get("company"),
                   "contact": _ld(r).get("contactName") or r.get("contact_name"),
                   "fit": fit_of(r), "rank": rank_of(r), "uni": is_university(r)} for r in picked],
    }
    out["line"] = "release %s %s: %d/%d cards (fit %s-%s, %d universities), pool %d eligible = %.1f more days%s" % (
        client_id, target, out["shipped"], per_day, out["lowest_fit"], out["highest_fit"], out["universities"],
        eligible_left, out["days_covered"], "" if not short else "  <-- SHORT by %d, NOT padded (nothing else clears fit>=%d)" % (short, FIT_FLOOR))
    return out


def _set_date(client_id, row, date_iso):
    """Move a card between the pool (None) and a report (a business day). lead_data.source_date mirrors the column
    because app.html falls back to it when reading a card. A card in a report is by definition not TSA-held."""
    ld = _ld(row)
    ld["source_date"] = date_iso or ""
    if date_iso:
        ld.pop("tsa_held", None)
    db.update("leads", "id=eq.%s&client_id=eq.%s" % (row["id"], client_id),
              {"source_date": date_iso, "lead_data": ld})


def veto(client_id, lead_id, reason="", by="operator"):
    """Operator veto: this card never ships. Out of the next report immediately (back to no date) and out of the
    pool permanently; the next best card replaces it on the next assembly."""
    rows = db.select("leads", "id=eq.%s&client_id=eq.%s&select=%s" % (lead_id, client_id, LEAD_COLS))
    if not rows:
        return {"error": "no such lead for %s: %s" % (client_id, lead_id)}
    r = rows[0]
    today = datetime.date.today().isoformat()
    if (r.get("source_date") or "") and (r.get("source_date") or "") <= today:
        return {"error": "%s was already delivered on %s — a card the client has seen cannot be vetoed"
                         % (lead_id, r["source_date"])}
    ld = _ld(r)
    ld.update({"vetoed": True, "vetoReason": reason, "vetoedBy": by,
               "vetoedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_date": ""})
    db.update("leads", "id=eq.%s&client_id=eq.%s" % (lead_id, client_id), {"source_date": None, "lead_data": ld})
    return {"client_id": client_id, "lead_id": lead_id, "vetoed": True, "reason": reason,
            "line": "vetoed %s (%s) — out of the report and the pool; re-assemble to backfill" % (lead_id, reason or "no reason given")}


def lock_report(client_id, date_iso, by="operator", apply=False):
    """Freeze one dated report so the nightly gate stops reassembling it (operator 2026-10-09).

    Used when the scoring regime changes under an imminent report: Monday's 20 cards were reviewed under the old
    scores and must ship as reviewed, while the re-scored pool feeds Tuesday onward. A locked card keeps its date,
    is not returned to the pool, and cannot be picked for another day."""
    rows = db.select_all("leads", "client_id=eq.%s&source_date=eq.%s&select=%s" % (client_id, date_iso, LEAD_COLS))
    cards = [r for r in rows if _ld(r).get("approved")]
    if apply:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for r in cards:
            ld = _ld(r)
            ld["reportLocked"] = True
            ld["reportLockedBy"] = by
            ld["reportLockedAt"] = now
            db.update("leads", "id=eq.%s&client_id=eq.%s" % (r["id"], client_id), {"lead_data": ld})
    return {"client_id": client_id, "date": date_iso, "applied": bool(apply), "locked": len(cards),
            "line": "%s %s: %d cards locked%s" % (client_id, date_iso, len(cards), "" if apply else "  (DRY RUN)")}


def unlock_report(client_id, date_iso, apply=False):
    """Release a lock so the gate reassembles that day again. A lock with no way out would be a one-way door:
    a stale one could stop a day from ever rebuilding (PLAN item 9b makes past-dated locks expire by themselves)."""
    rows = db.select_all("leads", "client_id=eq.%s&source_date=eq.%s&select=%s" % (client_id, date_iso, LEAD_COLS))
    cards = [r for r in rows if _ld(r).get("reportLocked")]
    if apply:
        for r in cards:
            ld = _ld(r)
            for k in ("reportLocked", "reportLockedBy", "reportLockedAt"):
                ld.pop(k, None)
            db.update("leads", "id=eq.%s&client_id=eq.%s" % (r["id"], client_id), {"lead_data": ld})
    return {"client_id": client_id, "date": date_iso, "applied": bool(apply), "unlocked": len(cards),
            "line": "%s %s: %d cards unlocked%s" % (client_id, date_iso, len(cards), "" if apply else "  (DRY RUN)")}


def undeliver(client_id, lead_id, reason="", by="operator", apply=False, t=None):
    """Take back a card the client NEVER ACTED ON and return it to the pool (operator 2026-10-09).

    A delivered card is normally frozen forever, and that stays true for every card the client USED: if he sent,
    stepped, re-statused or filed it, he really received it and it keeps its date and its ledger row. The one
    revocable case is a card that was dated by a BUG and sat untouched (the publish leak that dated cards the night
    they were published put a report on the Oct 9 Ecuador holiday). Untouched means nothing is undone by taking it
    back, and leaving it delivered would burn a real lead on a day nobody worked.

    Un-delivering = out of the client's view (source_date NULL -> pool, invisible), out of the ledger (so Decisores
    stops counting it) with the reason logged, and back in the ranked pool so the gate can ship it on a real
    business day IF it still ranks. The card keeps approved=true: it is pool-eligible, not rejected."""
    rows = db.select("leads", "id=eq.%s&client_id=eq.%s&select=%s" % (lead_id, client_id, LEAD_COLS))
    if not rows:
        return {"error": "no such lead for %s: %s" % (client_id, lead_id)}
    r = rows[0]
    today = datetime.date.today().isoformat()
    sd = r.get("source_date") or ""
    if not (sd and sd <= today):
        return {"error": "%s is not delivered (source_date=%r), nothing to take back" % (lead_id, sd)}
    t = t or deliveries.touched(client_id)
    if deliveries.is_actioned(r, t):
        return {"error": "%s WAS ACTIONED by the client: a card he used stays delivered" % lead_id,
                "lead_id": lead_id, "actioned": True}
    ck = contact_key(r)
    if not apply:
        return {"client_id": client_id, "lead_id": lead_id, "was_date": sd, "contact_key": ck,
                "undelivered": False, "applied": False, "reason": reason,
                "line": "would un-deliver %s (dated %s, never actioned) -> pool" % (lead_id, sd)}
    ld = _ld(r)
    ld["source_date"] = ""
    ld["undelivered"] = {"wasDate": sd, "reason": reason, "by": by,
                         "at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    db.update("leads", "id=eq.%s&client_id=eq.%s" % (lead_id, client_id), {"source_date": None, "lead_data": ld})
    removed = deliveries.revoke(client_id, ck, lead_id, reason) if ck else 0
    return {"client_id": client_id, "lead_id": lead_id, "was_date": sd, "contact_key": ck,
            "undelivered": True, "applied": True, "ledger_rows_removed": removed, "reason": reason,
            "line": "un-delivered %s (was %s, never actioned) -> pool; ledger rows removed %d" % (lead_id, sd, removed)}


def pool_dated_unapproved(client_id, date_iso, reason="", by="operator", apply=False):
    """Return to the pool every UN-APPROVED card holding a given report date (operator 2026-10-09, queue item 0).

    An un-approved card is invisible to the client (app.html demands `approved`), so a report date on it means
    nothing today and is a trap tomorrow: the day it gets approved it instantly reads as DELIVERED on that past
    date, with no one having ever seen it. The Oct 9 publish leak left 4 such rows on the Ecuador holiday.
    Un-approved means no date. This touches no client-visible card: an approved row on the date is skipped."""
    rows = db.select_all("leads", "client_id=eq.%s&source_date=eq.%s&select=%s" % (client_id, date_iso, LEAD_COLS))
    targets = [r for r in rows if not _ld(r).get("approved")]
    skipped = [r["id"] for r in rows if _ld(r).get("approved")]
    for r in targets:
        if apply:
            ld = _ld(r)
            ld["source_date"] = ""
            ld["pooledFrom"] = {"wasDate": date_iso, "reason": reason, "by": by,
                                "at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            db.update("leads", "id=eq.%s&client_id=eq.%s" % (r["id"], client_id),
                      {"source_date": None, "lead_data": ld})
    return {"client_id": client_id, "date": date_iso, "applied": bool(apply),
            "pooled": sorted(r["id"] for r in targets), "left_alone_approved": sorted(skipped),
            "line": "%s %s: %d un-approved cards -> pool, %d approved left alone%s" % (
                client_id, date_iso, len(targets), len(skipped), "" if apply else "  (DRY RUN)")}


def undeliver_date(client_id, date_iso, reason="", by="operator", apply=False):
    """Take back every UN-ACTIONED card delivered on one date (the leak case: a whole report on a non-business
    day). Cards the client acted on are listed and LEFT delivered. Backs the ledger up before touching it."""
    rows = db.select_all("leads", "client_id=eq.%s&source_date=eq.%s&select=%s" % (client_id, date_iso, LEAD_COLS))
    cards = [r for r in rows if _ld(r).get("approved")]        # only cards the client could actually see
    t = deliveries.touched(client_id)
    acted = [r["id"] for r in cards if deliveries.is_actioned(r, t)]
    if apply and cards:
        deliveries.backup_ledger(client_id)
    done, errors = [], []
    for r in cards:
        if r["id"] in acted:
            continue
        res = undeliver(client_id, r["id"], reason=reason, by=by, apply=apply, t=t)
        (errors if res.get("error") else done).append(res)
    return {"client_id": client_id, "date": date_iso, "applied": bool(apply),
            "cards_on_date": len(cards), "not_approved_on_date": len(rows) - len(cards),
            "actioned_kept_delivered": acted, "undelivered": [d["lead_id"] for d in done], "errors": errors,
            "line": "%s %s: %d client-visible cards, %d actioned (kept), %d un-delivered -> pool%s" % (
                client_id, date_iso, len(cards), len(acted), len(done), "" if apply else "  (DRY RUN)")}


def assemble_all(only=None, apply=True):
    """Assemble the next business day's report for every client with a daily volume (EJE's own pool + the library
    are not client reports; archived clients are OFF)."""
    from factory.workers import client_status
    targets = [c["id"] for c in db.select("clients", "select=id,icp_config")
               if (c.get("icp_config") or {}).get("ready_leads_per_day") and c["id"] not in ("eje", "eje_productoras")
               and not client_status.is_archived(c.get("icp_config"))]
    if only:
        targets = [t for t in targets if t == only]
    return {cid: assemble(cid, apply=apply) for cid in targets}


if __name__ == "__main__":
    import sys, json
    cid = sys.argv[1] if len(sys.argv) > 1 else "2uplatam"
    if "--veto" in sys.argv:
        i = sys.argv.index("--veto")
        print(json.dumps(veto(cid, sys.argv[i + 1], sys.argv[i + 2] if len(sys.argv) > i + 2 else ""), indent=2))
    elif "--undeliver-date" in sys.argv:
        i = sys.argv.index("--undeliver-date")
        reason = sys.argv[i + 2] if len(sys.argv) > i + 2 and not sys.argv[i + 2].startswith("--") else ""
        res = undeliver_date(cid, sys.argv[i + 1], reason=reason, apply="--apply" in sys.argv)
        print(json.dumps(res, indent=2, ensure_ascii=False)); print(res["line"])
    elif "--undeliver" in sys.argv:
        i = sys.argv.index("--undeliver")
        reason = sys.argv[i + 2] if len(sys.argv) > i + 2 and not sys.argv[i + 2].startswith("--") else ""
        res = undeliver(cid, sys.argv[i + 1], reason=reason, apply="--apply" in sys.argv)
        print(json.dumps(res, indent=2, ensure_ascii=False)); print(res.get("line") or res.get("error"))
    else:
        res = assemble(cid, apply="--apply" in sys.argv)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print(res.get("line") or res.get("error"))
