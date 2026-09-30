// api/mark-sent.js  ->  POST /api/mark-sent
// The Send-button backend: logs a real touch on a lead (messages_sent + actions) and marks it contacted.
// This is what the cadence counts, so it must be exact. Verifies the lead belongs to the caller's client.
// body: { client_id, lead_id, channel, message_text?, sent_at? }

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { readBody, send } = require("./_lib/http");

module.exports = async (req, res) => {
  if (req.method !== "POST") return fail(res, 405, "method not allowed");
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const b = await readBody(req);
  const { client_id, lead_id, channel } = b;
  if (!client_id || !lead_id || !channel) return fail(res, 400, "client_id, lead_id, channel required");
  if (!canAccess(ctx, client_id)) return fail(res, 403, "forbidden");

  const owns = await db.select(
    "leads",
    `id=eq.${encodeURIComponent(lead_id)}&client_id=eq.${encodeURIComponent(client_id)}&select=id`
  );
  if (!owns.length) return fail(res, 404, "lead not found in client");

  const who = ctx.user.email || "user";
  const sent_at = b.sent_at || new Date().toISOString();

  await db.insert("messages_sent", {
    lead_id, user_name: who, channel, message_text: b.message_text || "", sent_at, client_id,
  });
  try {
    await db.insert("actions", {
      lead_id, user_name: who, channel, completed: true, completed_at: sent_at, client_id,
    });
  } catch (e) { /* actions is a durable backup; never block the send on it */ }
  await db.patch(
    "leads",
    `id=eq.${encodeURIComponent(lead_id)}&client_id=eq.${encodeURIComponent(client_id)}`,
    { status: "contacted" }
  );

  return send(res, 200, { ok: true, lead_id, channel, sent_at });
};
