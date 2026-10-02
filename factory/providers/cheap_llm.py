# factory/providers/cheap_llm.py
# LLM ROUTER with two lanes:
#   generate(prompt)                -> CHEAP lane (bulk enrichment): cheapest-first, fallback. Gemini-flash-lite etc.
#   generate(prompt, premium=True)  -> PREMIUM lane (the Composer / Tier-3 synthesis): best-quality-first.
# Only tries providers whose API key is present. Groq/Cerebras/DeepSeek use the OpenAI-compatible chat API.
import os, json, urllib.request
from factory.packages import budget

# (name, env_key, url, model). Per-call price estimates live in config/prices.json (llm_cheap / llm_premium).
CHEAP = [
    ("groq",     "GROQ_API_KEY",     "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions",      "gpt-oss-120b"),
    ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/chat/completions",        "deepseek-chat"),
    ("gemini",   "GEMINI_API_KEY",   None,                                               "gemini-flash-lite-latest"),
]
# Premium lane: quality first (for the Composer's high-value synthesis).
PREMIUM = [
    ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/chat/completions",   "deepseek-chat"),
    ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions", "gpt-oss-120b"),
    ("gemini",   "GEMINI_API_KEY",   None,                                          "gemini-flash-latest"),
]
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def _openai_chat(url, key, model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]["content"].strip()


def _gemini(model, prompt):
    key = os.environ["GEMINI_API_KEY"]
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.3}}).encode()
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (model, key)
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())["candidates"][0]["content"]["parts"][0]["text"].strip()


def generate(prompt, client_id=None, job_type="llm", premium=False):
    lane = "llm_premium" if premium else "llm_cheap"
    ladder = PREMIUM if premium else CHEAP
    lane_prices = budget.prices().get(lane, {})
    last = None
    for name, envk, url, model in ladder:
        if not os.environ.get(envk):
            continue
        est = float(lane_prices.get(name, 0.0002))  # price from config/prices.json
        ok, reason = budget.can_spend(client_id, name, est)  # gate before spend (same call as hunter.py/apollo.py)
        if not ok:
            last = reason
            continue
        try:
            text = _gemini(model, prompt) if name == "gemini" else _openai_chat(url, os.environ[envk], model, prompt)
            budget.log_cost(name, est, client_id=client_id, job_type=job_type, estimated=True)
            return {"provider": name, "text": text}
        except Exception as e:
            last = e
            continue
    raise RuntimeError("no %s LLM provider available (last error: %s)" % ("premium" if premium else "cheap", last))
