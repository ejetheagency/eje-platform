# factory/test_guard_providers.py
# GUARD: no provider SDK import or provider URL may live outside factory/providers/ or api/_lib/llm.js
# (TREASURY.md §8.1, DREAM_TEAM_STACK rule 1). Scans the LIVE system (factory/, api/, public/); legacy
# one-off scripts/ are out of scope. Fails (exit 1) if any provider host appears outside the allowed files.
import os, re, sys

PROVIDER_HOSTS = [
    "api.hunter.io", "api.apollo.io", "api.groq.com", "api.cerebras.ai", "api.deepseek.com",
    "generativelanguage.googleapis.com", "places.googleapis.com", "maps.googleapis.com",
    "google.serper.dev", "serper.dev", "prospeo.io", "api.brandfetch.io", "icypeas",
]
ALLOW = ("factory/providers/", "api/_lib/llm.js")  # the only places allowed to name a provider
ROOTS = ["factory", "api", "public"]


def scan():
    pat = re.compile("|".join(re.escape(h) for h in PROVIDER_HOSTS))
    hits = []
    for root in ROOTS:
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                if not (f.endswith(".py") or f.endswith(".js")):
                    continue
                if f.startswith("test_guard"):   # the guard tests legitimately list the hosts
                    continue
                path = os.path.join(dp, f).replace("\\", "/")
                if any(a in path for a in ALLOW):
                    continue
                try:
                    src = open(path, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                for i, line in enumerate(src.splitlines(), 1):
                    if pat.search(line):
                        hits.append("%s:%d: %s" % (path, i, line.strip()[:80]))
    return hits


if __name__ == "__main__":
    hits = scan()
    for h in hits:
        print("  VIOLATION", h)
    ok = not hits
    print("\nGUARD providers-outside-adapter: %s (%d violation(s))" % ("PASS" if ok else "FAIL", len(hits)))
    sys.exit(0 if ok else 1)
