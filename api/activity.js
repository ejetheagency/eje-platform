// api/activity.js  ->  GET /api/activity?client_id=<id>&lead_id=<id>
// Merged activity timeline for one lead (messages + notes + status changes), newest first.
// Powers the record view in the CRM surface. Read-only, tenant-scoped.

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { send } = require("./_lib/http");

module.exports = async (req, res) => {
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");
  const u = new URL(req.url, "http://x");
  const clientId = u.searchParams.get("client_id");
  const leadId = u.searchParams.get("lead_id");
  if (!clientId || !leadId) return fail(res, 400, "client_id and lead_id required");
  if (!canAccess(ctx, clientId)) return fail(res, 403, "forbidden");

  const q = `lead_id=eq.${encodeURIComponent(leadId)}&client_id=eq.${encodeURIComponent(clientId)}`;
  const [msgs, notes, hist] = await Promise.all([
    db.select("messages_sent", `${q}&select=channel,message_text,sent_at`),
    db.select("notes", `${q}&select=note_text,updated_at`),
    db.select("status_history", `${q}&select=status,created_at`),
  ]);

  const tl = [];
  for (const m of msgs) tl.push({ type: "message", channel: m.channel, text: m.message_text, at: m.sent_at });
  for (const nt of notes) tl.push({ type: "note", text: nt.note_text, at: nt.updated_at });
  for (const h of hist) tl.push({ type: "status", status: h.status, at: h.created_at });
  tl.sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0)); // newest first

  send(res, 200, { client_id: clientId, lead_id: leadId, count: tl.length, timeline: tl });
};
