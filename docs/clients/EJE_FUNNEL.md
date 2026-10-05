# EJE funnel (connected funnel doc — the composer/factory reads this, not generic defaults)
Source of truth for EJE's OWN outreach. Authoritative brand detail: `~/claude/eje-brand/BRAND.md` §1b + `VOZ.md`. This doc exists so the composer never again invents the wrong offer (it once wrote a "visibility diagnostic"; EJE does NOT sell that). Every client should have a funnel doc like this, referenced from `clients.icp_config.funnel_doc`.

## The offer (what EJE sells)
"Generador de conversaciones accionables" — a SYSTEM the client's team OPERATES, not a send-service. Core value = verified decision-maker contact cards (right decisor + exact channel + ready message) + the discipline to execute in one extra routine step. **NEVER say "we send / on your behalf / automated" — that is WRONG.** The client sends via guided one-click steps.

## First-touch -> loom funnel
- **First touch = email, personalized.** Open with the invitation (CTA first), lead with the *destino* (the change in their life: "saber de dónde sale tu próximo cliente"), use SELECTION not agitation ("calzas con el perfil de mis clientes"), transparency as the weapon.
- **The "loom" = a short presentación (~3 min) that explains how the system works**, offered as the value-drop. From the real Daniela close: *"Te envío una presentación por email y me comentas."* It comes after interest, or is offered in the first email as the low-friction next step.
- Cadence (ciclo de vida): Ciclo 1 email -> IG DM; Ciclo 2 email -> WhatsApp; Ciclo 3+ email. **The 2nd touch is NEVER email (IG or LinkedIn).** Always 10:00-18:00 recipient's timezone.

### Real first-touch (verbatim, MIRROR THIS — sent 2026-09-18 from contact@ejetheagency.com)
> Hola José! Te habla Emiliano de EJE Agency.
>
> Te cuento: ahora mismo estoy trabajando con UnaBase, y cuando escuché de Logistik vi que calzaba con el perfil de mis clientes y decidí escribirte.
>
> ¿Quieres que te envíe un video explicando lo que hago? Quizás Logistik es un fit para nuestro servicio.
>
> ¡Quedo atento!

This is the register: 4 short lines, warm with exclamations, introduces himself by name, casual current-client proof ("ahora mismo estoy trabajando con UnaBase"), selection ("calzaba con el perfil de mis clientes y decidí escribirte"), the loom offered as a soft question ("¿Quieres que te envíe un video explicando lo que hago?"), soft fit framing, "¡Quedo atento!". Do NOT make it longer or more corporate ("disciplina de una bandeja activa" is too much for the first touch).

## Current first-touch templates (WEEK OF 2026-10-05, until changed) — A/B, half and half
Send ~5 of each per day, one template per lead (never both to the same person). Both end in the ask "¿a quién le envío la info?" (identify the decisor / next step). NO loom this week. **Subject = "{company} x EJE"** for both templates.

**Template A (referral + IG angle):**
> Hola {first}, ¿cómo estás? Espero que súper. Te habla Emiliano de @ejetheagency.
>
> Un conocido me habló de ustedes, entré a su Instagram para revisar, y hoy trabajo con clientes en su sector. Cuéntame, ¿a quién le debería enviar la info, por aquí mismo o a alguien más del equipo?
>
> Creo que quizás {company} puede ser un match para nuestro servicio.

**Template B (honest-cold + client names + explicit value):**
> Hola {first}, ¿todo bien? Te habla Emiliano de EJE.
>
> Te escribo en frío total ya que vi que {company} tiene un perfil parecido a clientes que ayudo hoy. Básicamente ayudamos a empresas como UnaBase, 2upLatam o Estudio Fe: iniciamos conversaciones con su cliente ideal para que luego ellos cautiven y cierren la venta.
>
> Quizás calificas para usar el sistema. Cuéntame a quién le envío más info, o si te la mando por aquí. Abrazo.

The loom-offer first-touch (above) stays the ARCHIVED exemplar; A/B is the active test. When the operator says "change templates", swap this block.

## Warm / follow-up register (from real WhatsApp threads — e.g. somoshobby/Felipe, 2026-10)
Once a lead replies or a client is onboarding, this is his register (mirror it, it is NOT the cold first-touch):
- Warm + confident + calm, reassuring, zero pressure: "Dale {first}.", "Hola {first}, feliz lunes! A empezar la semana con todo!", "Gracias a ti {first}.", "Increíble me parece!", "Cualquier cosa estoy aquí.", "Abrazo, estamos hablando en un rato."
- Frames value as natural result of doing the work: "una venta o conversación avanzada paga la inversión y mucho más", "mientras las tareas sean cumplidas eso sucede naturalmente", "cuando las cosas se hacen bien el resultado es mejor aún".
- Offers help to the client's team: "Si necesitas que le aclare dudas a alguien de tu equipo, feliz lo hago."
- Short exclamations, "!", warm closes ("Abrazo"), tú, LATAM. Never corporate, never pushy.

## Voice rules (mirror exactly)
- CTA first; every message ends in a QUESTION or a DATE, never a period.
- Short: ~3-4 lines, one idea. LATAM Spanish (tiempo/dale/ustedes/tomar/celular). Anglicisms OK (match, contact cards, clicks). No em dashes. No corporate words (optimizar, potenciar, robusto, integral, sinergia).
- AFFIRM, don't agitate: no "¿estás harto?" / "imagina si". Say who it's NOT for. "Cuéntame si te acomoda." "el mejor ejemplo, irónicamente, soy yo."
- "no es X, es Y" only when genuinely different things.

## ICP + exclusions
- B2B only. **"No calificas si vendes a consumidor final."** Decision-maker = owner/founder/CEO/partner.
- Sectors = resembling current clients: agencies, studios, service-sellers, productoras.
- EXCLUDE (enforced in `factory/packages/icp_filters.py`): global brands/giants (Stripe, Havas, big agency networks), franchises/chains, schools/universities (.edu), chambers/associations/foundations, government (.gob/.gov). NOT generic single-token names (those are real small agencies).

## Social proof (real metrics only, never invent)
- LockPro (current client): ~120-140 envíos/semana, 5-7% respuesta. USE EVERYWHERE.
- UnaBase: ~75 decisores contactados, 5-10 conversaciones, 7-10% efectividad.
- "el mejor ejemplo, irónicamente, soy yo" (reaches prospects with his own system).
- Anchors: "Una negativa vale 10x más que el silencio." "No es magia. Es un sistema que convierte tu embudo en una disciplina."
