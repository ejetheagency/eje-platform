#!/usr/bin/env python3
# scripts/classify-response.py
#
# THE FLYWHEEL SEED. A client describes a reply in plain language ("Miguel de X respondió, dijo Y").
# The cheap lane classifies it into a RESPONSE TYPE (a growing taxonomy) + temperature + next move.
# Aggregated per sector, these response types are the data that later reshapes the product itself:
# the action buttons stop being hardcoded (Loom/Reunion/Respondio) and become sector-learned options,
# and a self-serve client who picks their sector inherits all of it. ~$0 per classification.
#
#   python3 scripts/classify-response.py "Miguel de Cactus Films dijo que le interesa pero ..."
#
# Output feeds: the lead's stage/note, AND (aggregated) the per-sector button/playbook config.

import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_router import route

# growing taxonomy — new types get added as real responses reveal them (that IS the intelligence)
TAXONOMY = ["interested","wants_info","wants_pricing","wants_meeting","wants_demo_or_video",
            "not_interested","no_budget","bad_timing","already_has_vendor","referred_elsewhere",
            "no_response","asked_to_stop","closed_won","other"]

def main():
    text = " ".join([a for a in sys.argv[1:] if not a.startswith("--")]) or sys.stdin.read()
    if not text.strip():
        print('usage: classify-response.py "<what the prospect said>"'); return
    prompt = ("Un cliente describe la respuesta de un prospecto. Clasificala. Responde SOLO JSON valido, sin "
        "markdown:\n"
        '{"company":..,"person":..,"what_they_said":(resumen 1 frase, sin guiones largos),'
        f'"response_type":(UNO de: {", ".join(TAXONOMY)}),'
        '"secondary_type":(otro de la lista o null),'
        '"temperature":("hot"|"warm"|"cold"),'
        '"suggested_next_action":(paso concreto en espanol)}\n'
        "TEXTO:\n"+text)
    raw = route(prompt, tier="cheap", client="eje").strip()
    raw = re.sub(r"^```(json)?|```$","",raw,flags=re.M).strip()
    m = re.search(r"\{.*\}", raw, re.S)
    d = json.loads(m.group(0) if m else raw)
    print("── response classified (cheap lane) ──")
    print(f"  lead           {d.get('company')}  /  {d.get('person')}")
    print(f"  they said      {d.get('what_they_said')}")
    print(f"  RESPONSE TYPE  {d.get('response_type')}" + (f"  (+{d.get('secondary_type')})" if d.get('secondary_type') else ""))
    print(f"  temperature    {d.get('temperature')}")
    print(f"  NEXT ACTION -> {d.get('suggested_next_action')}")
    print("\n(this response_type, aggregated per sector, is what reshapes the action buttons + playbook)")

if __name__ == "__main__":
    main()
