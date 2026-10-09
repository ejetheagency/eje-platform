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
# OWNER-LEVEL titles. Repaired 2026-10-09 (queue item 1) against the real pooled cards, which showed four classes
# of true decisor scoring the generic +12 because no pattern matched them:
#   - academic heads: Decano/Decana, Rector/Rectora, Vicerrector/a (9 pooled cards). Universities are in-ICP and a
#     Decano runs their faculty's budget; "rector" also covers "vicerrector", both decide for this ICP.
#   - propietario/propietaria/copropietario (3 cards: "Fotografo y propietario", "Chef copropietario",
#     "Dermatologa y propietaria"). Same class as dueño: owner-operated, and the owner IS the decisor.
#   - "Socia": the old `socia?o` only matched socio/sociao, so every female partner missed. Now soci[ao].
#   - titular/propietario variants already intended by the old pattern but never spelled out.
#
# WORD BOUNDARIES ARE LOAD-BEARING on the added alternatives (caught by test_fit before this shipped): without \b,
# "rector" matches inside "di-rector" and promoted EVERY Director to owner-level, and "soci[ao]" matches inside
# "Redes Sociales", "Medios Sociales", "Asociado" and "Trabajadora Social". A false owner match is worse than a
# missed one: it inflates fit, and fit is what decides who the client gets tomorrow.
#
# "DIRECTOR/A" IS CONTEXT-DEPENDENT, and this is the one judgment in the repair worth stating plainly. The operator
# listed Director/a as a decisor title, but the word spans two very different jobs:
#   - directing the ORGANIZATION or the UNIT WE SELL TO = decision authority -> owner-tier:
#     Director General, Director Ejecutivo, and the academic unit heads (Director de Carrera / Escuela / Facultad /
#     Departamento / Instituto / Posgrado). A Director de Carrera runs that program's budget and partnerships; he is
#     the academic analogue of a Decano, and 2uplatam sells exactly into that unit.
#   - directing a CRAFT inside someone else's company = not the decision maker -> stays mid:
#     Director de Arte, Director de Marketing, Director Creativo. Promoting those would inflate every agency lead.
_OWNER = re.compile(r"owner|founder|co-?found|ceo|due[nñ][ao]|fundador[ao]?|partner|president[ae]?|titular|"
                    r"\bsoci[ao]\b|\bco-?propietari[ao]\b|\bpropietari[ao]\b|\bsub-?decan[ao]\b|\bdecan[ao]\b|"
                    r"\bvicerrector[ao]?\b|\brector[ao]?\b|director general|gerente general|"
                    r"director[ao]? ejecutiv[ao]|"
                    r"\b(?:director[ao]?|jefe|jefa) de (?:carrera|escuela|facultad|departamento|instituto|posgrado)\b",
                    re.I)
_MID = re.compile(r"director|gerente|head|jefe|lead|manager|encargad|coordinad", re.I)

# Country of operation, when companies.country is empty (it is empty for 28 of the 29 pooled cards that have a
# companies row, so geo silently cost a correct Ecuador lead its 20 points). ccTLD + phone dial code, both free and
# deterministic. companies has no address column, so address is not a usable source here.
_TLD_COUNTRY = {"ec": "Ecuador", "mx": "Mexico", "co": "Colombia", "cl": "Chile", "pe": "Peru", "ar": "Argentina",
                "br": "Brazil", "uy": "Uruguay", "py": "Paraguay", "bo": "Bolivia", "ve": "Venezuela",
                "cr": "Costa Rica", "pa": "Panama", "gt": "Guatemala", "do": "Dominican Republic", "es": "Spain"}
_DIAL_COUNTRY = {"593": "Ecuador", "52": "Mexico", "57": "Colombia", "56": "Chile", "51": "Peru", "54": "Argentina",
                 "55": "Brazil", "598": "Uruguay", "595": "Paraguay", "591": "Bolivia", "58": "Venezuela",
                 "506": "Costa Rica", "507": "Panama", "502": "Guatemala", "34": "Spain"}


def geo_country(co, ct=None):
    """The lead's country: the stored value first, then the domain's ccTLD, then the phone's dial code.
    Returns "" when nothing says where this company operates (and unknown is never penalized, per the header)."""
    co, ct = co or {}, ct or {}
    c = (co.get("country") or "").strip()
    if c:
        return c
    host = (co.get("domain") or co.get("website") or "").lower()
    host = re.sub(r"^https?://", "", host).split("/")[0]
    parts = [p for p in host.split(".") if p]
    if parts:                                  # example.com.ec -> "ec"; example.ec -> "ec"
        tld = parts[-1]
        if tld in _TLD_COUNTRY:
            return _TLD_COUNTRY[tld]
    phone = re.sub(r"[^\d+]", "", (ct.get("phone") or co.get("whatsapp") or ""))
    if phone.startswith("+") or phone.startswith("00"):
        digits = phone.lstrip("+").lstrip("0")
        for n in (3, 2):                       # longest dial code first: 593 before 59
            if digits[:n] in _DIAL_COUNTRY:
                return _DIAL_COUNTRY[digits[:n]]
    return ""


def owner_signal(name, co):
    """An empty title on a one-person business is not "no seniority": it is usually the owner. Three FREE signals,
    from data the factory already stored (no fetch, no paid call), checked in order of confidence:

      1. a role word on the PERSON: enrichment often records it in the name itself, e.g. "Domenica (cofundadora)".
      2. a role word in the company BRIEF, which is the extract of the company's OWN site, e.g. YogaLe Studio's
         "Duena mujer con 4 canales". _OWNER matches the role NOUNS (fundador/fundadora/cofundadora/dueña/
         propietaria/socia) and deliberately does NOT match the company-founding participles "fundada"/"cofundado
         en 2024", which say when the COMPANY started, not who decides.
      3. the company being NAMED AFTER the person (NadiaVaro Consultora / Nadia Valdivieso). Requires a >=4-char
         name token, so "Ana" or "Luz" cannot match a random substring.

    All five empty-title pooled cards that a human had scored 88 are caught by (1) or (2), which is why this is the
    right fix: the signal was already in the card, the scorer just never read those fields."""
    co = co or {}
    if _OWNER.search(name or ""):
        return "role word on the person"
    if _OWNER.search(co.get("brief") or ""):
        return "role word in the company brief (own site)"
    toks = [t for t in re.split(r"[^a-z]+", _strip_accents((name or "").lower())) if len(t) >= 4]
    if toks:
        hay = re.sub(r"[^a-z0-9]+", "",
                     _strip_accents((co.get("name") or "").lower()) + " " + (co.get("domain") or "").lower())
        if any(t in hay for t in toks):
            return "company named after the person"
    return ""


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def _is_female(name):
    toks = [t for t in re.split(r"[^a-z]+", _strip_accents((name or "").lower())) if len(t) > 1]
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
    elif owner_signal(name, co):
        s += 40   # no title, but the card itself says owner-operated, and the owner is the decisor
    # --- decisor gender preference (e.g. 2uplatam wants decisoras mujeres) ---
    pref_female = bool(ic.get("prefer_female_decisor")) or (ic.get("decisor") == "mujeres")
    if pref_female:
        if _is_female(name):
            s += 25
        # male/unknown: NOT penalized, just no fit bonus
    else:
        s += 15  # gender isn't a criterion for this profile -> neutral credit (don't cap non-pref clients)
    # --- geo match (country from the stored value, else the ccTLD, else the phone dial code) ---
    geo = (ic.get("geo") or "").lower()
    cc = geo_country(co, ct).lower()
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


def fit_score_card(ld, ic):
    """Score a CARD (leads.lead_data) with the SAME function publish.py uses on companies/contacts rows.

    The pool lives in `leads`, not in companies/contacts: 57 of 86 pooled 2uplatam cards have no companies row at
    all (hand-staged). Re-scoring them needed a way in, and the one thing we must NOT do is write a second scorer
    that drifts from this one. So this is an ADAPTER, not an implementation: it maps the card's fields onto the
    (co, ct, signals, ic) shape and calls fit_score. One score, computed one way (PLAN item 1)."""
    ld = ld or {}
    co = {"name": ld.get("companyName"), "domain": ld.get("_key") or ld.get("website"),
          "website": ld.get("website"), "country": ld.get("country"),
          "brief": ld.get("companyBrief"),   # the own-site extract owner_signal reads when the title is empty
          "instagram": ld.get("instagramHandle"), "linkedin": ld.get("contactLinkedIn"),
          "instagramFollowers": ld.get("instagramFollowers") or 0, "whatsapp": ld.get("whatsapp")}
    ct = {"full_name": ld.get("contactName") or ld.get("decisor"), "title": ld.get("contactTitle"),
          "email": ld.get("contactEmail"), "phone": ld.get("whatsapp"),
          "linkedin_url": ld.get("contactLinkedIn")}
    signals = [{"type": t} for t in (ld.get("whyNow") or [])]
    return fit_score(co, ct, signals, ic)
