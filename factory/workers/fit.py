# factory/workers/fit.py
# Profile-aware FIT score (the "best-lead signals" doctrine). Measures how well a lead matches THIS client's ICP,
# config-driven from icp_config, NOT a generic enrichment checklist. Two rules the old checklist broke:
#  1. differentiate on what the PROFILE cares about (e.g. 2uplatam = decisoras mujeres + owner seniority + geo);
#  2. NEVER score a lead down for data we didn't mine / channels the ICP doesn't have -> unknown is not penalized,
#     it just isn't added, and a strong lead on what we DO know reads high (~90), not capped at 72.
import re
import unicodedata

_FEM = {"natali", "nataly", "nathaly", "raquel", "isabel", "pilar", "carmen", "mercedes", "dolores", "beatriz",
        "ines", "ruth", "flor", "abril", "noelia", "soledad", "consuelo", "rocio", "azucena"}
_MASC_A = {"garcia", "sosa", "costa", "matias", "elias", "tobias", "josue", "luca", "andrea", "bautista", "isaias", "zacarias"}
_OWNER = re.compile(r"owner|founder|co-?found|ceo|due[nñ][ao]|fundador[a]?|socia?o|partner|president[ae]?|titular|director general|gerente general", re.I)
_MID = re.compile(r"director|gerente|head|jefe|lead|manager|encargad|coordinad", re.I)


def _is_female(name):
    toks = [t for t in re.split(r"[^a-z]+", "".join(c for c in unicodedata.normalize("NFD", (name or "").lower())
            if unicodedata.category(c) != "Mn")) if len(t) > 1]
    if not toks:
        return False
    f = toks[0]
    if f in _FEM:
        return True
    if f in _MASC_A:
        return False
    return f.endswith("a")


def fit_score(co, ct, signals, ic):
    co, ct, ic = co or {}, ct or {}, ic or {}
    s = 0.0
    title = (ct.get("title") or "").lower()
    name = ct.get("full_name") or ""
    # --- decisor seniority (owner-level is the best fit for owner-verifiable ICPs) ---
    if _OWNER.search(title):
        s += 40
    elif _MID.search(title):
        s += 25
    elif title.strip():
        s += 12
    # --- decisor gender preference (e.g. 2uplatam wants decisoras mujeres) ---
    pref_female = bool(ic.get("prefer_female_decisor")) or (ic.get("decisor") == "mujeres")
    if pref_female:
        if _is_female(name):
            s += 25
        # male/unknown: NOT penalized, just no fit bonus
    else:
        s += 15  # gender isn't a criterion for this profile -> neutral credit (don't cap non-pref clients)
    # --- geo match ---
    geo = (ic.get("geo") or "").lower()
    cc = (co.get("country") or "").lower()
    if not geo:
        s += 20
    elif cc and geo in cc:
        s += 20
    # (wrong geo = 0; it genuinely doesn't fit)
    # --- quality signals / traction (what we HAVE mined) ---
    foll = co.get("instagramFollowers") or 0
    if foll:
        s += min(12, foll / 1000.0 * 3)     # scaled; absent -> not penalized
    s += min(len(signals or []), 3) * 5      # up to 15
    # --- channel richness (secondary, additive; never subtractive) ---
    if co.get("instagram"):
        s += 8
    if co.get("linkedin") or co.get("contactLinkedIn"):
        s += 8
    return int(min(round(s), 100))
