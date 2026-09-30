// api/notes.js  ->  POST /api/notes
// Adds a free note to a lead. Verifies the lead belongs to the caller's client.
// body: { client_id, lead_id, note_text }

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { readBody, send } = require("./_lib/http");

module.exports = async (req, res) => {
  if (req.method !== "POST") return fail(res, 405, "method not allowed");
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const b = await readBody(req);
  const { client_id, lead_id, note_text } = b;
  if (!client_id || !lead_id || !note_text) return fail(res, 400, "client_id, lead_id, note_text required");
  if (!canAccess(ctx, client_id)) return fail(res, 403, "forbidden");

  const owns = await db.select(
    "leads",
    `id=eq.${encodeURIComponent(lead_id)}&client_id=eq.${encodeURIComponent(client_id)}&select=id`
  );
  if (!owns.length) return fail(res, 404, "lead not found in client");

  await db.insert("notes", { lead_id, user_name: ctx.user.email || "user", note_text, client_id });
  return send(res, 201, { ok: true, lead_id });
};
