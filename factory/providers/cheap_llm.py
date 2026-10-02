# factory/providers/cheap_llm.py
# D2 cheap-LLM ROUTER: cheapest-first with automatic fallback + per-call metering. Only tries providers
# whose API key is present, so it works today with Gemini alone and lights up Groq/Cerebras the moment
# their keys are in env. Groq + Cerebras use the OpenAI-compatible chat API. No multi-account rotation.
import os, json, urllib.request
from factory.packages import budget

# (name, env_key, url, model, est_usd) — cheapest first.
LADDER = [
    ("groq",     "GROQ_API_KEY",     "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile", 0.00005),
    ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions",      "llama-3.3-70b",           0.00005),
    ("gemini",   "GEMINI_API_KEY",   None,                                               "gemini-flash-lite-latest", 0.0002),
]


def _openai_chat(url, key, model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        j = json.loads(r.read().decode())
    return j["choices"][0]["message"]["content"].strip()


def generate(prompt, client_id=None, job_type="llm"):
    """Return {provider, text}. Tries cheapest available provider first, falls back on error/rate-limit."""
    last = None
    for name, envk, url, model, est in LADDER:
        if not os.environ.get(envk):
            continue
        try:
            if name == "gemini":
                from factory.providers.gemini import _gen
                text = _gen(prompt)
            else:
                text = _openai_chat(url, os.environ[envk], model, prompt)
            budget.log_cost(name, est, client_id=client_id, job_type=job_type, estimated=True)
            return {"provider": name, "text": text}
        except Exception as e:
            last = e
            continue
    raise RuntimeError("no cheap-LLM provider available (last error: %s)" % last)
