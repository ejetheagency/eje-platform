#!/usr/bin/env python3
# scripts/llm_router.py
#
# THE COST GOVERNOR'S BRAIN. One entry point for every LLM call in the system. It:
#   1. Routes each task to the CHEAPEST capable model (cheap lane for bulk, premium only for judgment).
#   2. CACHES by prompt hash, so an identical call never bills twice.
#   3. METERS every call into a ledger (tokens + estimated cost per client), the data that later
#      prices Pro add-ons and warns before credits run out.
#
# Provider-agnostic: it uses whatever key you have in env, checked cheapest-first. All the cheap
# providers speak the OpenAI chat-completions dialect, so one call path covers them.
#
#   from llm_router import route
#   text = route("Extract the founder's name from this about page:\n"+html, tier="cheap")
#
#   python3 scripts/llm_router.py --status     # show which providers are active + ledger totals
#   python3 scripts/llm_router.py --test        # run a tiny prompt on the cheapest active provider

import os, sys, json, hashlib, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT, "cache", "llm")
LEDGER = os.path.join(ROOT, "cache", "llm_ledger.jsonl")

# cheapest-first within each tier. price = USD per 1M output tokens (rough, for metering only).
PROVIDERS = [
    # --- CHEAP LANE (bulk extraction / classification) ---
    {"name":"groq",     "tier":"cheap",   "env":"GROQ_API_KEY",     "base":"https://api.groq.com/openai/v1",
     "model":"llama-3.3-70b-versatile", "price":0.79, "free":True},
    {"name":"gemini",   "tier":"cheap",   "env":"GEMINI_API_KEY",   "base":"https://generativelanguage.googleapis.com/v1beta",
     "model":"gemini-flash-lite-latest", "price":0.10, "free":True},
    {"name":"deepseek", "tier":"cheap",   "env":"DEEPSEEK_API_KEY", "base":"https://api.deepseek.com",
     "model":"deepseek-chat", "price":1.10, "free":False},
    # --- PREMIUM LANE (rare judgment only) ---
    {"name":"anthropic","tier":"premium", "env":"ANTHROPIC_API_KEY","base":"https://api.anthropic.com/v1",
     "model":"claude-sonnet-4-5", "price":15.0, "free":False},
]

def _env(name):
    v = os.environ.get(name)
    if v: return v
    # also read eje-leads/.env and a local .env if present
    for p in [os.path.expanduser("~/claude/eje-leads/.env"), os.path.join(ROOT, ".env")]:
        if os.path.exists(p):
            for l in open(p):
                l=l.strip()
                if l.startswith(name+"="): return l.split("=",1)[1].strip().strip('"')
    return None

def active_providers(tier=None):
    out=[]
    for p in PROVIDERS:
        if tier and p["tier"]!=tier: continue
        if _env(p["env"]): out.append(p)
    return out

def _cache_key(model, prompt): return hashlib.sha256((model+"|"+prompt).encode()).hexdigest()[:24]

def _log(provider, prompt, out, client):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    est = (len(out)/4)/1_000_000 * provider["price"]   # crude output-token cost estimate
    rec = {"t": int(time.time()), "provider": provider["name"], "model": provider["model"],
           "client": client, "chars_out": len(out), "est_usd": round(est, 6)}
    open(LEDGER, "a").write(json.dumps(rec)+"\n")

def _call_openai_compat(provider, key, prompt):
    if provider["name"]=="gemini":  # gemini native generateContent (most reliable for AI-Studio keys)
        req = urllib.request.Request(provider["base"]+"/models/"+provider["model"]+":generateContent?key="+key,
            data=json.dumps({"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0}}).encode(),
            headers={"Content-Type":"application/json"}, method="POST")
        r=json.load(urllib.request.urlopen(req, timeout=60)); return r["candidates"][0]["content"]["parts"][0]["text"]
    if provider["name"]=="anthropic":  # anthropic has its own dialect
        req = urllib.request.Request(provider["base"]+"/messages",
            data=json.dumps({"model":provider["model"],"max_tokens":1024,
                             "messages":[{"role":"user","content":prompt}]}).encode(),
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"}, method="POST")
        r=json.load(urllib.request.urlopen(req, timeout=60)); return r["content"][0]["text"]
    req = urllib.request.Request(provider["base"]+"/chat/completions",
        data=json.dumps({"model":provider["model"],"messages":[{"role":"user","content":prompt}],"temperature":0}).encode(),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"}, method="POST")
    r=json.load(urllib.request.urlopen(req, timeout=60)); return r["choices"][0]["message"]["content"]

def route(prompt, tier="cheap", client="eje", use_cache=True):
    provs = active_providers(tier) or active_providers()   # fall back to any active provider
    if not provs:
        raise RuntimeError("no LLM provider key found. Add GROQ_API_KEY / GEMINI_API_KEY / DEEPSEEK_API_KEY to env.")
    provider = provs[0]
    if use_cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cf = os.path.join(CACHE_DIR, _cache_key(provider["model"], prompt)+".txt")
        if os.path.exists(cf): return open(cf).read()
    out = _call_openai_compat(provider, _env(provider["env"]), prompt)
    if use_cache: open(cf, "w").write(out)
    _log(provider, prompt, out, client)
    return out

def main():
    if "--status" in sys.argv:
        print("Active providers (cheapest-first):")
        for p in PROVIDERS:
            on = "ON " if _env(p["env"]) else "off"
            print(f"  [{on}] {p['name']:10} {p['tier']:8} {p['model']:26} {'(free tier)' if p['free'] else ''}")
        if os.path.exists(LEDGER):
            recs=[json.loads(l) for l in open(LEDGER)]
            tot=sum(r["est_usd"] for r in recs)
            print(f"\nLedger: {len(recs)} calls, est ${tot:.4f} total")
        else:
            print("\nLedger: empty (no LLM calls billed yet)")
    elif "--test" in sys.argv:
        try:
            print(route("Reply with exactly the word: ready", tier="cheap", use_cache=False))
        except Exception as e:
            print("no key active yet:", e)
    else:
        print("usage: llm_router.py --status | --test")

if __name__ == "__main__":
    main()
