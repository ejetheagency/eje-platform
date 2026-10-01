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
  let segText = "(todavía no hay leads en Seguimiento)";
  try {
    const tl = (await db.select("tracked_leads", `client_id=eq.${encodeURIComponent(client_id)}&select=id,company,decisor_name,stage&order=updated_at.desc&limit=30`))
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
  catch (e) { return fail(res, 502, "clara error: " + e.message); }

  const reply = String(out.reply || "").trim() || "Listo.";

  if (out.intent === "log" && out.lead && out.lead.company) {
    try {
      const d = out.lead;
      const stage = STAGES.has(d.stage) ? d.stage : "nuevo";
      const source = SOURCES.has(d.source) ? d.source : "manual";
      const who = ctx.user.email || "user";
      const row = (await db.insert("tracked_leads", {
        client_id, user_name: who, company: d.company, decisor_name: d.decisor_name || null,
        contact_email: d.contact_email || null, contact_phone: d.contact_phone || null,
        instagram: d.instagram || null, linkedin: d.linkedin || null, source, stage,
      }, { returning: true }))[0];
      const note = (d.summary || "") + (d.next_action ? ("\n\nPróximo paso: " + d.next_action) : "");
      await db.insert("tracked_lead_notes", { tracked_lead_id: row.id, client_id, user_name: who, note_text: note, stage_at_time: stage });
      return send(res, 200, { reply, logged: true, tracked_lead: row });
    } catch (e) {
      return send(res, 200, { reply: "Quise registrarlo en Seguimiento pero algo falló. Probá de nuevo o cargalo a mano.", logged: false });
    }
  }

  if (out.intent === "add_note" && out.lead && out.lead.company && out.lead.note_text) {
    try {
      const term = String(out.lead.company).replace(/[%*,()]/g, "").trim();
      const matches = await db.select(
        "tracked_leads",
        `client_id=eq.${encodeURIComponent(client_id)}&company=ilike.*${encodeURIComponent(term)}*&select=id,company,stage&order=updated_at.desc&limit=1`
      );
      if (!matches[0]) {
        return send(res, 200, { reply: 'No encontré a "' + out.lead.company + '" en Seguimiento. Si es nuevo, decime y lo registro.', logged: false });
      }
      const lead = matches[0];
      const who = ctx.user.email || "user";
      const changesStage = STAGES.has(out.lead.stage) && out.lead.stage !== lead.stage;
      const stageAt = changesStage ? out.lead.stage : lead.stage;
      await db.insert("tracked_lead_notes", {
        tracked_lead_id: lead.id, client_id, user_name: who,
        note_text: String(out.lead.note_text), stage_at_time: stageAt,
      });
      const patch = { updated_at: new Date().toISOString() };
      if (changesStage) patch.stage = out.lead.stage;
      await db.patch("tracked_leads", `id=eq.${encodeURIComponent(lead.id)}`, patch);
      return send(res, 200, { reply: reply || ("Listo, lo anoté en " + lead.company + "."), logged: true, note_added: true, tracked_lead_id: lead.id });
    } catch (e) {
      return send(res, 200, { reply: "Quise agregar la nota pero algo falló. Probá de nuevo.", logged: false });
    }
  }

  return send(res, 200, { reply, logged: false });
};
