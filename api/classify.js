// api/classify.js  ->  POST /api/classify
// The flywheel seed, server-side: a client describes a prospect's reply in plain language; the cheap lane
// classifies it into a response type + temperature + next move. Aggregated per sector, these types are
// what later reshape the product (sector-learned action buttons / playbook).
// body: { client_id, text }  ->  { classification }

const { authContext, canAccess, fail } = require("./_lib/auth");
const { route, parseJSON } = require("./_lib/llm");
const { readBody, send } = require("./_lib/http");

const TAXONOMY = ["interested","wants_info","wants_pricing","wants_meeting","wants_demo_or_video",
  "not_interested","no_budget","bad_timing","already_has_vendor","referred_elsewhere",
  "no_response","asked_to_stop","closed_won","other"];

module.exports = async (req, res) => {
  if (req.method !== "POST") return fail(res, 405, "method not allowed");
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const b = await readBody(req);
  const { client_id, text } = b;
  if (!client_id || !text || !String(text).trim()) return fail(res, 400, "client_id and text required");
  if (!canAccess(ctx, client_id)) return fail(res, 403, "forbidden");

  const prompt =
    "Un cliente describe la respuesta de un prospecto. Clasificala. Responde SOLO JSON valido, sin markdown:\n" +
    '{"company":..,"person":..,"what_they_said":(resumen 1 frase, sin guiones largos),' +
    `"response_type":(UNO de: ${TAXONOMY.join(", ")}),` +
    '"secondary_type":(otro de la lista o null),' +
    '"temperature":("hot"|"warm"|"cold"),' +
    '"suggested_next_action":(paso concreto en espanol)}\n' +
    "TEXTO:\n" + text;

  let d;
  try {
    d = parseJSON(await route(prompt));
  } catch (e) {
    return fail(res, 502, "classifier failed: " + e.message);
  }
  if (!TAXONOMY.includes(d.response_type)) d.response_type = "other";
  return send(res, 200, { classification: d });
};
