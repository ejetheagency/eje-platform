# factory/packages/icp_filters.py
# Shared ICP quality filters used by BOTH Gate A and discovery so chains/franchises/global brands are never
# enriched, corroboration sources must be specific profiles, and name variants are matched. Deterministic, free.
import re, unicodedata, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; EJEFactory/1.0)"}

# Known global brands + chains whose bare name resolves to the wrong (global/chain) entity.
_BRANDS = {"ledvance", "osram", "philips", "signify", "bosch", "siemens", "3m", "nestle", "coca-cola", "pepsi",
           "samsung", "lg", "sony", "dell", "hp", "ibm", "oracle", "sap", "visa", "mastercard", "toyota", "nike",
           "ey", "kpmg", "deloitte", "pwc", "mcdonalds", "starbucks", "subway", "kfc", "burger king", "dominos",
           "fogo de chao", "fogo de chão", "marriott", "hilton", "fedex", "dhl", "ups",
           "russell bedford", "bdo", "grant thornton", "crowe", "rsm", "baker tilly", "mazars", "nexia", "moore", "uhy",
           "stripe", "google", "meta", "facebook", "amazon", "microsoft", "apple", "havas", "ogilvy", "publicis",
           "wpp", "accenture", "mccann", "bbdo", "ddb", "leo burnett", "saatchi", "wunderman", "dentsu"}
_GEO = r"\b(ecuador|chile|peru|perú|colombia|mexico|méxico|argentina|uruguay|españa|spain|usa|canada|brasil|brazil|panama|panamá|guatemala|bolivia|venezuela|sa|s\.a\.|ltda|inc|llc|corp|group|grupo)\b"
_CHAIN_KW = re.compile(r"franquicia|franchise|franquicias|sucursal|sucursales|locales en|nuestras sedes|our locations|"
                       r"en todo el mundo|worldwide|global presence|multinacional|international locations|cadena de|"
                       r"member firm|firma miembro|network of|red internacional|miembro de la red|red global|"
                       r"present in \d|presente en \d|oficinas en \d|offices in \d", re.I)
_COUNTRIES = ["ecuador", "peru", "perú", "colombia", "mexico", "méxico", "chile", "argentina", "usa", "estados unidos",
              "brasil", "brazil", "españa", "panama", "panamá", "guatemala", "bolivia", "uruguay", "paraguay", "venezuela", "canada"]
# OFF-ICP entity TYPES (not businesses that buy prospecting/VA services): schools, chambers, associations,
# foundations, government. Catches the Stripe/Havas/CES-Design/Chamber-of-Commerce class of mistake.
_OFF_ICP_NAME = re.compile(r"\b(universidad|university|colegio|academia|academy|centro superior|centro de estudios|"
                           r"escuela de|school of|c[aá]mara de comercio|chamber of commerce|asociaci[oó]n|association|"
                           r"gremio|federaci[oó]n|federation|cooperativa|fundaci[oó]n|foundation|ong\b|ngo\b|"
                           r"ministerio|municipio|gobierno|alcald[ií]a|ayuntamiento|instituto de dise|institute of design)\b", re.I)
_OFF_ICP_DOM = re.compile(r"\.(edu|gob|gov)(\.|/|$)", re.I)   # school / government domains
# source URLs that are NOT a specific profile/page about the person -> cannot corroborate
_BAD_SRC = re.compile(r"/reel/|/pub/dir/|/search\b|[?&]q=|google\.[^/]+/search|bing\.com/search|duckduckgo|"
                      r"/explore/|/tag/|/hashtag/|/directory|/dir/|yellowpages|paginasamarillas|/results|facebook\.com/pages", re.I)
# small nickname map (extend as variants surface)
_NICK = {"sandy": "sandra", "pepe": "jose", "paco": "francisco", "pancho": "francisco", "beto": "alberto",
         "lupe": "guadalupe", "nacho": "ignacio", "memo": "guillermo", "charlie": "carlos", "alex": "alejandro",
         "dani": "daniel", "gabo": "gabriel", "pili": "pilar", "maru": "maria", "coco": "jorge", "tavo": "gustavo"}


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def is_brandlike(name):
    # True -> known global brand/chain OR a single generic token; a search-only name cannot be trusted.
    n = (name or "").strip().lower()
    if not n:
        return True
    core = re.sub(_GEO, "", n).strip()
    if core in _BRANDS or any(b in core for b in _BRANDS):
        return True
    toks = [t for t in re.split(r"\s+", core) if t]
    if any(t in _BRANDS for t in toks):
        return True
    return len(toks) <= 1


def _homepage(website):
    if not website:
        return ""
    url = website if website.startswith("http") else ("https://" + website)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=10) as r:
            return r.read(300000).decode("utf-8", "ignore").lower()
    except Exception:
        return ""


def _known_brand(name):
    # True only for a KNOWN global brand/chain (token for single words, substring for multi-word). NOT generic
    # single-token names (those are handled by is_brandlike for Gate A's search-trust only, never as exclusion).
    n = re.sub(_GEO, "", (name or "").lower()).strip()
    toks = set(re.split(r"\s+", n))
    for b in _BRANDS:
        if (" " in b or "-" in b):
            if b in n:
                return True
        elif b in toks:
            return True
    return False


def is_chain(name, website):
    # Returns (excluded, reason). PRECISE exclusion: known global brands/chains, off-ICP entity types
    # (schools/chambers/associations/government), and EXPLICIT franchise/network language on the site.
    # Deliberately does NOT exclude generic single-token names or "mentions N countries" (those over-removed
    # real small agencies).
    if _known_brand(name):
        return (True, "known global brand/chain")
    if _OFF_ICP_NAME.search(name or ""):
        return (True, "off-ICP entity (school/chamber/association/government)")
    if _OFF_ICP_DOM.search(website or ""):
        return (True, "off-ICP domain (edu/gov)")
    txt = _homepage(website)
    if txt and _CHAIN_KW.search(txt):
        return (True, "franchise/chain/network language on site")
    return (False, None)


def specific_source(url):
    # A corroborating source must be a specific profile/page about the person, not a reel/search/directory.
    return bool(url) and not _BAD_SRC.search(url)


def norm_name(name):
    # Normalize for matching: strip accents, lowercase, expand nicknames, keep first + last (drop middles/initials).
    n = _strip_accents((name or "").lower())
    toks = [t for t in re.split(r"[^a-z]+", n) if len(t) > 1]
    toks = [_NICK.get(t, t) for t in toks]
    if not toks:
        return ""
    return (toks[0] + " " + toks[-1]) if len(toks) >= 2 else toks[0]
