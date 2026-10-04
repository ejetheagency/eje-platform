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
           "russell bedford", "bdo", "grant thornton", "crowe", "rsm", "baker tilly", "mazars", "nexia", "moore", "uhy"}
_GEO = r"\b(ecuador|chile|peru|perú|colombia|mexico|méxico|argentina|uruguay|españa|spain|usa|canada|brasil|brazil|panama|panamá|guatemala|bolivia|venezuela|sa|s\.a\.|ltda|inc|llc|corp|group|grupo)\b"
_CHAIN_KW = re.compile(r"franquicia|franchise|franquicias|sucursal|sucursales|locales en|nuestras sedes|our locations|"
                       r"en todo el mundo|worldwide|global presence|multinacional|international locations|cadena de|"
                       r"member firm|firma miembro|network of|red internacional|miembro de la red|red global|"
                       r"present in \d|presente en \d|oficinas en \d|offices in \d", re.I)
_COUNTRIES = ["ecuador", "peru", "perú", "colombia", "mexico", "méxico", "chile", "argentina", "usa", "estados unidos",
              "brasil", "brazil", "españa", "panama", "panamá", "guatemala", "bolivia", "uruguay", "paraguay", "venezuela", "canada"]
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


def is_chain(name, website):
    # Returns (excluded: bool, reason: str|None). Excludes global brands, franchises, and multi-country chains.
    if is_brandlike(name):
        return (True, "global brand or generic single-token name")
    txt = _homepage(website)
    if not txt:
        return (False, None)
    if _CHAIN_KW.search(txt):
        return (True, "franchise/chain language on site")
    if sum(1 for c in set(_COUNTRIES) if c in txt) >= 3:
        return (True, "operates in 3+ countries (chain)")
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
