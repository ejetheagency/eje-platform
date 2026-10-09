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

**Max 4 sentences.** The offer is **one plain line** ("hacemos foto, video y dron de eventos de planta"): no
feature list, no brand-introduction paragraph, **never the sender's city** when it differs from the prospect's
region. Lead with the edge, not with geography. Sound like a person: "Qué tal" / "Hola", short sentences, one
casual aside allowed. Use accents on names (Mónica, Raúl) unless a signature spells it otherwise.

- **Door 1, Patrón A:** greeting + the one real observation + offer line + Patrón C question.
- **Door 1, Patrón B:** honest cold open **plus ONE true why-them clause**:
  *"Te escribo en frío porque vi que este año inauguraron la planta de Apodaca, y esas son de las fechas que vale
  la pena tener bien grabadas."* The why-them line comes from a real company moment worth filming: anniversary
  year, plant inauguration or expansion this year, a family-day or recognition program on their careers page, a
  recent award. **One clause, plain words, no numbers, no inference about what it means for them.**

- **THE "SO WHAT" TEST, applied to every why-them line.** Reading it, the recipient must think *"ah, that is why
  he is writing me"*. True is not enough. "Tienen una página de reclutamiento", "mantienen sus redes activas" and
  "traen reclutamiento abierto" are all true and all meaningless: they do not connect to why this company would
  want its event filmed. If the line does not make that connection, it fails and gets cut.

- **FALLBACK when no fact passes: the sender's own truth + an imagined scene**, framed as imagining and **never as
  fact**: *"Trabajamos seguido dentro de plantas y me imagino que juntar a todo <empresa> en una posada es todo un
  operativo."* The scene must be **specific to that company's real shape** (its number of plants, its shifts, its
  business units, its plazas, its sector), never generic. A scene that would fit any company is the same template
  failure in a different costume. This fallback is preferred over a weak fact.

- **NO LOCALITY CLAIMS** ("aquí", "aquí en el área", "a la vuelta") unless the sender is actually local to the
  prospect's region. Writing "aquí en el área" from another city is simply false and it is the kind of lie a
  prospect catches instantly.
- **NO TWO DOOR-1 MESSAGES MAY SHARE THEIR FIRST TWO SENTENCES.** Ten identical openers is a template, and the
  prospect sees it immediately. **Vary the capacity close too**: "¿ya tienen quién lo cubra?", "¿eso lo ves tú o
  alguien de comunicación?", "¿lo graban internamente o con alguien de fuera?", "¿ya está asignado o todavía lo
  están viendo?", "¿lo arman ustedes o lo contratan?".
- **Patrón C close:** a capacity question that can be answered with a no. **Never "¿te interesa?"**
- **Doors 2+, Patrón H only:** *"Le escribí a <nombre> hace unos días sobre <tema> y no he tenido respuesta, lo
  cual es normal en estas fechas. Te escribo porque cae cerca de tu área. ¿Con cuál de los dos sigo?"*
  It must be **inclusive and never imply going over door 1's head**, and **never imply door 1 agreed to anything**.
  Banned: "me permito escribirle a usted directo".
- Doors 2+ **never repeat door 1's pitch** and never repeat the brand paragraph.

## Step 7d: unknown plant size

A company with no public headcount is allowed **only with a labeled proxy**: a press line ("más de X empleos"),
**job-posting volume**, or plant area. The label must say it is a proxy, not a headcount. **With no proxy, replace
the company.**

## Step 8: the self-selling layer (standard on every demo)

1. Per company: **its own hook with source** and a **"Por qué ahora"** tied to a filmable or time-bound moment
   (plant opening, expansion, anniversary, hiring wave, a past posada or family day they posted publicly).
   No leftovers from a previous prospect's research.
2. Per door: **its own message**, written to the patterns in step 7c (max 4 sentences, Patrón A or B on door 1,
   Patrón H on doors 2+, Patrón C close). **Doors 2 and 3 name door 1**, so the name circulates inside the account
   without ever implying that person agreed to anything.
3. **"Ruta sugerida"** per account: order of doors and channels, each with a one-line reason.
4. **Contextual coach bubbles**: by company size, by channel, by door type. Any number shown needs a public source
   link or the label **"estimado inicial, el sistema lo ajusta con tus respuestas"**. No invented statistics.
5. **Season countdown** in the header, configurable per prospect.
6. **Company channel links**: website, LinkedIn, Instagram, Facebook, YouTube, published WhatsApp, phone.
7. **"Lo que el sistema hizo hoy"** at the top, **computed from the JSON** so it cannot drift: accounts, personal
   emails (confirmed vs sin fecha), sources checked, and **what was discarded and why**. The discards sell harder
   than the finds.
8. **Closing block**: plan line, contact (email + WhatsApp from config), referral ask. No prices.

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
