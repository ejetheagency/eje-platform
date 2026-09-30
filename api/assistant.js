// api/assistant.js  ->  POST /api/assistant
// The Seguimiento assistant, server-side: a client pastes a thread / notes / voice-memo transcript about a
// lead; the cheap lane structures it into a tracked_lead and (optionally) files it. "Just tell me what happened."
// body: { client_id, text, apply? }  ->  { structured, tracked_lead? }

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { route, parseJSON } = require("./_lib/llm");
const { readBody, send } = require("./_lib/http");

const STAGES = new Set(["nuevo", "contactado", "respondio", "conversacion", "reunion", "propuesta", "ganado", "perdido", "pausa"]);
const SOURCES = new Set(["referral", "inbound", "event", "manual", "ad_ig", "ad_meta", "other"]);

module.exports = async (req, res) => {
  if (req.method !== "POST") return fail(res, 405, "method not allowed");
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const b = await readBody(req);
  const { client_id, text } = b;
  if (!client_id || !text || !String(text).trim()) return fail(res, 400, "client_id and text required");
  if (!canAccess(ctx, client_id)) return fail(res, 403, "forbidden");

  const prompt =
    "Del siguiente texto (un hilo, notas o transcripcion de una nota de voz sobre un posible cliente), " +
    "extrae la info del lead. Responde SOLO con JSON valido, sin markdown, con estas claves exactas:\n" +
    '{"company":..,"decisor_name":..,"contact_email":..,"contact_phone":..,"instagram":(handle sin @ o null),' +
    '"linkedin":(url o null),"source":("referral"|"inbound"|"event"|"manual"|"ad_ig"|"ad_meta"|"other"),' +
    '"stage":("nuevo"|"contactado"|"respondio"|"conversacion"|"reunion"|"propuesta"|"ganado"|"perdido"|"pausa"),' +
    '"summary":(2-3 frases en espanol: quien es + estado de la relacion, sin guiones largos),' +
    '"next_action":(un proximo paso concreto recomendado en espanol)}\n' +
    "Usa null para lo que no aparezca. TEXTO:\n" + text;

  let d;
  try {
    d = parseJSON(await route(prompt));
  } catch (e) {
    return fail(res, 502, "assistant could not structure the text: " + e.message);
  }
  d.stage = STAGES.has(d.stage) ? d.stage : "nuevo";
  d.source = SOURCES.has(d.source) ? d.source : "manual";

  if (!b.apply) return send(res, 200, { structured: d, applied: false });

  const who = ctx.user.email || "user";
  const row = (
    await db.insert("tracked_leads", {
      client_id, user_name: who,
      company: d.company || "(sin nombre)", decisor_name: d.decisor_name || null,
      contact_email: d.contact_email || null, contact_phone: d.contact_phone || null,
      instagram: d.instagram || null, linkedin: d.linkedin || null,
      source: d.source, stage: d.stage,
    }, { returning: true })
  )[0];
  const note = (d.summary || "") + "\n\nPROXIMO PASO (asistente): " + (d.next_action || "");
  await db.insert("tracked_lead_notes", {
    tracked_lead_id: row.id, client_id, user_name: who, note_text: note, stage_at_time: d.stage,
  });
  return send(res, 201, { structured: d, applied: true, tracked_lead: row });
};
