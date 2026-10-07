# 2uplatam (Fernando) — THE CADENCE = THE PRODUCT. This structure must NEVER break.
**Locked 2026-10-07 for onboarding.** The deliverable Fernando pays for: **every business day, a clean "Hoy" with
≥20 fully-enriched, ready-to-action leads**, each moving through this exact lifecycle. No excuses, no half-done cards.

## The non-negotiable guarantee
- **≥20 leads/day on Hoy, every business day.** Fully enriched (named decisor + verified email + ≥2 channels) and
  ready to action. If the factory can't produce 20 net-new, it drips from the enriched pool — Hoy is NEVER short.
- Each lead carries its **channel set** (email / IG / LinkedIn / WhatsApp). A 4-channel lead looks slightly richer
  than an email+IG one, but the STRUCTURE below is identical — channels just fill the slots.

### How the guarantee is enforced (WIRED vs pending — docs = machine)
- **WIRED — daily SLA check + alert.** `factory/workers/sla_check.py` runs at the end of every nightly run. It
  counts the Hoy the client will actually see (approved + today's report-date on the 08:00 Chile boundary, email
  present = actionable) against `ready_leads_per_day` (2uplatam = 20). If short, it fires `notify` so a dry Hoy is
  NEVER silent. Verified live: it reports `0/20 SHORT by 20` and alerts. Target is per-client in `icp_config.ready_leads_per_day`.
- **WIRED — keep-the-pool-full + drip.** `scheduler.pool_floor` discovers to keep READY ≈ 20×ready_pool_days;
  `release.schedule_all` dates uncontacted leads 20/day so Hoy shows a dated report, not the whole pool.
- **PENDING — net-new production.** The competent miner (`agent_miner.py` with Claude Haiku in the judgment seat,
  proven to find real owners + real emails where the cheap LLMs found 0) is NOT yet wired into the nightly run path.
  Until it is, the drip can only backfill from whatever the pool holds; a dry pool = the SLA alert fires (correct behavior).
  Next build: wire `agent_miner` into the run so the 20 are produced autonomously, and put the Anthropic key on Railway.

## The lifecycle (the structure that cannot break)
Every touch MENTIONS THE LEVERAGE — the client names / the "pensé en ti porque encajas con el perfil de mis clientes".

| Touch | When | Channel | Purpose |
|---|---|---|---|
| **T1** | Day 0 | **Email** | First touch. The pitch. |
| **T2** | +48 h | **IG** | Attention-puller → points back to the email. Mentions the leverage (names). |
| **T3** | +7 days | **2nd email** — OR **WhatsApp** if the lead HAS WhatsApp | Re-pull attention. WhatsApp behaves like IG (short attention-puller), not a formal email. |
| **T4** | recommended gap after T3 | **the remaining channel** (LinkedIn / whichever is left). If NONE left → **insist via WhatsApp, or IG if no WhatsApp**. | Last of the main sequence. |
| **Monthly** | T4 + 30d, then monthly | **Newsletter touch** (3 months) | Soft re-engagement. Fernando writes it monthly — **success cases from his own clients**. "ahora no" = "todavía no". |
| **Close** | after 3 monthly touches | — | Lead closes for good. |

**Channel fallback (fill the slots with what the lead has):** IG → LinkedIn → WhatsApp. For 2uplatam we do NOT burn
the domain with a redundant extra email — if a non-email slot has no channel, we insist through WhatsApp/IG.

## The double-touch recommendation (IG + WhatsApp only — the "recomendaciones")
IG and WhatsApp allow a **2nd balloon**. If an IG DM went out Tuesday, by **Thursday** send a longer attention+explain
message. Surface these as a **Recomendaciones** item on Hoy/Tareas (small, platform double-touches), never on email/LinkedIn.
**Fernando's real voice (verbatim template for the IG/WA double-touch):**
> Oye te cuento; te he escrito un par de veces y se han perdido los mensajes.
>
> Calzas con el perfil de alguno de mis clientes por lo tanto pensé en ti hoy.
>
> Te cuento en cortísimo:
> Abrimos conversaciones con tus clientes ideales y luego tú cierras la venta 🙂. Podemos coordinar una demo si quieres explorar.
>
> Cuéntame. Si tienes capacidad para 5-10 conversaciones extra semanales puede funcionarte.

## First-week UX (what Fernando sees)
- **Hoy** = the 20 ready-to-action cards, each with its current touch + channel one-click.
- **Recomendaciones** = the IG/WhatsApp double-touch nudges.
- **HIDE every tab that isn't his** (EJE-only / internal surfaces). Only crucial, usable things visible.
- **Clara** (assistant) = present but labeled **"en desarrollo / no funcional aún"** — don't let it imply a finished feature.
- Spanish = neutral LATAM, correct orthography, warm (his voice), always naming the leverage.
