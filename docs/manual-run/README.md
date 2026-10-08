# Manual demon-run recipe (2026-10-07) → the blueprint the NIGHT FACTORY must automate

This folder holds the reusable scripts from the 2026-10-07 session where the brain (Claude) manually produced,
for 2uplatam, a **6-day buffer of 20 fully-enriched premium leads/day** (Oct 8-15) + a lifecycle projection.
**The goal now: make `run_nightly` do ALL of this autonomously**, so no one builds reports by hand again.

NOTE: these scripts reference the session scratchpad paths and are REFERENCE BLUEPRINTS, not drop-in runnable
(the mining-agent orchestration was done via the Claude Agent tool, not a script). The LOGIC is what to port.

## The recipe we ran by hand (each step = a factory department to wire)

1. **Discover + enrich (DEMON MODE) — one agent per sector lane.** For each sector, an agent used `serper.py`
   (uncapped Google via the factory's SERPER key, NOT the capped WebSearch tool) + WebFetch to find ~10 real
   companies, each with: named decisor (mandatory), live website, email, **WhatsApp (wa.me/mobile)**, Instagram,
   LinkedIn (person + company), 2nd decisor, 4-part intel brief, `ofrecen` phrase, why-now. **No empty core
   channels.** `serper.py` is the key unblock — the Claude-Code WebSearch tool caps at 200/session; serper does not.
2. **Named-decisor + ICP gate** (drop if no real owner/GM/CFO). `agent_miner.py` already has this.
3. **Email verify** (MillionVerifier, never ship `invalid`; accept valid/accept_all/unknown). 1 check/lead.
4. **Compose per-lead scripts, per channel, per PURPOSE** (`hybrid_oct13.py`): pyme → 2uplatam business template
   with `{ofrecen}` filled; universities → networking template. Each lead gets email + WhatsApp + IG + LinkedIn +
   follow-up copy stored IN the lead (`lead_data.pitchEmailES / whatsappMessage / instagramDM / linkedinDM /
   followupEmail`) + `purpose` flag (networking|sales) so the app renders the right script per channel.
5. **Logos** (`logos_v2.py`): scrape each site's apple-touch-icon (real square logo), Google favicon sz=128
   fallback. Stored in `lead_data.logo`. Clearbit is DEAD (DNS fails) — do not use it.
6. **Score** (floor 60, built from channels: email+8 wa+10 ig+6 li+8 2nd+8 brief+4, cap 99). Never ship a raw
   0-100 factory score to a client report (an "8" is nonsense + sorts wrong).
7. **Schedule / stage** (`uni_publish.py` / `hybrid_*`): write each lead with a future `source_date` + `approved=true`.
   The app auto-releases it at 8 AM Santiago (no cron needed to "send"). Keep ≥3 business days staged as insurance.
8. **Project** (`project_lifecycle.py` + `build_projection_html.py`): simulate every lead's cadence forward →
   day-by-day load + problems. Artifact: see PLAN.md for the live URL.

## The cadence (now WIRED in public/app.html, non-EJE / WhatsApp-forward)
`t1 email (d0) → t2 WhatsApp (+2d) → t3 Instagram (+4d) → t4 email (+7d) → t5 LinkedIn (+5d) → monthly`.
Each non-email touch resolves to what the lead has, preferring WhatsApp, then IG/LinkedIn, then email.
EJE (`ISEJE`) keeps its IG-first doctrine — unchanged.

## What the factory must gain to do this itself (maps to PLAN Track B)
- Run the **serper lanes** per client ICP (not the capped tool) + the **demon-enrichment pass** (exhaust every
  route for WhatsApp/IG/LinkedIn/email + logo) as the DEFAULT, not on request.
- Generate per-lead **per-channel scripts by `purpose`** + the 4-part brief + `ofrecen` (Haiku).
- **Score with the floor formula**, set **logos**, then **stage 20/day** keeping a ≥3-day forward buffer.
- Honest structural limit to encode: **academics (universities) rarely have personal IG or direct WhatsApp** —
  their channel floor is LinkedIn + email + faculty line. Consumer pymes = IG + WhatsApp ~100%.
