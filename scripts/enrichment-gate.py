#!/usr/bin/env python3
# scripts/enrichment-gate.py
#
# THE AUTO-ENRICHMENT QUALITY GATE (Phase 3). A lead is not shippable unless it is actionable.
# Removes the operator from manually eyeballing lead quality before drafting/sending.
#
# HARD blockers (a lead CANNOT ship / auto-draft): missing company, no named decision-maker
#   (a real person, not a role inbox), no valid email, no live channel (Instagram or LinkedIn).
# SOFT flags (advisory, do NOT block): thin brief, low score, no website. Surfaced so the
#   enrichment agents can deepen them, but they don't stop an otherwise-actionable lead.
#
#   python3 scripts/enrichment-gate.py               # AUDIT loaded EJE leads (read-only)
#   python3 scripts/enrichment-gate.py --apply        # enforce: readyToSend = (no hard blockers)
#   python3 scripts/enrichment-gate.py --only-ready    # audit only leads currently marked readyToSend
#
# Enforcement is ADDITIVE: flips lead_data.readyToSend, writes lead_data._holdReason (hard fails)
# and lead_data._qualityFlags (soft). Never deletes a lead. Held leads queue for re-enrichment.

import json, sys, re, urllib.request, urllib.parse
from collections import Counter

SB  = "https://ogdsuztzhmnnjolilsuo.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZHN1enR6aG1ubmpvbGlsc3VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMDI0MDMsImV4cCI6MjA5MTc3ODQwM30.9iKhJJWd_zg6WfdxTR9ojK4DVLR3e-bLdPXY-0uDp7Q"
H   = {"apikey": KEY, "Authorization": "Bearer " + KEY}
APPLY = "--apply" in sys.argv
ONLY_READY = "--only-ready" in sys.argv

GENERIC = {"info","contacto","hola","hello","mail","office","proyectos","ventas","sales",
           "equipo","team","admin","contact","hi","studio","estudio","agencia","new","business"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def sb_get(q):
    return json.load(urllib.request.urlopen(urllib.request.Request(SB + "/rest/v1/" + q, headers=H)))
def sb_patch(q, body):
    r = urllib.request.Request(SB + "/rest/v1/" + q, data=json.dumps(body).encode(),
        headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(r)

def named_decisor(name):
    if not name: return False
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    return len(parts) >= 2 and parts[0].lower() not in GENERIC

def check(lead):
    ld = lead.get("lead_data") or {}
    hard, soft = [], []
    if not (ld.get("companyName") or lead.get("company")): hard.append("no company")
    if not named_decisor(ld.get("contactName") or lead.get("contact_name")): hard.append("no named decision-maker")
    em = (ld.get("contactEmail") or lead.get("contact_email") or "").strip()
    if not EMAIL_RE.match(em): hard.append("no/invalid email")
    if not (ld.get("instagramHandle") or ld.get("contactLinkedIn")): hard.append("no live channel (IG/LinkedIn)")
    # soft quality
    if len((ld.get("companyBrief") or "").strip()) < 120: soft.append("thin brief")
    score = lead.get("score") or ld.get("score") or 0
    try: score = float(score)
    except Exception: score = 0
    if score < 80: soft.append("low score")
    if not (ld.get("website") or "").startswith("http"): soft.append("no website")
    return hard, soft

def main():
    q = "leads?client_id=eq.eje&select=id,company,contact_name,contact_email,score,lead_data&limit=1000"
    if ONLY_READY: q += "&lead_data->>readyToSend=eq.true"
    leads = sb_get(q)
    print(("ENFORCE" if APPLY else "AUDIT") + f" enrichment gate on {len(leads)} EJE leads\n")
    npass = nhold = 0; hard_r = Counter(); soft_r = Counter(); held = []
    for l in leads:
        hard, soft = check(l)
        for f in hard: hard_r[f]+=1
        for f in soft: soft_r[f]+=1
        if hard: nhold += 1; held.append((l["company"], hard))
        else: npass += 1
        if APPLY:
            ld = l.get("lead_data") or {}
            ld["readyToSend"] = (len(hard) == 0)
            ld["_holdReason"] = "; ".join(hard)
            ld["_qualityFlags"] = "; ".join(soft)
            sb_patch(f"leads?id=eq.{urllib.parse.quote(l['id'])}&client_id=eq.eje", {"lead_data": ld})
    print(f"SHIPPABLE (passes hard gate): {npass}   HELD (blocked): {nhold}\n")
    if held:
        print("Held leads (hard blockers only):")
        for c, fs in held[:30]: print(f"  HOLD  {c[:26]:26} -> {'; '.join(fs)}")
        print("\nHard blockers by frequency:")
        for r, n in hard_r.most_common(): print(f"  {n:4}x  {r}")
    print("\nSoft quality flags (advisory, do not block, feed the enrichment agents):")
    for r, n in soft_r.most_common(): print(f"  {n:4}x  {r}")
    if not APPLY: print("\n(audit only — re-run with --apply to enforce readyToSend)")

if __name__ == "__main__":
    main()
