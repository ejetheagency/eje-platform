# Sector templates (the reusable first-touch library)

These are **first-touch templates by SECTOR**, written in the operator's register and meant to be **replicated across
any client that shares the industry** (not locked to one account). They are the **floor**: every lead inherits its
sector template with merge fields; the AI-composed pitch only *upgrades* it, so a card is never empty.

Stored on a client as `clients.icp_config.outreach_first_touch` (+ `sender_name`, `sector_template`). The factory
`publish` worker and the app both merge the tokens below.

## Merge tokens
- `{first}` — decisor first name · `{decisor}` — decisor full name
- `{company}` — target company/brand
- `{sender}` — the client's person who sends (from `icp_config.sender_name`)
- `{industry}` — target industry
- `{brands}` — similar brands/accounts (AI fills with real names; floor degrades to "la tuya")

## Pattern: "permiso para enviar más info"
Cold but warm · selection ("tenemos clientes similares a {company}") · what we do in the sector's language · small-team
credibility + years · soft offer of references/past work · the ask: *"¿Te mando la info por aquí mismo o a alguien más
del equipo?"* No pressure, no corporate slop.

---

## estudio-de-branding  (live on: somoshobby) — APPROVED by operator 2026-10-05
> Hola {first}, ¿cómo estás? Te habla {sender} de @somoshobby. Les escribimos en frío ya que tenemos clientes similares a {company} y sentimos que quizás les interesaría escuchar qué hacemos. Te cuento: ayudamos a marcas como {brands} a crear un mundo estético y verbal alrededor de sus marcas. Somos un equipo pequeño y llevamos creando mundos desde hace 16 años, por lo tanto entregamos toda nuestra atención y experiencia a cada proyecto. Con gusto te envío referencias y proyectos pasados para que te hagas una idea. ¿Te mando la info por aquí mismo o a alguien más del equipo?

## productora-video-corporativo  (for: nanovideos) — DRAFT (Claude's attempt at the pattern, pending operator review)
> Hola {first}, ¿cómo estás? Te habla {sender} de NanoVideos. Les escribimos en frío ya que trabajamos con áreas de Personas similares a la de {company} y sentimos que quizás les interesaría ver qué hacemos. Te cuento: ayudamos a equipos de RRHH y Comunicaciones Internas a convertir sus inducciones, capacitaciones y comunicación interna en video que la gente de verdad ve y recuerda, en vez de un manual que nadie abre. Somos un equipo pequeño y llevamos años creando contenido que engancha a los colaboradores, por lo tanto entregamos toda nuestra atención y experiencia a cada proyecto. Con gusto te envío ejemplos y proyectos pasados para que te hagas una idea. ¿Te mando la info por aquí mismo o a alguien más del equipo?
