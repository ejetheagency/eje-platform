#!/usr/bin/env python3
# Uncapped web search via the factory's serper key (separate from the Claude Code WebSearch budget).
# Usage: python3 serper.py "your google query"
import sys, os, json, urllib.request
sys.path.insert(0, "/Users/jofreeyzaguirre/claude/unabase-app")
from factory.packages import db  # loads .env into os.environ
key = os.environ.get("SERPER_API_KEY") or os.environ.get("SERPER_KEY")
q = " ".join(sys.argv[1:]).strip()
if not q:
    print("usage: serper.py <query>"); sys.exit(1)
req = urllib.request.Request("https://google.serper.dev/search",
    data=json.dumps({"q": q, "gl": "ec", "hl": "es", "num": 10}).encode(),
    headers={"X-API-KEY": key, "Content-Type": "application/json"})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=25).read())
except Exception as e:
    print("SERPER_ERROR:", e); sys.exit(2)
for o in r.get("organic", []):
    print("TITLE:", o.get("title", ""))
    print("LINK:", o.get("link", ""))
    print("SNIPPET:", o.get("snippet", ""))
    print("---")
kg = r.get("knowledgeGraph")
if kg:
    print("KG:", json.dumps({k: kg.get(k) for k in ("title", "type", "attributes") if kg.get(k)}, ensure_ascii=False))
