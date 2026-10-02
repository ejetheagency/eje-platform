# Outreach Playbooks: Addendum to the Master Plan

> **For the AI assistant reading this in the repo:** This extends `docs/ENRICHMENT_MASTER_PLAN.md` §11 (Template Library) and §4 (Lead Lifecycle). It defines a *playbook*: a sequence of touches across channels with a stated intent per step, stored as data, executed by the task worker, measured by outcome, and shown to clients as the reason behind each "siguiente tarea." The first playbook below is reconstructed from a real conversation that turned a "no" into a request for a proposal. Treat it as the seed of the library, not as a hardcoded flow.

---

## 1. Why playbooks, not templates

A template is one message. A playbook is the *sequence*: which channel, after how many days, with what intent, and what to do when the answer is no. The reply rate of a system that only sends first messages is a fraction of one that runs the whole sequence. Daniela replied on touch 3, after a channel switch; she asked for a proposal on touch 6, after a "no." Neither would exist with a single email.

Playbooks are also what the system teaches. Every "siguiente tarea" the client sees carries the step's intent in one line ("tercer toque: cambio de canal y pregunta de capacidad"), so the client learns the discipline by doing it, not by reading a guide.

---

## 2. Data model

```
playbooks
  id, name, version, channel_set, mode (broad | account_based), author, status (draft | active | retired)

playbook_steps
  playbook_id, step_no,
  trigger,            # after_days: N | on_reply | on_soft_no | on_hard_no | on_question
  channel,            # email | instagram_dm | linkedin | whatsapp | voice_note | call
  intent,             # one-line, human-readable; shown to the client as the "why"
  template_id,        # from the template library (approach, not text)
  required_fields,    # personalization fields the message must have
  stop_if             # e.g. replied, unsubscribed, hard_no_twice

playbook_runs
  id, playbook_id, lead_id, client_id, started_at, current_step, state
  # state: running | replied | soft_no | hard_no | reopened | nurture | converted | stopped

touches
  run_id, step_no, sent_at, channel, template_id, message_hash, outcome
  # outcome: none | seen | replied | soft_no | hard_no | question | reopened | asked_for_material
```

`touches.outcome` is the training signal. The Strategist ranks playbooks (and individual steps) by replies, reopens and conversions per lead, per ICP type, per channel. Same 80/20 allocation as pivots.

New lead states (extend master plan §4): `SOFT_NO`, `REOPENED`, `NURTURE`. A soft no is a reply that declines without closing the door ("no nos sirve," "por ahora no"). It is a state, not an end. A hard no ("no me escribas más") ends the run and flags the contact.

---

## 3. Playbook 01 · "Cambio de canal y reapertura" (reconstructed from a real run)

Target: owner of a small design studio, Chile. First channel email, no reply.

```yaml
playbook:
  id: pb_001_channel_switch_reopen
  name: Cambio de canal y reapertura
  mode: broad
  steps:
    - step: 1
      trigger: { start: true }
      channel: email
      intent: "Primer contacto con un dato real de su empresa y la propuesta en una linea."
      required_fields: [first_name, company, one_real_fact]

    - step: 2
      trigger: { after_days: 4, if: no_reply }
      channel: instagram_dm
      intent: "Cambiar de canal. Nombrar el correo anterior. Ofrecer un resumen aqui, sin repetir el pitch."
      example: "Hola Daniela! Te escribi un correo hace unos dias desde EJE. Quede esperando tu respuesta. ¿Quieres que te haga un resumen por aqui?"
      required_fields: [first_name]

    - step: 3
      trigger: { after_days: 3, if: no_reply }
      channel: instagram_dm
      intent: "Tono humano. Reconocer que los mensajes se perdieron (sin culpar). Decir por que ella: calza con el perfil de un cliente. Pitch en dos lineas. Terminar con una pregunta de capacidad, no con una pregunta de interes."
      example: |
        Hola Daniela! Como estas? Me imagino que ocupadisima jajaja
        Oye te cuento; te he escrito un par de veces y se han perdido los mensajes.
        Calzas con el perfil de alguno de mis clientes por lo tanto pense en ti hoy.
        Te cuento en cortisimo: abrimos conversaciones con tus clientes ideales y luego tu cierras la venta :). Podemos coordinar una demo si quieres explorar.
        Cuentame. Si tienes capacidad para 5-10 conversaciones extra semanales puede funcionarte.
      required_fields: [first_name, why_her_one_line]
      notes: "La pregunta de capacidad ('¿tienes capacidad para X?') invita a responder aunque la respuesta sea no. Una pregunta de interes ('¿te interesa?') invita al silencio."

    - step: 4
      trigger: { on: soft_no }
      channel: voice_note
      intent: "No discutir el no. Preguntar como consiguen clientes hoy. Voz, no texto: una voz es una persona, un texto es un pitch."
      example_prompt: "¿Y hoy como les llegan los clientes, mas que nada?"
      stop_if: hard_no

    - step: 5
      trigger: { on: answer_to_step_4 }
      channel: voice_note
      intent: "Reencuadre con lo que ella dijo. Si nombra referidos o anuncios: 'esa es una maquina; la otra es la que falta; las dos juntas es el ideal'. Sin pedir nada todavia."
      required_fields: [their_current_channel]

    - step: 6
      trigger: { on: reopened | asked_for_material }
      channel: instagram_dm
      intent: "Celebrar lo que tienen (flujo), no minimizarlo. Posicionar el sistema como 'para no depender de eso'. Enviar material por el canal formal (email) y dejar la puerta abierta sin presion."
      example: |
        Me parece increible que esten con flujo.
        Yo eventualmente los puedo ayudar a no depender de eso. Y esas dos maquinas funcionando es el ideal :)
        Te envio una presentacion por email y me comentas.
      next_state: nurture
      nurture_rule: { after_days: 21, channel: email, intent: "Un dato nuevo, una linea, sin pedir reunion." }
```

Observed outcome: touch 3 produced a reply (soft no). Touch 4 and 5 answered the question and reframed. Touch 6 produced a request for a presentation. State: `NURTURE`, with the proposal sent.

---

## 4. What made it work (rules the system enforces, not suggestions)

1. **Switch channel before repeating the message.** A second email is the same message twice. An Instagram DM that names the email is a second person knocking.
2. **Name the previous touch.** "Te escribi un correo," "te he escrito un par de veces." It signals persistence without pressure, and it is honest.
3. **Say why her, in one line.** "Calzas con el perfil de uno de mis clientes." The reader learns she was chosen, not scraped.
4. **End with a capacity question, not an interest question.** "¿Tienes capacidad para 5-10 conversaciones extra?" is easy to answer either way. "¿Te interesa?" is easy to ignore.
5. **A soft no opens a question, not a rebuttal.** Ask how they get clients today. Whatever they answer is the material for the reframe.
6. **Voice after a no.** A voice note after a "no" reads as a person who heard her. Text reads as a script that did not.
7. **Reframe with their words.** They said referrals and ads, so: that is one machine, this is the other. The pitch becomes their own diagnosis.
8. **Celebrate what they have before offering what they lack.** "Me parece increible que esten con flujo." Then: "para no depender de eso."
9. **Move material to the formal channel.** Proposal by email, conversation on Instagram. Two channels, two roles.
10. **Leave in `NURTURE`, not `CLOSED`.** "Por ahora estamos bien" is a date, not a verdict. The system schedules the next light touch; the human does not have to remember.

---

## 5. How the system uses this

- **Execution.** The task worker reads `playbook_steps` and creates the client's "siguiente tarea" with channel, suggested text (generated from the template approach + the lead's facts), and the intent line. The client clicks, reviews, sends from their own account, and marks the outcome. The system advances the run.
- **Teaching.** The intent line is visible on every task. After 30 days a client has read "cambio de canal," "pregunta de capacidad," "reencuadre con sus palabras" dozens of times, attached to real people. That is the training.
- **Learning.** Nightly, the Strategist computes per playbook and per step: reply rate, soft-no-to-reopen rate, material-requested rate, conversion rate, per ICP type and channel. Steps that do not move outcomes get fewer runs; variants get tried in the 20% exploration slot. A playbook that works for design studios in Chile is proposed to the next design studio automatically.
- **Capturing new playbooks.** When the founder (or later, a client) runs a sequence by hand that produces a reply, the admin page offers "Guardar como playbook": it reads the touches from the lead's history, asks for the intent line per step, and stores a draft. This is how the library grows from real conversations, which is the only source worth having.
- **Account-based mode.** Playbooks for `account_based` clients add a step type `next_person_same_company` with the citation rule ("le escribi a Andrea la semana pasada"). Same engine.

---

## 6. Rules added to the codebase

1. No message is sent outside a playbook run. Even a one-off has a one-step playbook, so the outcome is recorded.
2. Every step has an `intent` string. A step without intent is rejected at validation.
3. Soft no and hard no are different states with different consequences. The classifier that labels replies must distinguish them; when unsure, it labels `question` and routes to the human.
4. Nurture touches are capped (config: `nurture_max_touches: 3`, `nurture_interval_days: 21`). After that, `PARKED`.
5. Playbooks are versioned. A change creates a new version; runs in progress finish on the version they started.
6. Templates carry an approach, never the literal text of a previous message. The examples in this document are illustrations of the approach, not strings to reuse.
