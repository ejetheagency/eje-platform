---
name: account-demo
description: Build a self-selling account demo for a prospect from public data only. Input a prospect name + ICP text (optionally a city list); output demos/<prospect>/index.html + leads.json + a fill-rate report. Use for any prospect demo, account research, or "find me decision-makers at X kind of company" request.
---

# Account demo: one prospect, one command, zero manual pushing

Turn a prospect's ICP into a guided "day in the system" page built on real, sourced accounts. Everything here was
learned by doing it wrong first on REBRND (Oct 2026). The targets below are the definition of done, not aspirations.

## Input and output

**Input:** prospect name, ICP text in their own words, optionally a city list and a season date.
**Output:** `demos/<prospect>/leads.json`, `demos/<prospect>/config.json`, `demos/<prospect>/index.html`, and a
fill-rate report in chat.

**Build:** `python3 demos/_template/build.py <prospect>`. Layout and copy live in the template; everything
prospect-specific lives in the two JSON files. Never hand-edit `index.html`.

## Hard rules (break these and the demo is worthless)

- **Never invent anything.** Not a name, not an email, not a phone, not a statistic. A missing input renders a
  visible `falta`, never a placeholder. A fake `wa.me` number on a page whose whole pitch is "nothing is guessed"
  destroys the demo.
- **No paid APIs** (no Serper, Hunter, MillionVerifier, Places). Web search and web fetch only.
- **No scraping LinkedIn or Instagram.** Linking a public company account or a profile URL that appeared in search
  results is fine. Reading a name off a search-result title is fine. Fetching the profile is not.
- **No em dashes anywhere** (global rule). The build asserts this and fails if one slips in.
- **Never personal cell numbers, personal emails, home addresses, or anything behind a login.**
- **No prices on the page.** Price is a conversation, not a web element.

## Step 1: account selection

- **Mid-size first: 250 to 2,000 employees.** They decide faster and the plant decides its own event. This is the
  real market; mega-corporations are where research goes to die.
- **Maximum 2 big accounts**, and a big one only earns its place if you find a **plant-level route** (plant HR,
  plant comms, a published recruitment channel). **One big account may stay as the "conmutador + formulario"
  example**, with a coach note explaining that big companies centralize on switchboards and forms to filter
  suppliers: it is their design, not a snub.
- Mix sectors and cities. Prefer companies with a recent filmable moment (see hooks).
- **Replace, don't settle.** A company that misses the targets after the full method list gets swapped out. Gaps
  are only acceptable with a full attempt log *after* replacement has been exhausted.

## Step 2: doors (who actually buys)

Doors are manager-level people who would really sign for this offer:
**RR.HH. / Capital Humano, comunicación interna, capacitación, compras, gerencia de planta.**

- **C-suite is "contexto" only.** Never door 1, never the primary mailto, and **never counted** toward targets.
  A founder or CEO is useful to name-drop, not to sell to.
- Every door needs a role, an entry route, a confidence badge with source links, and its own message.
- Where no name is public, the door is `por identificar` with the entry route spelled out (switchboard, form,
  recruitment channel). That is an honest gap and reads better than a filled cell.

## Step 3: the email method list, in order

Run it in this order and stop when the targets are met:

1. **`"@domain"` search**, plus the same with `pdf`, `proveedores`, `vacante`, `CV`, `contacto`, `prensa`.
2. **Job postings**: company careers page, OCC, Computrabajo, Indeed MX, university job boards. `"envía tu CV a..."`
   is usually a real HR person at that plant. **This is the single highest-yield source and it was the one missed
   on the first pass.**
3. **Supplier and procurement docs**: supplier manuals, registro de proveedores, códigos de conducta, licitaciones,
   ISO / Industria Limpia certificates.
4. **Sustainability and annual report PDFs**, press releases ("contacto de prensa").
5. **Chamber and cluster directories**: CAINTRA, CANACINTRA, clusterindustrial, sector associations (ANFACA gave a
   better, openable source than a paywalled data broker), event sponsor pages, university partnership pages.
6. **Pattern**: any published personal email at the domain gives the pattern. **Apply it to every named door at
   that company.** This is the fastest multiplier: one company went from 0 to 4 routes this way.
7. **Surname-only inboxes** (`jlopez@`): try to upgrade by matching initial + surname to a named person at that
   company. Until the full name is confirmed, the inbox is a route but the person is not "named".
8. **Free MX lookup** to confirm the domain receives mail. No SMTP probing.

Email status is always one of: `publicado` / `patrón inferido` / `buzón de área` / `ruta débil` / `no encontrado`,
each with a source link.

## Step 4: counting rules (this is where honesty lives)

**Only personal emails tied to a named, non-contexto person count toward the target.**

- **Área / team / program inboxes do NOT count.** `rrhh@`, `info@`, `contacto@`, `compras_@`, `proveedores@`,
  `pg_integracion_talento@` and any role or program alias reach whoever answers, not a decision maker. They go in
  a separate **"Rutas adicionales"** block under the doors and are **never the primary mailto**.
- **A sister-company inbox is never a route.** Same group is not same company.
- **A sales inbox is never a door.** That team sells, it does not buy event video. Mark `ruta débil`, show it only
  as a redirect, never prefill it.
- **Contexto doors never count**, even though they are real personal emails.
- Two inboxes that reach the same place count once.

## Step 5: currency (the Nora Sanchez rule)

A directory listed a woman as HR manager at a company she left in **2013**. She is now somewhere else. Sending to
her would have been the most visible possible failure.

- **Sources older than 2023 need a newer confirmation or the person is discarded.**
- **Undated directory sources** (commercial data brokers) get status **"sin fecha, verificar vigencia"** and are
  confirmed by phone before sending.
- **Report two numbers: confirmed, and total including sin fecha.** A demo may show sin fecha with its label.
  **A client report counts only confirmed.**

## Step 6: labels, evidence, proof

- Every value carries a source link and a status chip: `verificado` / `inferido` / `no encontrado`.
- **Every personal email carries a "Cómo lo encontramos" toggle**: name source (link) -> pattern source (link) ->
  resulting address. That is the proof the prospect can click.
- **Every door carries a counting chip**: `cuenta: confirmado` / `cuenta: verificar vigencia` /
  `no cuenta: contexto`.

## Step 7: hard targets (definition of done)

| Target | Value |
|---|---|
| Personal emails per company | **>= 2** |
| Personal emails total | **>= 20** |
| Companies with >= 1 personal email | **all non-exempt (9 of 10)** |
| Companies with >= 2 personal emails | **>= 7** |
| Named manager-level door per company | **>= 1** |

**THE BIG-ACCOUNT EXEMPTION.** The one big account kept as the **"conmutador + formulario" example is exempt from
the email targets**. Its job is to teach why big companies route through switchboards and forms, so having zero
published emails is the point, not a failure. It still needs its hook, doors, route, coach and attempt log.
**Targets apply to the other 9.** Exactly one account may be exempt.

**THE REPLACEMENT CAP.** Missing a target means **replacing the company**, not lowering the bar, but replacement is
capped: **maximum 2 replacements per slot.** After the second replacement also falls short, **accept a documented
gap**: keep the best of the three, attach its full **attempt log** listing every method tried, and **show the gap
in the report** rather than hiding it. Endless replacement is how a day disappears with nothing shipped.

## Step 7b: FACT HUNT, before writing a single message

Do this per company, as a research step, not as a writing step.

- Look for the company's **OWN event content**: posada, fin de año, día de la familia, aniversario, inauguración,
  as photos or video on **their** Facebook, Instagram, YouTube, LinkedIn page or site, **dated within the last 18
  months**. Link it. For an event-video prospect this is the preferred fact, because it proves the event exists.
- Second choice: **one specific first-party fact** (their own post or page). Not a news inference.
- **Banned**: inferences dressed as facts ("la posada va a ser más grande", "si la plantilla está creciendo"),
  **stacked facts (maximum ONE)**, news-scraped headline facts (investment amounts, job counts), invented numbers.
- **The 1,000-companies test**: could this sentence be sent to a thousand companies by changing the name? If yes,
  cut it. "Vi que están creciendo" fails. "Vi que el año pasado hicieron su posada el 13 de diciembre" passes.
- Record the result per company as **Patrón A** (fact found, with link and date) or **Patrón B** (no qualifying
  fact). Expect most companies to be B: that is the honest outcome, not a research failure.

## Step 7c: message patterns (the copy rules)

**REGISTER: always tú, never usted.** Every message, every channel, every door: *te escribo, tu área, ¿ya tienen
quién lo cubra?, ¿eso lo ves tú?*. This is the default for **all demos and client messages** and changes only if a
client's `config.json` overrides it. Do not switch register by channel.

Keep it short, the length of the client's own sample. **Never the sender's city** when it differs from the
prospect's region. No feature list and no brand-introduction paragraph beyond what the client's sample carries.

- **THE MESSAGES ARE NOT YOURS TO WRITE.** Templates come from the client's own voice samples, stored in
  `config.json` under **`voice_samples`** (one for door 1, one for doors 2+). The system **only fills the
  variables** and, when a hook passes the "so what" test, swaps it into the same sentence in the same tone.
  **It never writes the voice itself and never rephrases for variety.**
  **If a client has no voice samples, ASK FOR THEM before generating any message.** Do not invent a voice to fill
  the gap: a generated voice is the thing that reads as AI, no matter how good the phrasing is.

- **Keep the client's imperfections.** If they write without accents, in lowercase, with run-on sentences, keep it.
  "aqui", "en frio", "revise la compañia", a lowercase "te envio mas info por aqui?" are the signal that a person
  wrote it. Correcting their Spanish is how a human template turns back into an AI message. Proper names keep
  their accents (Mónica, Raúl); the client's own words keep the client's spelling.

- **The same message across companies is FINE.** It is a human template, which is exactly what a person sending
  twenty messages a day actually uses. Artificial variation is a tell, not a feature. Do not vary wording to make
  messages look different.

- **THE "SO WHAT" TEST, for the optional hook.** A hook earns a place in the template only if, reading it, the
  recipient thinks *"ah, that is why he is writing me"*. True is not enough: "tienen una página de reclutamiento"
  and "mantienen sus redes activas" are true and meaningless. If no hook passes, **send the template as written**.
  Expect most companies to have no hook.

- **HOOK PLACEMENT: insert, never replace.** The hook goes **immediately before** the sentence that names the
  service, never in its place, so the pronoun that follows ("con eso") still points at the service and not at the
  hook. Replacing the clause silently changes what is being offered: a posada hook became an offer to help with
  *last year's posada*, and a hiring hook read as an offer to *fill their job opening*. Keep the hook short and
  plain so it reads as an aside, not as the subject of the sentence.
  Correct: *"...clientes que tengo hoy. <hook>, entiendo que hacen eventos internos y nosotros eventualmente
  podemos ayudar con eso. te envio..."*

- **NO LOCALITY CLAIMS** ("aquí", "aquí en el área") unless the sender is actually local to the prospect's region.

- **The close comes from the client's sample too.** Whatever question their own message ends on is the close.
  The only constraint: it must be answerable with a no, and it is **never "¿te interesa?"**.
- **Doors 2+ use the client's second sample**, the one that names door 1 and hands the choice to the reader. It
  must be **inclusive, never imply going over door 1's head**, and **never imply door 1 agreed to anything**.
  Match the pronoun to door 1's gender ("sigo con ella o contigo?" / "sigo con el o contigo?").
  Banned in any register: "me permito escribirle a usted directo".

**Worked example (REBRND, Oct 2026).** The client's own two samples, filled with variables only:
> *Door 1:* "Hola <nombre>, aqui Carlos de @rebrnd. Te escribo en frio ya que revise la compañia y tienen un
> perfil similar a clientes que tengo hoy. entiendo que hacen eventos internos y nosotros eventualmente podemos
> ayudar con eso. te envio mas info por aqui? o a alguien mas del equipo."
> *Door 1 with a hook that passed:* same text with "entiendo que hacen eventos internos" replaced by
> "vi que el año pasado hicieron su posada el 13 de diciembre".
> *Doors 2+:* "Hola <nombre>, aqui Carlos de @rebrnd. Le escribi a <puerta 1> hace unos dias sobre los eventos
> internos y no me ha respondido, normal. Te escribo porque cae mas cerca de tu area. sigo con ella o contigo?"
Note the missing accents and the lowercase: that is the client's hand and it stays.

## Step 7d: unknown plant size

A company with no public headcount is allowed **only with a labeled proxy**: a press line ("más de X empleos"),
**job-posting volume**, or plant area. The label must say it is a proxy, not a headcount. **With no proxy, replace
the company.**

## Step 8: the self-selling layer (standard on every demo)

1. Per company: **its own hook with source** and a **"Por qué ahora"** tied to a filmable or time-bound moment
   (plant opening, expansion, anniversary, hiring wave, a past posada or family day they posted publicly).
   No leftovers from a previous prospect's research.
2. Per door: the client's template with variables filled (step 7c). **Doors 2 and 3 name door 1**, so the name
   circulates inside the account without ever implying that person agreed to anything.
3. **"Ruta sugerida"** per account: order of doors and channels, each with a one-line reason.
4. **Contextual coach bubbles**: by company size, by channel, by door type. Any number shown needs a public source
   link or the label **"estimado inicial, el sistema lo ajusta con tus respuestas"**. No invented statistics.
5. **Season countdown** in the header, configurable per prospect.
6. **Company channel links**: website, LinkedIn, Instagram, Facebook, YouTube, published WhatsApp, phone.
7. **"Lo que el sistema hizo hoy"** at the top, **computed from the JSON** so it cannot drift: accounts, personal
   emails (confirmed vs sin fecha), sources checked, and **what was discarded and why**. The discards sell harder
   than the finds.
8. **Closing block**: plan line, contact (email + WhatsApp from config), referral ask. No prices.

## Step 8b: where the demo LIVES (the real app, not a page)

A demo is a **demo client inside the real app**, on the same link and the same design system. A prospect who
sees a one-off page sees a brochure; a prospect who sees his accounts inside the product sees the product.

- Publish the accounts as `public/demo-<slug>.json` (`build.py` does this: `publish_demo_client`). ONE CARD PER
  COMPANY, because the app keys cards by website hostname and two doors on one domain would collide. The extra
  doors ride inside the card, never as synthetic domains (inventing a URL to win a unique key is inventing data).
- The app opens it with `?demo=<slug>`, which stores `eje_ws=demo-<slug>`. A `demo-` workspace reads that static
  JSON and **never touches Supabase**: nothing to authenticate against, nothing another client could leak into it,
  and `canWrite()` stays false so a demo can never write.
- The guidance extras (time bar, countdown, coach, "lo que el sistema hizo hoy", evidence toggles, closing block)
  live in the **Guía** tab, built from the app's existing components and tokens only. Never add a palette, a font
  or a layout of your own to `app.html`.
- Everything demo-only sits behind `if(EJE_DEMO)`. **Declare the flag at script top level**, not inside the auth
  gate's IIFE, or `load()` and `renderGuia()` will not see it (this cost a debugging cycle once).
- Gate before committing: `node --check` every inline script, plus a screenshot diff proving the app with demo
  OFF is **pixel-identical** to `main`, plus `golden_<client>` on the branch.
- Work on a branch (`demo-mode`), never `main`. Vercel builds a preview URL; production stays untouched.
- The standalone `demos/<slug>/index.html` is **fallback only**, for sending a file when no link will do.

## Step 9: verification before reporting (never skip)

- **Every URL checked.** Bot-blocked ones (Facebook 400, LinkedIn 999, broker 403) opened in a real headless
  browser to confirm they exist; anything genuinely dead is **replaced, not cited**. A source the prospect cannot
  open is not a source.
- **Every mailto byte-matched** against the data, with **no pattern template in a To: field** and **no area inbox
  as a primary recipient**.
- **390px mobile**: Chrome headless clamps the viewport to 500px, so verify inside a 390px iframe and assert
  `scrollWidth == 390` with zero overflowing elements.
- **Zero em dashes.** **No invented values anywhere.**

## Step 10: report format

1. **Fill rate vs target first** (per the concise-CEO-report rule).
2. Per-company table: personal emails, named doors, area inboxes, attempt log.
3. Gaps with their logs, and the decisions the operator needs to make.

## What this skill does NOT do yet

- It does not write to the `leads` table or the `client_deliveries` ledger. Demo output is standalone.
- It has no paid-provider enrichment and no verification of deliverability (no MillionVerifier), so
  "patrón inferido" stays unverified until someone calls.
- Account discovery is manual-search driven; there is no scheduled or capped run. That is PLAN item 3b.
