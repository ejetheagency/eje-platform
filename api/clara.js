// api/clara.js  ->  POST /api/clara
// Clara: the in-product assistant. She knows (1) the app (manual), (2) the client's ICP (clients.icp_config),
// and (3) the user's live context (current tab + a real data snapshot). She can ANSWER/guide OR actually
// REGISTER a prospect into Seguimiento (tracked_leads) — and only confirms what she really did.
// body: { client_id, message, context:{view,summary}, history:[{role,text}] } -> { reply, logged, tracked_lead? }

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { route, parseJSON } = require("./_lib/llm");
const { readBody, send } = require("./_lib/http");

const STAGES = new Set(["nuevo", "contactado", "respondio", "conversacion", "reunion", "propuesta", "ganado", "perdido", "pausa"]);
const SOURCES = new Set(["referral", "inbound", "event", "manual", "ad_ig", "ad_meta", "other"]);

// Clara is BETA and INFO-ONLY for now: she answers/guides + summarizes (read-only). Note-writing is OFF
// until it's smart enough (it echoed the raw message and could hit a stray lead). No writes = no mess for clients.
const CLARA_WRITES = false;

const MANUAL =
  "Sos Clara, la asistente de EJE. EJE NO es un CRM común: es un GENERADOR DE CONVERSACIONES ACCIONABLES. " +
  "Ayudás al usuario a INICIAR conversaciones con sus clientes potenciales con el menor esfuerzo. Pestañas:\n" +
  "- Inicio: resumen + tus números (gráficos de conversaciones generadas, embudo, meta del día). Acá viven los 'Resultados'; NO hay pestaña aparte llamada Resultados.\n" +
  "- Hoy: tarjetas de decisores del día para contactar en un clic (copia el mensaje y abre el canal).\n" +
  "- Tareas: cajas de acción — Conversaciones (quién respondió), Tareas para hoy (ejecutor que se desliza, una tarjeta por tarea con el canal correcto), En cola (próximos pasos y cuándo).\n" +
  "- Decisores: base de datos buscable de todos los decisores.\n" +
  "- Seguimiento: para registrar y seguir prospectos de fuera (ad, referido, inbound). El usuario te CUENTA qué pasó y vos lo registrás DE VERDAD.\n" +
  "- Historial: reportes y días anteriores.  - Ajustes: cuenta y tema.\n" +
  "'Plantillas' todavía NO existe (llega pronto). Nunca menciones pestañas ni funciones que no existen.\n" +
  "Canales: correo, Instagram DM, LinkedIn, WhatsApp. Cadencia: 1er email -> IG DM -> 2º email.\n" +
  "Playbook: el objetivo es iniciar conversaciones y llevar a una reunión. La nota de voz por Instagram es lo que MÁS convierte cuando un lead se pone tibio. Primer toque cálido con un dato real de la empresa. Nunca descartes un lead por un canal faltante.\n";

module.exports = async (req, res) => {
  if (req.method !== "POST") return fail(res, 405, "method not allowed");
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const b = await readBody(req);
  const { client_id, message } = b;
  if (!client_id) return fail(res, 400, "client_id required");
  if (!canAccess(ctx, client_id)) return fail(res, 403, "forbidden");

  // PREDETERMINED ACTION — summarize a Seguimiento lead's notes (reliable, no free-form ambiguity).
  if (b.action === "summarize_lead" && b.tracked_lead_id) {
    try {
      const t = await db.select("tracked_leads", `client_id=eq.${encodeURIComponent(client_id)}&id=eq.${encodeURIComponent(b.tracked_lead_id)}&select=company,decisor_name,stage`);
      if (!t[0]) return send(res, 200, { reply: "No encontré ese lead." });
      const notes = await db.select("tracked_lead_notes", `client_id=eq.${encodeURIComponent(client_id)}&tracked_lead_id=eq.${encodeURIComponent(b.tracked_lead_id)}&select=note_text,created_at&order=created_at.asc`);
      const notesText = notes.map((n) => "(" + String(n.created_at).slice(0, 10) + ") " + String(n.note_text || "").replace(/\s+/g, " ")).join("\n") || "(sin notas)";
      const p = "Resumí en 2 o 3 frases cortas, en español neutro y directo (sin guiones largos, sin repetir), qué está pasando con este lead y cuál es el próximo paso concreto. " +
        "Lead: " + (t[0].company || "") + (t[0].decisor_name ? (" (" + t[0].decisor_name + ")") : "") + " · etapa actual: " + t[0].stage + ".\nNotas (cronológicas):\n" + notesText;
      const reply = String(await route(p) || "").trim() || "Sin novedades para resumir.";
      return send(res, 200, { reply, action: "summarize_lead" });
    } catch (e) { return fail(res, 502, "clara summarize error: " + e.message); }
  }

  if (!message || !String(message).trim()) return fail(res, 400, "message required");

  let name = client_id, icp = {};
  try {
    const c = await db.select("clients", `id=eq.${encodeURIComponent(client_id)}&select=name,icp_config`);
    if (c[0]) { name = c[0].name; icp = c[0].icp_config || {}; }
  } catch (e) {}

  // Give Clara the client's Seguimiento (their relationships + notes) so she can answer about specific leads.
  // tl is hoisted so the write path can recognize an EXISTING lead in-memory (no extra query) and never duplicate.
  let segText = "(todavía no hay leads en Seguimiento)";
  let tl = [];
  try {
    tl = (await db.select("tracked_leads", `client_id=eq.${encodeURIComponent(client_id)}&select=id,company,decisor_name,stage&order=updated_at.desc&limit=30`))
      .filter((x) => x.company !== "__VERIFY_DELETE_ME__");
    if (tl.length) {
      const notes = await db.select("tracked_lead_notes", `client_id=eq.${encodeURIComponent(client_id)}&select=tracked_lead_id,note_text,created_at&order=created_at.desc`);
      const byLead = {};
      notes.forEach((n) => { (byLead[n.tracked_lead_id] = byLead[n.tracked_lead_id] || []).push(n); });
      segText = tl.map((l) => {
        const ns = (byLead[l.id] || []).slice(0, 4).map((n) => "· " + String(n.note_text || "").replace(/\s+/g, " ").slice(0, 220)).join(" ");
        return "— " + l.company + (l.decisor_name ? (" (" + l.decisor_name + ")") : "") + " [etapa: " + l.stage + "]" + (ns ? (" notas: " + ns) : " (sin notas)");
      }).join("\n").slice(0, 4500);
    }
  } catch (e) {}

  const who = ctx.user.email || "user";

  // ── Deterministic lead recognition (the whole premise): match names against THIS client's own list,
  //    in memory, so we recognize an existing lead and never duplicate — independent of the flaky LLM.
  const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9áéíóúñü ]/gi, " ").replace(/\s+/g, " ").trim();
  function resolveExisting(ref) {
    const q = norm(ref); if (q.length < 3) return null;
    for (const l of tl) { if (norm(l.company) === q || (l.decisor_name && norm(l.decisor_name) === q)) return l; }
    for (const l of tl) { const co = norm(l.company); if (co.length >= 4 && (co.startsWith(q) || q.startsWith(co)) && Math.min(co.length, q.length) / Math.max(co.length, q.length) >= 0.6) return l; }
    for (const l of tl) { const co = norm(l.company); if (co.length >= 4 && (q.includes(co) || co.includes(q)) && Math.min(co.length, q.length) >= 5 && Math.min(co.length, q.length) / Math.max(co.length, q.length) >= 0.7) return l; }
    return null;
  }
  function leadInMessage(msg) {
    const m = norm(msg); if (!m) return null;
    let best = null, bestLen = 0;
    for (const l of tl) {
      const co = norm(l.company);
      if (co.length >= 3 && m.includes(co) && co.length > bestLen) { best = l; bestLen = co.length; }
      const dm = norm(l.decisor_name);
      if (dm && dm.length >= 4 && m.includes(dm) && dm.length > bestLen) { best = l; bestLen = dm.length; }
    }
    return best;
  }
  const activeId = b.context && b.context.active_lead_id;
  const activeLead = activeId ? tl.find((l) => l.id === activeId) : null;

  async function appendNote(lead, noteText, newStage, replyText) {
    const changesStage = STAGES.has(newStage) && newStage !== lead.stage;
    const stageAt = changesStage ? newStage : lead.stage;
    await db.insert("tracked_lead_notes", { tracked_lead_id: lead.id, client_id, user_name: who, note_text: String(noteText || "").trim() || "(nota)", stage_at_time: stageAt });
    const patch = { updated_at: new Date().toISOString() };
    if (changesStage) patch.stage = newStage;
    await db.patch("tracked_leads", `id=eq.${encodeURIComponent(lead.id)}`, patch);
    return { reply: replyText || ("Listo, lo anoté en " + lead.company + "."), logged: true, note_added: true, tracked_lead_id: lead.id };
  }

  // ── DETERMINISTIC NOTE FAST-PATH (no LLM). The most common write: "agregale a X que ...", "anota en X: ...",
  //    or (card open) "agregá que ...". Reliable + instant + cheap. Only fires when a tracked lead is found.
  const NOTE_VERB = /^\s*(?:y\s+)?(?:le\s+)?(?:agr[eé]g|an[oó]t|sum[aá]|pon[eé]|ap[uú]nt|marc|actualiz|a[ñn]ad|agend|registr|recuerd|record|dej[aá])/i;
  if (CLARA_WRITES && message && NOTE_VERB.test(message)) {
    const lead = leadInMessage(message) || activeLead;
    if (lead) {
      try {
        let note = message.replace(/^\s*(?:y\s+)?(?:le\s+)?\S+\s+(?:a|en|para|sobre|de)\s+.+?\s*(?:que|:)\s+/i, "").trim();
        if (!note || note.length < 3) note = message.replace(/^\s*(?:y\s+)?(?:le\s+)?\S+\s*(?:que|:)\s+/i, "").trim() || message;
        return send(res, 200, await appendNote(lead, note, null, "Listo, lo anoté en " + lead.company + "."));
      } catch (e) { return send(res, 200, { reply: "Quise anotarlo pero algo falló. Probá de nuevo.", logged: false }); }
    }
  }

  const view = (b.context && b.context.view) || "(desconocida)";
  const summary = (b.context && b.context.summary) || "(sin datos)";
  const icpText = icp && icp.icp ? icp.icp : "(ICP aún no configurado)";
  const history = Array.isArray(b.history) ? b.history.slice(-6) : [];

  const sys =
    MANUAL +
    "\nCONTEXTO ACTUAL (es la VERDAD del estado, usalo, no asumas):\n- Espacio/cliente: " + name +
    "\n- Cliente ideal (ICP): " + icpText +
    "\n- Pestaña actual: " + view +
    "\n- Estado real de sus datos: " + summary +
    "\n\nSEGUIMIENTO del cliente (sus relaciones reales, con sus notas; USALO para responder sobre un lead específico):\n" + segText +
    "\n\nPodés (a) responder/guiar/RESUMIR usando los datos de arriba, o (b) REGISTRAR en Seguimiento un prospecto NUEVO que el usuario te cuenta (eso sí lo inserta el servidor de verdad).\n" +
    "Si te piden resumir o contar sobre un lead que YA está en Seguimiento (ej: 'resumime las notas de Fernando'), LEÉ sus notas de arriba y poné el resumen en tu reply. NO es un 'log' y NO cambia nada: solo respondés. NUNCA digas que hiciste/actualizaste/guardaste algo si solo leíste.\n" +
    "Respondé SOLO con JSON válido, sin markdown:\n" +
    '{"intent":"answer"|"log"|"add_note",' +
    '"reply":"<1-2 frases cortas, en el español LOCAL del usuario (chileno/colombiano según el cliente), cálida y directa>",' +
    '"lead":<si intent=log (prospecto NUEVO): {"company":..,"decisor_name":..,"contact_email":..,"contact_phone":..,"instagram":(sin @ o null),"linkedin":(url o null),"source":("referral"|"inbound"|"event"|"manual"|"ad_ig"|"ad_meta"|"other"),"stage":("nuevo"|"contactado"|"respondio"|"conversacion"|"reunion"|"propuesta"|"ganado"|"perdido"|"pausa"),"summary":(1-2 frases),"next_action":(un paso concreto)} ; si intent=add_note (lead que YA existe): {"company":(nombre EXACTO de un lead de la lista de SEGUIMIENTO de arriba),"note_text":(la nota a agregar con lo que contó el usuario),"stage":(nueva etapa si cambió, o null)} ; si intent=answer: null>}\n' +
    "REGLAS: muy BREVE. Usá el estado real (si los de hoy YA están contactados, NO digas que esperan; mandá a Tareas). No inventes pestañas/métricas (números en Inicio; Plantillas no existe). " +
    "Si el usuario quiere AGREGAR/anotar/actualizar algo de un lead que YA está en la lista de SEGUIMIENTO (ej: 'agregale a Fernando que firma el viernes'), usá intent=add_note con company = el nombre de ESE lead (tal como aparece arriba). Si es un prospecto NUEVO que no está en la lista, usá intent=log. " +
    "Con intent=log o add_note el reply CONFIRMA lo hecho (se ejecuta de verdad). No inventes datos: usá solo lo que el usuario dijo.\n";

  const convo = history.map((h) => (h.role === "user" ? "Usuario" : "Clara") + ": " + h.text).join("\n");
  const prompt = sys + (convo ? "\nConversación:\n" + convo : "") + "\nUsuario: " + message + "\nJSON:";

  let out;
  try { out = parseJSON(await route(prompt)); }
  catch (e) { return send(res, 200, { reply: "Perdón, no te entendí bien. ¿Me lo repetís más corto?", logged: false }); }

  const reply = String(out.reply || "").trim() || "Listo.";

  // BETA: note-writing is off for now — redirect to the manual control instead of guessing/echoing.
  if (!CLARA_WRITES && (out.intent === "add_note" || out.intent === "log")) {
    return send(res, 200, { reply: 'Por ahora estoy en beta y te doy info del sistema. Para guardar una nota, usá "Nueva nota" en la ficha del lead.', logged: false, beta: true });
  }

  // ADD NOTE to an existing lead (LLM path; catches phrasings the fast-path missed). Resolve the lead
  // from the model's company, else the user's words, else the open card; model note or fall back to message.
  if (out.intent === "add_note") {
    try {
      const lead = resolveExisting(out.lead && out.lead.company) || leadInMessage(message) || activeLead;
      if (!lead) return send(res, 200, { reply: 'No encontré a "' + ((out.lead && out.lead.company) || "ese lead") + '" en Seguimiento. Si es nuevo, decime y lo registro.', logged: false });
      const noteText = (out.lead && out.lead.note_text) ? out.lead.note_text : message;
      return send(res, 200, await appendNote(lead, noteText, out.lead && out.lead.stage, reply));
    } catch (e) { return send(res, 200, { reply: "Quise agregar la nota pero algo falló. Probá de nuevo.", logged: false }); }
  }

  // LOG a prospect. DEDUP: if a lead with that name already exists (or the card is open), APPEND to it
  // instead of creating a duplicate — recognizing the existing lead is the whole point.
  if (out.intent === "log" && out.lead && out.lead.company) {
    try {
      const d = out.lead;
      const existing = resolveExisting(d.company) || leadInMessage(message) || activeLead;
      const noteFromLog = (d.summary || "") + (d.next_action ? ("\n\nPróximo paso: " + d.next_action) : "");
      if (existing) return send(res, 200, await appendNote(existing, noteFromLog || message || "Actualización.", d.stage, reply));
      const stage = STAGES.has(d.stage) ? d.stage : "nuevo";
      const source = SOURCES.has(d.source) ? d.source : "manual";
      const row = (await db.insert("tracked_leads", {
        client_id, user_name: who, company: d.company, decisor_name: d.decisor_name || null,
        contact_email: d.contact_email || null, contact_phone: d.contact_phone || null,
        instagram: d.instagram || null, linkedin: d.linkedin || null, source, stage,
      }, { returning: true }))[0];
      await db.insert("tracked_lead_notes", { tracked_lead_id: row.id, client_id, user_name: who, note_text: noteFromLog, stage_at_time: stage });
      return send(res, 200, { reply, logged: true, tracked_lead: row });
    } catch (e) {
      return send(res, 200, { reply: "Quise registrarlo en Seguimiento pero algo falló. Probá de nuevo o cargalo a mano.", logged: false });
    }
  }

  return send(res, 200, { reply, logged: false });
};
