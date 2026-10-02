# factory/test_guard_spend.py
# GUARD: every PAID provider adapter (per-call price > 0, or it uses the LLM lane prices) that logs a
# cost MUST also call budget.can_spend before spending (TREASURY.md §8.1, closes 002 audit §3). Free
# adapters (price 0) are exempt. Fails (exit 1) if any paid adapter spends without a gate.
import os, json, importlib, sys


def paid_adapters_missing_gate():
    pdir = "factory/providers"
    bad = []
    for f in sorted(os.listdir(pdir)):
        if not f.endswith(".py") or f == "__init__.py":
            continue
        src = open(os.path.join(pdir, f)).read()
        if "log_cost" not in src:            # doesn't spend/log -> not in scope
            continue
        gated = "can_spend" in src
        try:
            mod = importlib.import_module("factory.providers." + f[:-3])
        except Exception as e:
            bad.append("%s (import error: %s)" % (f, e))
            continue
        est = getattr(mod, "EST_USD", 0) or 0
        dc = getattr(mod, "DETAILS_COST", 0) or 0
        uses_lane = ("llm_cheap" in src) or ("llm_premium" in src)   # cheap_llm has no module-level price
        paid = (est > 0) or (dc > 0) or uses_lane
        if paid and not gated:
            bad.append(f)
    return bad


if __name__ == "__main__":
    bad = paid_adapters_missing_gate()
    for b in bad:
        print("  VIOLATION paid adapter without can_spend:", b)
    ok = not bad
    print("\nGUARD paid-adapter-must-gate: %s (%d violation(s))" % ("PASS" if ok else "FAIL", len(bad)))
    sys.exit(0 if ok else 1)
