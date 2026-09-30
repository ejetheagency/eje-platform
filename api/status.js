// api/status.js  ->  POST /api/status
// Changes a lead's status and records it in status_history. Verifies lead ownership.
// body: { client_id, lead_id, status }

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { readBody, send } = require("./_lib/http");

const ALLOWED = ["none", "contacted", "replied", "loom_sent", "meeting", "closed", "skip"];

module.exports = async (req, res) => {
  if (req.method !== "POST") return fail(res, 405, "method not allowed");
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const b = await readBody(req);
  const { client_id, lead_id, status } = b;
  if (!client_id || !lead_id || !status) return fail(res, 400, "client_id, lead_id, status required");
  if (!ALLOWED.includes(status)) return fail(res, 400, "invalid status");
  if (!canAccess(ctx, client_id)) return fail(res, 403, "forbidden");

  const owns = await db.select(
    "leads",
    `id=eq.${encodeURIComponent(lead_id)}&client_id=eq.${encodeURIComponent(client_id)}&select=id`
  );
  if (!owns.length) return fail(res, 404, "lead not found in client");

  await db.patch(
    "leads",
    `id=eq.${encodeURIComponent(lead_id)}&client_id=eq.${encodeURIComponent(client_id)}`,
    { status }
  );
  try {
    await db.insert("status_history", { lead_id, user_name: ctx.user.email || "user", status, client_id });
  } catch (e) { /* history is best-effort audit */ }

  return send(res, 200, { ok: true, lead_id, status });
};
