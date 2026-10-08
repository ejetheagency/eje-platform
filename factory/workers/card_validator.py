# factory/workers/card_validator.py
# THE QUALITY STANDARD, IN CODE (operator, 2026-10-07): "the standard lives in code, not in a prompt."
# A published card must carry the fields that make it ready to contact. This validator is the single source of truth
# for what "a good card" means; the nightly reports the % of tonight's cards that pass, so the quality bar is a
# measured number, not a vibe. It does NOT block publish (the gates do that) - it GAUGES card completeness so the
# operator can spot-check and so the enrichment-depth gap is visible every night.
#
# Required on a card (lead_data shape, as app.html reads it):
#   1. named decisor          -> contactName
#   2. verified/soft email    -> contactEmail (publish only sets it when the email passed the gate = verified or soft)
#   3. 2+ channels            -> >=2 of {email, whatsapp, instagram, linkedin}
#   4. logo                   -> logo
#   5. hook fact              -> hookFact, else a non-empty whyNow/whyICP (an offer-relevant reason to reach out)
#   6. per-channel scripts    -> a message for EVERY channel the card actually has (email->pitchEmailES,
#                                whatsapp->whatsappMessage, instagram->instagramDM, linkedin->linkedinDM)


def _has(v):
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, tuple, dict)):
        return len(v) > 0
    return bool(v)


def channels_present(ld):
    ch = []
    if _has(ld.get("contactEmail")):
        ch.append("email")
    if _has(ld.get("whatsapp")):
        ch.append("whatsapp")
    if _has(ld.get("instagramHandle")):
        ch.append("instagram")
    if _has(ld.get("contactLinkedIn")):
        ch.append("linkedin")
    return ch


def validate_card(ld):
    """Return {'ok': bool, 'missing': [reasons]} for one card's lead_data dict."""
    ld = ld or {}
    missing = []
    if not _has(ld.get("contactName")):
        missing.append("named_decisor")
    if not _has(ld.get("contactEmail")):
        missing.append("verified_email")
    ch = channels_present(ld)
    if len(ch) < 2:
        missing.append("two_channels")
    if not _has(ld.get("logo")):
        missing.append("logo")
    if not (_has(ld.get("hookFact")) or _has(ld.get("whyNow")) or _has(ld.get("whyICP"))):
        missing.append("hook_fact")
    # per-channel script for every channel the card HAS (no script for a channel we lack is not a miss)
    script_of = {"email": "pitchEmailES", "whatsapp": "whatsappMessage",
                 "instagram": "instagramDM", "linkedin": "linkedinDM"}
    for c in ch:
        if not _has(ld.get(script_of[c])):
            missing.append("script_" + c)
    return {"ok": not missing, "missing": missing}


def validate_batch(cards):
    """cards = list of lead_data dicts. Returns pass %, counts, and a tally of the most common missing fields."""
    total = len(cards)
    if not total:
        return {"total": 0, "passed": 0, "pct": 0, "missing_tally": {}}
    passed = 0
    miss_tally = {}
    for ld in cards:
        r = validate_card(ld)
        if r["ok"]:
            passed += 1
        for m in r["missing"]:
            miss_tally[m] = miss_tally.get(m, 0) + 1
    return {"total": total, "passed": passed, "pct": round(100 * passed / total),
            "missing_tally": dict(sorted(miss_tally.items(), key=lambda kv: -kv[1]))}
